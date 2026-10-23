"""LLM-backed query variants with bounded, deterministic parsing."""

from dataclasses import dataclass
from rag_factory.core.interfaces.services import LLMService


@dataclass
class QueryExpander:
    llm: LLMService
    max_variants: int = 3

    def expand(self, query: str) -> list[str]:
        if self.max_variants <= 0:
            raise ValueError("max_variants must be positive")
        if not query.strip():
            return []
        generated = self.llm.generate(
            "Suggest alternate search queries, one per line, without explanations:\n" + query
        )
        if not isinstance(generated, str):
            raise TypeError("LLM response must be text")
        candidates = [query.strip(), *(line.strip(" -\t0123456789.") for line in generated.splitlines())]
        result = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate.casefold() not in seen:
                result.append(candidate)
                seen.add(candidate.casefold())
            if len(result) >= self.max_variants + 1:
                break
        return result
