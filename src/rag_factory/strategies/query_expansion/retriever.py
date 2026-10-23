"""Query expansion strategy delegates to reusable multi-query fusion."""

from dataclasses import dataclass
from typing import Callable, Sequence

from rag_factory.core.interfaces.services import LLMService
from rag_factory.strategies.multi_query.retriever import MultiQueryRetriever
from rag_factory.strategies.query_expansion.expansion.expander import QueryExpander


@dataclass
class QueryExpansionRetriever:
    llm: LLMService
    search: Callable[[str, int], Sequence[str]]
    max_variants: int = 3

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        return MultiQueryRetriever(
            QueryExpander(self.llm, self.max_variants), self.search
        ).retrieve(query, limit)
