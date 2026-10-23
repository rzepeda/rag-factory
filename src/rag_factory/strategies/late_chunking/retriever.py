"""Retrieve late-pooled vectors using a compatible query embedding model."""

from dataclasses import dataclass

from rag_factory.core.index_manifest import IndexManifest, IndexRequirement, validate_index_compatibility
from rag_factory.core.interfaces.services import EmbeddingService, VectorStoreService


@dataclass
class LateChunkingRetriever:
    embedding: EmbeddingService
    store: VectorStoreService
    embedding_model: str

    def retrieve(self, query: str, manifest: IndexManifest, limit: int = 5) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        validate_index_compatibility(
            manifest,
            IndexRequirement(
                frozenset({"vectors", "late_chunking"}),
                schema_version="1", embedding_model=self.embedding_model,
                distance_metric="euclidean",
            ),
        )
        if not query.strip():
            return []
        vectors = self.embedding.embed([query])
        if len(vectors) != 1 or len(vectors[0]) != manifest.embedding_dimensions:
            raise ValueError("Query vector dimensions must match the index")
        return list(self.store.search(vectors[0], limit))
