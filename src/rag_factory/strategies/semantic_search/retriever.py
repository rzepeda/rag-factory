"""Semantic retrieval against a separately produced compatible index."""

from dataclasses import dataclass

from rag_factory.core.index_manifest import (
    IndexManifest, IndexRequirement, validate_index_compatibility,
)
from rag_factory.core.interfaces.services import EmbeddingService, VectorStoreService


@dataclass
class SemanticRetriever:
    embedding: EmbeddingService
    store: VectorStoreService
    embedding_model: str
    distance_metric: str = "euclidean"

    def retrieve(self, query: str, manifest: IndexManifest, limit: int = 5) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        validate_index_compatibility(
            manifest,
            IndexRequirement(
                capabilities=frozenset({"vectors"}),
                schema_version="1",
                embedding_model=self.embedding_model,
                distance_metric=self.distance_metric,
            ),
        )
        if not query.strip():
            return []
        vectors = self.embedding.embed([query])
        if len(vectors) != 1 or not vectors[0]:
            raise ValueError("Embedding provider must return one nonempty query vector")
        if len(vectors[0]) != manifest.embedding_dimensions:
            raise ValueError("Incompatible index embedding_dimensions")
        return list(self.store.search(vectors[0], limit))
