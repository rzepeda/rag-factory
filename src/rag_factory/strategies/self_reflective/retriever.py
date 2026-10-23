"""Bounded retrieve-grade-retry loop using provider-neutral services."""

from dataclasses import dataclass
from typing import Callable, Sequence

from rag_factory.core.interfaces.services import DocumentStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements
from rag_factory.strategies.self_reflective.grading.grader import RelevanceGrader


REQUIREMENTS = StrategyRequirements(
    retrieval=(
        ServiceRequirement("llm", frozenset({"generate"})),
        ServiceRequirement("document_store", frozenset({"get"})),
    )
)


@dataclass
class SelfReflectiveRetriever:
    search: Callable[[str, int], Sequence[str]]
    documents: DocumentStoreService
    grader: RelevanceGrader
    max_attempts: int = 2

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0 or self.max_attempts <= 0:
            raise ValueError("limit and max_attempts must be positive")
        if not query.strip():
            return []
        accepted = []
        seen = set()
        for _ in range(self.max_attempts):
            for identifier in self.search(query, limit):
                if identifier in seen:
                    continue
                seen.add(identifier)
                passage = self.documents.get(identifier)
                if passage is None:
                    raise ValueError(f"Missing candidate document: {identifier}")
                if self.grader.relevant(query, passage):
                    accepted.append(identifier)
                    if len(accepted) >= limit:
                        return accepted
        return accepted
