"""P0: one atomic metadata snapshot survives failures and separate executions."""
import json

import pytest

from rag_factory.core.artifact_bundle import load_artifact_bundle, save_artifact_bundle
from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.service_registry import ServiceConfig
from rag_factory.factory.unified import UnifiedConfiguration, build_unified
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy
from tests.unit.core.test_unified_all_strategies import setup, spec


def test_artifact_bundle_roundtrip_and_atomic_replace_failure(tmp_path, monkeypatch):
    path = tmp_path / "bundle.json"
    manifests = {
        "tree": IndexManifest("tree-v1", frozenset({"keywords", "hierarchy", "chunks"}), "1"),
        "lexical": IndexManifest("lexical-v1", frozenset({"keywords"}), "1"),
    }
    hierarchy = {"tree": Hierarchy({"child": "parent"})}
    save_artifact_bundle(path, manifests, hierarchy)
    assert load_artifact_bundle(path) == (manifests, hierarchy)

    def fail(*args, **kwargs):
        raise OSError("injected replace failure")
    monkeypatch.setattr("rag_factory.core.artifact_catalog.os.replace", fail)
    with pytest.raises(OSError, match="injected replace failure"):
        save_artifact_bundle(path, {
            "tree": IndexManifest("tree-v2", frozenset({"keywords", "hierarchy", "chunks"}), "1")
        }, hierarchy)
    assert load_artifact_bundle(path) == (manifests, hierarchy)
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("mutation", [
    lambda d: d.update({"format_version": 2}),
    lambda d: d.update({"hierarchies": {}}),
    lambda d: d["hierarchies"].update({"unknown": {"x": "y"}}),
    lambda d: d["indexes"]["tree"].update({"schema_version": "2", "bad_field": 1}),
])
def test_reject_corrupt_or_mismatched_bundle(tmp_path, mutation):
    path = tmp_path / "bundle.json"
    save_artifact_bundle(path, {
        "tree": IndexManifest("tree", frozenset({"keywords", "hierarchy", "chunks"}), "1")
    }, {"tree": Hierarchy({"c": "p"})})
    data = json.loads(path.read_text())
    mutation(data)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_artifact_bundle(path)


def test_cross_execution_manifest_and_hierarchy_bundle(tmp_path):
    registry, services = setup()
    # Persist just provider state between two pipeline instances; no external services.
    for interface in ("keyword_store", "document_store", "vector_store"):
        descriptor, instance = registry.resolve(services[interface])
        registry.register(
            ProviderDescriptor(interface, "shared", descriptor.capabilities),
            lambda instance=instance: instance,
        )
        services[interface] = ServiceConfig(interface, "shared")
    configuration = UnifiedConfiguration(services, {
        "tree": spec("hierarchical", ["keyword_store", "document_store"],
                     ["keyword_store", "document_store", "tokenizer"]),
        "semantic": spec("semantic", ["embedding", "vector_store"],
                         ["embedding", "vector_store"], embedding_model="mock"),
    })
    path = tmp_path / "complete-bundle.json"
    with build_unified(configuration, registry) as writer:
        writer.index("tree", {"parents": {"parent": "cat parent"},
                              "children": {"child": "cat"},
                              "child_to_parent": {"child": "parent"}})
        writer.index("semantic", {"documents": {"vector-doc": "cat"}})
        writer.export_artifact_bundle(path)
    with build_unified(configuration, registry) as reader:
        reader.attach_artifact_bundle(path)
        assert reader.retrieve("tree", "cat")[0].document_id == "parent"
        assert reader.retrieve("semantic", "cat")[0].document_id == "vector-doc"


def test_invalid_bundle_does_not_publish_partial_pipeline_metadata(tmp_path):
    registry, services = setup()
    config = UnifiedConfiguration(services, {
        "lexical": spec("keyword", ["keyword_store"], ["keyword_store", "tokenizer"],
                        artifact_id="expected-id")
    })
    path = tmp_path / "bundle.json"
    save_artifact_bundle(path, {
        "lexical": IndexManifest("different-id", frozenset({"keywords"}), "1")
    })
    with build_unified(config, registry) as pipeline:
        with pytest.raises(ValueError, match="artifact_id"):
            pipeline.attach_artifact_bundle(path)
        assert pipeline._artifacts == {}
