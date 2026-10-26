"""P0: artifact catalogs never corrupt a valid previous version."""
import json
import pytest
from rag_factory.core.artifact_catalog import save_manifests, load_manifests
from rag_factory.core.index_manifest import IndexManifest

def test_catalog_atomic_replacement_and_roundtrip(tmp_path):
    path = tmp_path / "indexes.json"
    old = {"keyword": IndexManifest("artifact-old", frozenset({"keywords"}), "1")}
    new = {"keyword": IndexManifest("artifact-new", frozenset({"keywords"}), "1")}
    save_manifests(path, old)
    save_manifests(path, new)
    assert load_manifests(path) == new
    assert json.loads(path.read_text())["indexes"]["keyword"]["artifact_id"] == "artifact-new"
    assert not list(tmp_path.glob("*.tmp"))

def test_failed_atomic_replace_preserves_existing_catalog(tmp_path, monkeypatch):
    path = tmp_path / "indexes.json"
    old = {"keyword": IndexManifest("existing", frozenset({"keywords"}), "1")}
    save_manifests(path, old)
    def fail(*args, **kwargs):
        raise OSError("simulated disk replace failure")
    monkeypatch.setattr("rag_factory.core.artifact_catalog.os.replace", fail)
    with pytest.raises(OSError, match="simulated"):
        save_manifests(path, {"keyword": IndexManifest("replacement", frozenset({"keywords"}), "1")})
    assert load_manifests(path) == old
    assert not list(tmp_path.glob("*.tmp"))
