"""Explicit, sequential indexing composition independent of retrieval."""

from dataclasses import dataclass
from typing import Callable, Mapping


@dataclass(frozen=True)
class IndexStep:
    name: str
    run: Callable[[Mapping[str, str]], object]


@dataclass
class IndexingPipeline:
    steps: tuple[IndexStep, ...]

    def run(self, documents: Mapping[str, str]) -> dict[str, object]:
        if not self.steps or len({s.name for s in self.steps}) != len(self.steps):
            raise ValueError("Indexing steps must have unique names and be nonempty")
        return {step.name: step.run(documents) for step in self.steps}
