"""Explicit strategy registry and independent retrieval composition.

A strategy is registered once as a factory receiving validated parameters.
Callers can select and compose named implementations without editing algorithms.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from rag_factory.pipelines.retrieval import RetrievalPipeline, RetrievalSource


class Retriever(Protocol):
    def retrieve(self, query: str, limit: int = 5) -> list[str]: ...


Builder = Callable[[Mapping[str, Any]], Retriever]


@dataclass(frozen=True)
class StrategyConfig:
    implementation: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


class StrategyRegistry:
    def __init__(self):
        self._builders: dict[str, Builder] = {}

    def register(self, name: str, builder: Builder) -> None:
        if not name.strip() or name in self._builders:
            raise ValueError(f"Invalid or duplicate strategy: {name!r}")
        self._builders[name] = builder

    def build(self, config: StrategyConfig) -> Retriever:
        if config.implementation not in self._builders:
            raise ValueError(f"Unknown retrieval strategy: {config.implementation}")
        retriever = self._builders[config.implementation](config.parameters)
        if not callable(getattr(retriever, "retrieve", None)):
            raise TypeError("Strategy must implement retrieve(query, limit)")
        return retriever

    def compose(self, strategies: Mapping[str, StrategyConfig]) -> RetrievalPipeline:
        if not strategies:
            raise ValueError("At least one retrieval strategy is required")
        # Validate all names before any constructor side effects.
        for name, config in strategies.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Strategy instance names must be nonempty")
            if config.implementation not in self._builders:
                raise ValueError(f"Unknown retrieval strategy: {config.implementation}")
        sources = tuple(
            RetrievalSource(name, self.build(config).retrieve)
            for name, config in strategies.items()
        )
        return RetrievalPipeline(sources)
