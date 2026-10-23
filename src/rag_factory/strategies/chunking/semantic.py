"""Sentence-boundary chunking driven by an injected embedding service."""
import re
from dataclasses import dataclass
from math import sqrt
from rag_factory.core.interfaces.services import EmbeddingService

@dataclass
class SemanticBoundaryChunker:
    embedding: EmbeddingService
    threshold: float = 0.6
    max_sentences: int = 5

    def chunk(self, text: str) -> list[str]:
        if not 0 <= self.threshold <= 1 or self.max_sentences <= 0:
            raise ValueError("Invalid semantic chunking options")
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if not sentences:
            return []
        vectors = list(self.embedding.embed(sentences))
        if len(vectors) != len(sentences) or not vectors or not vectors[0]:
            raise ValueError("Embedding count or dimensions do not match sentences")
        width = len(vectors[0])
        if any(len(v) != width for v in vectors):
            raise ValueError("Inconsistent sentence embedding dimensions")
        chunks, current = [], [sentences[0]]
        for index in range(1, len(sentences)):
            left, right = vectors[index - 1], vectors[index]
            norm = sqrt(sum(x*x for x in left) * sum(x*x for x in right))
            similarity = sum(a*b for a, b in zip(left, right)) / norm if norm else 0
            if similarity < self.threshold or len(current) >= self.max_sentences:
                chunks.append(" ".join(current))
                current = []
            current.append(sentences[index])
        chunks.append(" ".join(current))
        return chunks
