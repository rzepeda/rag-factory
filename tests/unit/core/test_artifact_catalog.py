"""Artifact manifests are portable; index storage stays external."""

import json

import pytest

from rag_factory.core.artifact_catalog import load_manifests, save_manifests
from rag_factory.core.index_manifest import IndexManifest


def test_catalog_round_trip_and_deterministic_bytes(tmp_path):
    artifacts = {
        "keyword": IndexManifest("k", frozenset({"keywords"}), "1", analyzer="word-lowercase"),
        "semantic": IndexManifest(
            "s", frozenset({"vectors", "chunks"}), "1", embedding_model="mock",
            embedding_dimensions=2, distance_metric="euclidean", access_scope="sandbox",
        ),
    }
    path = tmp_path / "indexes.json"
    save_manifests(path, artifacts)
    first = path.read_bytes()
    assert load_manifests(path) == artifacts
    save_manifests(path, dict(reversed(list(artifacts.items()))))
    assert path.read_bytes() == first


def test_catalog_rejects_unknown_version_and_fields(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"format_version": 2, "indexes": {"a": {}}}))
    with pytest.raises(ValueError, match="Unsupported"):
        load_manifests(path)
    path.write_text(json.dumps({"format_version": 1, "indexes": {
        "x": {"artifact_id": "a", "capabilities": ["keywords"],
              "schema_version": "1", "unexpected": True}
    }}))
    with pytest.raises(ValueError, match="Unknown"):
        load_manifests(path)


def test_catalog_rejects_empty_entries(tmp_path):
    path = tmp_path / "empty.json"
    with pytest.raises(ValueError, match="requires"):
        save_manifests(path, {})
