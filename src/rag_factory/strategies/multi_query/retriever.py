"""Multi-query search with rank fusion and no provider-specific coupling."""

from dataclasses import dataclass
from typing import Callable, Sequence

from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements
from rag_factory.strategies.query_expansion.expansion.expander import QueryExpander


REQUIREMENTS = StrategyRequirements(
    retrieval=(ServiceRequirement("llm", frozenset({"generate"})),)
)


@dataclass
class MultiQueryRetriever:
    expander: QueryExpander
    search: Callable[[str, int], Sequence[str]]
    rank_constant: int = 60

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0 or self.rank_constant <= 0:
            raise ValueError("limit and rank_constant must be positive")
        variants = self.expander.expand(query)
        if not variants:
            return []
        scores: dict[str, float] = {}
        for variant in variants:
            for rank, identifier in enumerate(dict.fromkeys(self.search(variant, limit)), start=1):
                scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (self.rank_constant + rank)
        return sorted(scores, key=lambda identifier: (-scores[identifier], identifier))[:limit]
