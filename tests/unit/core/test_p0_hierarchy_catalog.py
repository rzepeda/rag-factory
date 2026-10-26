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
