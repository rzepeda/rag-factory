"""Compose independent retrievers through an explicit shared call signature."""

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class RetrievalSource:
    name: str
    search: Callable[[str, int], Sequence[str]]


@dataclass
class RetrievalPipeline:
    sources: tuple[RetrievalSource, ...]

    def search(self, query: str, limit: int = 5) -> dict[str, list[str]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if not self.sources or len({s.name for s in self.sources}) != len(self.sources):
            raise ValueError("Retrieval sources must have unique names and be nonempty")
        return {source.name: list(source.search(query, limit)) for source in self.sources}
