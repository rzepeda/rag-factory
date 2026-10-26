"""Explicit JSON persistence for index manifest metadata (never index contents).

No external infrastructure, automatic discovery, or schema migrations.
"""
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from rag_factory.core.index_manifest import IndexManifest


def save_manifests(path: str | Path, manifests: dict[str, IndexManifest]) -> None:
    """Write named index manifests as a portable versioned JSON catalog."""
    if not manifests or any(not isinstance(name, str) or not name.strip()
                            or not isinstance(manifest, IndexManifest)
                            for name, manifest in manifests.items()):
        raise ValueError("Catalog requires named IndexManifest entries")
    entries = {}
    for name, manifest in sorted(manifests.items()):
        data = asdict(manifest)
        data["capabilities"] = sorted(manifest.capabilities)
        entries[name] = data
    payload = {"format_version": 1, "indexes": entries}
    target = Path(path)
    # Never truncate a previous usable catalog on write failure.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_manifests(path: str | Path) -> dict[str, IndexManifest]:
    """Reject unfamiliar formats/fields rather than silently misread an artifact."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"format_version", "indexes"}:
        raise ValueError("Invalid artifact catalog format")
    if type(payload["format_version"]) is not int or payload["format_version"] != 1:
        raise ValueError("Unsupported artifact catalog version")
    items = payload["indexes"]
    if not isinstance(items, dict) or not items:
        raise ValueError("Artifact catalog indexes must be a nonempty mapping")
    known = set(IndexManifest.__dataclass_fields__)
    manifests = {}
    for name, data in items.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(data, dict):
            raise ValueError("Invalid artifact entry")
        if set(data) - known:
            raise ValueError(f"Unknown index manifest fields: {set(data) - known}")
        caps = data.get("capabilities")
        if not isinstance(caps, list) or any(not isinstance(v, str) or not v.strip() for v in caps):
            raise ValueError("Artifact capabilities must be a list of nonempty strings")
        manifests[name] = IndexManifest(**{**data, "capabilities": frozenset(caps)})
    return manifests
