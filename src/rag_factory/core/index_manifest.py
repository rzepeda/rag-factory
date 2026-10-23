"""Index artifacts describe outputs independently of retrieval strategies."""

from dataclasses import dataclass, field
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class IndexManifest:
    """Minimal declarative index identity and semantic compatibility metadata."""

    artifact_id: str
    capabilities: FrozenSet[str]
    schema_version: str
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    distance_metric: Optional[str] = None
    analyzer: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact_id.strip() or not self.schema_version.strip():
            raise ValueError("Artifact ID and schema version are required")
        if self.embedding_dimensions is not None and self.embedding_dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")
        if self.embedding_dimensions is not None and not self.embedding_model:
            raise ValueError("Embedding model must be provided with dimensions")


@dataclass(frozen=True)
class IndexRequirement:
    capabilities: FrozenSet[str]
    schema_version: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    distance_metric: Optional[str] = None
    analyzer: Optional[str] = None


def validate_index_compatibility(
    artifact: IndexManifest, requirement: IndexRequirement
) -> None:
    """Conservative metadata validation; providers may impose extra constraints."""
    missing = requirement.capabilities.difference(artifact.capabilities)
    if missing:
        raise ValueError(f"Missing index capabilities: {', '.join(sorted(missing))}")
    for attribute in (
        "schema_version", "embedding_model", "embedding_dimensions",
        "distance_metric", "analyzer",
    ):
        expected = getattr(requirement, attribute)
        if expected is not None and getattr(artifact, attribute) != expected:
            raise ValueError(f"Incompatible index {attribute}: expected {expected!r}")
