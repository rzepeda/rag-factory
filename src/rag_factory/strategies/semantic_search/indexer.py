"""Provider-independent semantic indexing, usable with offline service mocks."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.interfaces.services import EmbeddingService, VectorStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("embedding", frozenset({"embed"})),
        ServiceRequirement("vector_store", frozenset({"upsert"})),
    ),
    retrieval=(
        ServiceRequirement("embedding", frozenset({"embed"})),
        ServiceRequirement("vector_store", frozenset({"search"})),
    ),
)


@dataclass
class SemanticIndexer:
    embedding: EmbeddingService
    store: VectorStoreService
    embedding_model: str
    distance_metric: str = "euclidean"

    def index(self, documents: Mapping[str, str], artifact_id: str) -> IndexManifest:
        if not documents:
            raise ValueError("Cannot index an empty document set")
        if any(not key or not isinstance(content, str) for key, content in documents.items()):
            raise ValueError("Documents need nonempty identifiers and string content")
        if not self.embedding_model.strip():
            raise ValueError("Embedding model identifier is required")
        if not artifact_id.strip():
            raise ValueError("Artifact identifier is required")
        vectors = self.embedding.embed(list(documents.values()))
        if len(vectors) != len(documents):
            raise ValueError("Embedding provider returned the wrong number of vectors")
        dimensions = len(vectors[0]) if vectors else 0
        if dimensions <= 0 or any(len(v) != dimensions for v in vectors):
            raise ValueError("Embeddings must have consistent positive dimensions")
        self.store.upsert(dict(zip(documents, vectors)))
        return IndexManifest(
            artifact_id=artifact_id,
            capabilities=frozenset({"vectors"}),
            schema_version="1",
            embedding_model=self.embedding_model,
            embedding_dimensions=dimensions,
            distance_metric=self.distance_metric,
        )
