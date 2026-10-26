"""Durable, validated hierarchy metadata for cross-process retrieval.

Only relationship metadata is stored; document and keyword indexes remain external.
"""
import json
from pathlib import Path
from rag_factory.core.artifact_catalog import _atomic_write_json
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy


def save_hierarchies(path: str | Path, hierarchies: dict[str, Hierarchy]) -> None:
    if not hierarchies:
        raise ValueError("Hierarchy catalog requires entries")
    entries = {}
    for name, hierarchy in hierarchies.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(hierarchy, Hierarchy):
            raise ValueError("Invalid hierarchy entry")
        mapping = hierarchy.child_to_parent
        if not mapping or any(not isinstance(k, str) or not k.strip()
                              or not isinstance(v, str) or not v.strip()
                              for k, v in mapping.items()):
            raise ValueError("Hierarchy mappings must contain nonempty string IDs")
        entries[name] = dict(sorted(mapping.items()))
    _atomic_write_json(path, {"format_version": 1, "hierarchies": entries})


def load_hierarchies(path: str | Path) -> dict[str, Hierarchy]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"format_version", "hierarchies"}:
        raise ValueError("Invalid hierarchy catalog format")
    if type(payload["format_version"]) is not int or payload["format_version"] != 1:
        raise ValueError("Unsupported hierarchy catalog version")
    entries = payload["hierarchies"]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Hierarchy catalog must contain named entries")
    result = {}
    for name, mapping in entries.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(mapping, dict) or not mapping:
            raise ValueError("Invalid hierarchy entry")
        if any(not isinstance(k, str) or not k.strip()
               or not isinstance(v, str) or not v.strip()
               for k, v in mapping.items()):
            raise ValueError("Invalid hierarchy relationship")
        result[name] = Hierarchy(dict(mapping))
    return result
