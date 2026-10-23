"""Reciprocal rank fusion of independent retrieval sources."""

from dataclasses import dataclass

from rag_factory.pipelines.retrieval import RetrievalPipeline


@dataclass
class HybridRetriever:
    retrieval: RetrievalPipeline
    rank_constant: int = 60

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if self.rank_constant <= 0:
            raise ValueError("rank_constant must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")
        results = self.retrieval.search(query, limit)
        scores: dict[str, float] = {}
        for documents in results.values():
            for rank, identifier in enumerate(dict.fromkeys(documents), start=1):
                scores[identifier] = scores.get(identifier, 0) + 1 / (self.rank_constant + rank)
        return sorted(scores, key=lambda key: (-scores[key], key))[:limit]
