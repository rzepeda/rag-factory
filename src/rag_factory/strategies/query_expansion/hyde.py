"""Hypothetical-document expansion with a provider-neutral LLM."""
from dataclasses import dataclass
from typing import Callable, Sequence
from rag_factory.core.interfaces.services import LLMService

@dataclass
class HyDERetriever:
    llm: LLMService
    search: Callable[[str, int], Sequence[str]]

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if not query.strip():
            return []
        passage = self.llm.generate(
            "Write a short hypothetical answer passage to aid semantic retrieval. "
            "Return only the passage.\nQuestion:\n" + query
        )
        if not isinstance(passage, str) or not passage.strip():
            raise ValueError("HyDE requires a nonempty hypothetical passage")
        return list(dict.fromkeys(self.search(passage.strip(), limit)))[:limit]
