"""Bounded query rewriting when retrieval returns no useful candidates."""
from dataclasses import dataclass
from typing import Callable, Sequence
from rag_factory.core.interfaces.services import LLMService

@dataclass
class QueryRefinementRetriever:
    llm: LLMService
    search: Callable[[str, int], Sequence[str]]
    max_rewrites: int = 2

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0 or self.max_rewrites < 0:
            raise ValueError("Limit must be positive and max_rewrites nonnegative")
        if not query.strip():
            return []
        current, seen_queries = query, {query}
        for attempt in range(self.max_rewrites + 1):
            results = list(dict.fromkeys(self.search(current, limit)))[:limit]
            if results:
                return results
            if attempt == self.max_rewrites:
                return []
            rewritten = self.llm.generate(
                "Rewrite this search query to retrieve relevant evidence. "
                "Return only one revised search query.\nQuery:\n" + current
            )
            if not isinstance(rewritten, str) or not rewritten.strip():
                raise ValueError("Query refinement requires nonempty rewritten text")
            revised = rewritten.strip()
            if revised in seen_queries:
                return []
            seen_queries.add(revised)
            current = revised
        return []
