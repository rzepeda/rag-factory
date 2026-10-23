"""Provider-neutral two-stage retrieval and reranking."""

from dataclasses import dataclass
from typing import Callable, Sequence

from rag_factory.core.interfaces.services import DocumentStoreService, RerankerService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


REQUIREMENTS = StrategyRequirements(
    retrieval=(
        ServiceRequirement("document_store", frozenset({"get"})),
        ServiceRequirement("reranker", frozenset({"rerank"})),
    )
)


@dataclass
class RerankingRetriever:
    """Retrieve candidates, load originals, then rerank without provider coupling.

    A retriever callable provides candidate identifiers. The reranker may only
    order those candidates, never introduce unknown document identifiers.
    """

    search: Callable[[str, int], Sequence[str]]
    documents: DocumentStoreService
    reranker: RerankerService
    candidate_multiplier: int = 3

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0 or self.candidate_multiplier <= 0:
            raise ValueError("limit and candidate_multiplier must be positive")
        if not query.strip():
            return []
        candidate_ids = list(dict.fromkeys(self.search(query, limit * self.candidate_multiplier)))
        original = {}
        for identifier in candidate_ids:
            content = self.documents.get(identifier)
            if content is None:
                raise ValueError(f"Missing candidate document: {identifier}")
            original[identifier] = content
        if not original:
            return []
        ranking = list(self.reranker.rerank(query, original))
        if len(ranking) != len(original) or set(ranking) != set(original):
            raise ValueError("Reranker must return exactly the provided candidate IDs")
        return ranking[:limit]
