"""Atomic *metadata* snapshots for cross-execution index handoff.

Bundles keep manifests and hierarchy relationships in one versioned JSON file.
They do not include documents or physically commit provider data.
"""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping

from rag_factory.core.artifact_catalog import _atomic_write_json
from rag_factory.core.index_manifest import IndexManifest
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy


def _validate_bundle(manifests: Mapping[str, IndexManifest],
                     hierarchies: Mapping[str, Hierarchy]) -> None:
    if not isinstance(manifests, Mapping) or not manifests:
        raise ValueError("Bundle needs named index manifests")
    if not isinstance(hierarchies, Mapping):
        raise ValueError("Bundle hierarchies must be a mapping")
    for name, manifest in manifests.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(manifest, IndexManifest):
            raise ValueError("Invalid bundle index manifest")
        if ("hierarchy" in manifest.capabilities) != (name in hierarchies):
            raise ValueError(f"Hierarchy metadata mismatch for {name}")
    for name, hierarchy in hierarchies.items():
        if name not in manifests or not isinstance(hierarchy, Hierarchy):
            raise ValueError(f"Invalid bundle hierarchy: {name}")


def save_artifact_bundle(path: str | Path,
                         manifests: Mapping[str, IndexManifest],
                         hierarchies: Mapping[str, Hierarchy] | None = None) -> None:
    """Atomically publish a consistent snapshot of manifests and relationships."""
    relationships = {} if hierarchies is None else hierarchies
    _validate_bundle(manifests, relationships)
    indexes = {}
    for name, manifest in sorted(manifests.items()):
        data = asdict(manifest)
        data["capabilities"] = sorted(manifest.capabilities)
        indexes[name] = data
    payload = {
        "format_version": 1,
        "indexes": indexes,
        "hierarchies": {
            name: dict(sorted(hierarchy.child_to_parent.items()))
            for name, hierarchy in sorted(relationships.items())
        },
    }
    _atomic_write_json(path, payload)


def load_artifact_bundle(path: str | Path) -> tuple[dict[str, IndexManifest], dict[str, Hierarchy]]:
    """Reject incomplete/corrupt snapshots instead of publishing partial metadata."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"format_version", "indexes", "hierarchies"}:
        raise ValueError("Invalid artifact bundle format")
    if type(payload["format_version"]) is not int or payload["format_version"] != 1:
        raise ValueError("Unsupported artifact bundle version")
    raw_indexes, raw_hierarchies = payload["indexes"], payload["hierarchies"]
    if not isinstance(raw_indexes, dict) or not raw_indexes or not isinstance(raw_hierarchies, dict):
        raise ValueError("Invalid artifact bundle entries")
    known = set(IndexManifest.__dataclass_fields__)
    manifests = {}
    for name, data in raw_indexes.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(data, dict):
            raise ValueError("Invalid bundle index entry")
        if set(data) - known:
            raise ValueError("Unknown bundle index manifest fields")
        caps = data.get("capabilities")
        if not isinstance(caps, list) or any(not isinstance(v, str) or not v.strip() for v in caps):
            raise ValueError("Invalid bundle capabilities")
        manifests[name] = IndexManifest(**{**data, "capabilities": frozenset(caps)})
    hierarchies = {}
    for name, mapping in raw_hierarchies.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(mapping, dict):
            raise ValueError("Invalid bundle relationship entry")
        hierarchies[name] = Hierarchy(dict(mapping))
    _validate_bundle(manifests, hierarchies)
    return manifests, hierarchies
