"""Bounded, allowlisted LLM-directed retrieval routing (offline baseline)."""

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from rag_factory.core.interfaces.services import LLMService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


REQUIREMENTS = StrategyRequirements(
    retrieval=(ServiceRequirement("llm", frozenset({"generate"})),)
)


@dataclass
class AgenticRAGRetriever:
    """Choose an allowlisted retrieval tool, then invoke it with bounded rounds.

    The LLM returns a tool name only. It cannot provide executable code,
    parameters, file paths or arbitrary tool arguments.
    """

    llm: LLMService
    tools: Mapping[str, Callable[[str, int], Sequence[str]]]
    max_steps: int = 2

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0 or self.max_steps <= 0:
            raise ValueError("limit and max_steps must be positive")
        if not self.tools or any(
            not isinstance(name, str) or not name.strip() or not callable(tool)
            for name, tool in self.tools.items()
        ):
            raise ValueError("Tools must map nonempty names to retrieval callables")
        if not query.strip():
            return []
        seen: set[str] = set()
        results: list[str] = []
        available = sorted(self.tools)
        for _ in range(min(self.max_steps, len(available))):
            options = [name for name in available if name not in seen]
            if not options:
                break
            prompt = (
                "Select exactly one retrieval tool name from: "
                + ", ".join(options)
                + "\nRespond only with the tool name.\nQuery:\n"
                + query
            )
            choice = self.llm.generate(prompt)
            if not isinstance(choice, str) or choice.strip() not in options:
                raise ValueError("LLM selected an unknown or unavailable retrieval tool")
            selected = choice.strip()
            seen.add(selected)
            for identifier in self.tools[selected](query, limit):
                if not isinstance(identifier, str) or not identifier.strip():
                    raise ValueError("Retrieval tools must return nonempty document IDs")
                if identifier not in results:
                    results.append(identifier)
                    if len(results) == limit:
                        return results
        return results
