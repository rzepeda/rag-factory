"""Constrained LLM relevance grader with conservative invalid-output handling."""

from dataclasses import dataclass

from rag_factory.core.interfaces.services import LLMService


@dataclass
class RelevanceGrader:
    llm: LLMService

    def relevant(self, query: str, passage: str) -> bool:
        answer = self.llm.generate(
            "Determine whether this passage is relevant to the query. "
            "Answer exactly YES or NO.\nQuery:\n" + query
            + "\nPassage:\n" + passage
        )
        if not isinstance(answer, str) or answer.strip().upper() not in {"YES", "NO"}:
            raise ValueError("Relevance grader must return YES or NO")
        return answer.strip().upper() == "YES"
