"""Registered provider implementations and configured instance construction.

Registry is explicitly populated; importing it does not load provider SDKs.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from rag_factory.core.service_contracts import ProviderDescriptor


@dataclass(frozen=True)
class ServiceConfig:
    interface: str
    implementation: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    def __init__(self):
        self._providers: dict[tuple[str, str], tuple[ProviderDescriptor, Callable[..., object]]] = {}

    def register(self, descriptor: ProviderDescriptor, constructor: Callable[..., object]) -> None:
        key = (descriptor.interface, descriptor.implementation)
        if key in self._providers:
            raise ValueError(f"Duplicate provider registration: {key}")
        self._providers[key] = (descriptor, constructor)

    def resolve(self, config: ServiceConfig) -> tuple[ProviderDescriptor, object]:
        key = (config.interface, config.implementation)
        if key not in self._providers:
            raise ValueError(f"Unknown provider: {key}")
        descriptor, constructor = self._providers[key]
        return descriptor, constructor(**config.parameters)


def default_registry() -> ServiceRegistry:
    """Only adapters requiring no external infrastructure are built in."""
    from rag_factory.services.keyword.memory import MemoryKeywordStore
    from rag_factory.services.tokenizer.regex import RegexTokenizer

    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("keyword_store", "memory", frozenset({"upsert", "search"})),
        MemoryKeywordStore,
    )
    registry.register(
        ProviderDescriptor("tokenizer", "regex", frozenset({"tokenize"})),
        RegexTokenizer,
    )
    return registry
