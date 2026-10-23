"""Late chunking: contextualize full-document tokens before pooling spans."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol, Sequence, Mapping

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.interfaces.services import VectorStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


class ContextualTokenEncoder(Protocol):
    """Return one contextualized vector per token in the full input document."""

    def encode_tokens(self, tokens: Sequence[str]) -> Sequence[Sequence[float]]: ...


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("contextual_token_encoder", frozenset({"encode_tokens"})),
        ServiceRequirement("vector_store", frozenset({"upsert"})),
    ),
    retrieval=(
        ServiceRequirement("embedding", frozenset({"embed"})),
        ServiceRequirement("vector_store", frozenset({"search"})),
    ),
)


@dataclass
class LateChunkingIndexer:
    encoder: ContextualTokenEncoder
    store: VectorStoreService
    embedding_model: str

    def index(
        self,
        tokens: Sequence[str],
        spans: Mapping[str, tuple[int, int]],
        artifact_id: str,
    ) -> IndexManifest:
        """Pool document-contextual token vectors over half-open token spans."""
        if not artifact_id.strip() or not self.embedding_model.strip() or not tokens or not spans:
            raise ValueError("Artifact ID, embedding model, tokens and spans are required")
        if any(not isinstance(t, str) or not t.strip() for t in tokens):
            raise ValueError("Tokens must be nonempty strings")
        for identifier, boundaries in spans.items():
            if (not isinstance(identifier, str) or not identifier.strip()
                or not isinstance(boundaries, tuple) or len(boundaries) != 2
                or not all(type(v) is int for v in boundaries)
                or not (0 <= boundaries[0] < boundaries[1] <= len(tokens))):
                raise ValueError("Chunk spans must be valid half-open token ranges")
        contextual = self.encoder.encode_tokens(tokens)
        if len(contextual) != len(tokens):
            raise ValueError("Encoder must return one vector per document token")
        width = len(contextual[0])
        if width == 0 or any(len(v) != width for v in contextual):
            raise ValueError("Contextual vectors must have consistent positive dimensions")
        if any(not isfinite(value) for vector in contextual for value in vector):
            raise ValueError("Contextual vectors must contain finite numbers")
        chunks = {}
        for identifier, (start, end) in spans.items():
            chunks[identifier] = [
                sum(contextual[position][dimension] for position in range(start, end)) / (end - start)
                for dimension in range(width)
            ]
        self.store.upsert(chunks)
        return IndexManifest(
            artifact_id=artifact_id,
            capabilities=frozenset({"vectors", "late_chunking"}),
            schema_version="1",
            embedding_model=self.embedding_model,
            embedding_dimensions=width,
            distance_metric="euclidean",
        )
