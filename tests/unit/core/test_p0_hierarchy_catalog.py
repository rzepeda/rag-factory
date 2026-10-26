"""Offline cross-execution hierarchy catalog acceptance tests."""
import pytest
from rag_factory.core.hierarchy_catalog import save_hierarchies, load_hierarchies
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy


def test_hierarchy_catalog_roundtrip(tmp_path):
    path = tmp_path / "hierarchies.json"
    original = {"hierarchy": Hierarchy({"child-a": "parent-a", "child-b": "parent-a"})}
    save_hierarchies(path, original)
    assert load_hierarchies(path)["hierarchy"].child_to_parent == original["hierarchy"].child_to_parent


def test_hierarchy_catalog_rejects_invalid_data(tmp_path):
    path = tmp_path / "hierarchies.json"
    for contents in ('{"format_version": 2, "hierarchies": {"h": {"a": "b"}}}',
                     '{"format_version": 1, "hierarchies": {"h": {"a": ""}}}',
                     '{"format_version": 1, "hierarchies": {}}'):
        path.write_text(contents)
        with pytest.raises(ValueError):
            load_hierarchies(path)


def test_hierarchy_catalog_replace_failure_keeps_old(tmp_path, monkeypatch):
    path = tmp_path / "hierarchies.json"
    save_hierarchies(path, {"h": Hierarchy({"a": "b"})})
    def fail(*args):
        raise OSError("disk failure")
    monkeypatch.setattr("rag_factory.core.artifact_catalog.os.replace", fail)
    with pytest.raises(OSError, match="disk failure"):
        save_hierarchies(path, {"h": Hierarchy({"a": "new"})})
    assert load_hierarchies(path)["h"].child_to_parent == {"a": "b"}

def test_separate_pipeline_can_attach_saved_hierarchy(tmp_path):
    from tests.unit.core.test_unified_all_strategies import setup, spec
    from rag_factory.factory.unified import UnifiedConfiguration, build_unified
    from rag_factory.core.artifact_catalog import save_manifests, load_manifests
    registry, services = setup()
    config = UnifiedConfiguration(services, {
        "hierarchy": spec("hierarchical", ["keyword_store", "document_store"],
                          ["keyword_store", "document_store", "tokenizer"])
    })
    # The in-memory stores are explicitly shared between executions.
    instances = {}
    for interface in ("keyword_store", "document_store"):
        descriptor = registry.descriptor(services[interface])
        _, instance = registry.resolve(services[interface])
        instances[interface] = instance
        registry._providers[(interface, "shared")] = (descriptor, lambda instance=instance: instance)
        services[interface] = type(services[interface])(interface, "shared")
    config = UnifiedConfiguration(services, config.strategies)
    with build_unified(config, registry) as writer:
        manifest = writer.index("hierarchy", {
            "parents": {"parent": "cat parent"},
            "children": {"child": "cat"},
            "child_to_parent": {"child": "parent"},
        })
        save_manifests(tmp_path / "indexes.json", {"hierarchy": manifest})
        save_hierarchies(tmp_path / "hierarchies.json", writer._hierarchies)
    with build_unified(config, registry) as reader:
        reader.attach_artifacts(load_manifests(tmp_path / "indexes.json"),
                                hierarchies=load_hierarchies(tmp_path / "hierarchies.json"))
        assert reader.retrieve("hierarchy", "cat")[0].document_id == "parent"
