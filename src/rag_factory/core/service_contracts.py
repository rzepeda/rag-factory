"""Provider-independent declarations for strategy service requirements.

This module is intentionally small: it does not connect to, instantiate,
or provision external infrastructure.
"""

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class ServiceRequirement:
    """A capability required by a strategy at a particular lifecycle stage."""

    interface: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.interface.strip():
            raise ValueError("Service interface name must not be empty")


@dataclass(frozen=True)
class ProviderDescriptor:
    """Metadata supplied by a registered adapter implementation."""

    interface: str
    implementation: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.interface.strip() or not self.implementation.strip():
            raise ValueError("Provider interface and implementation are required")

    def satisfies(self, requirement: ServiceRequirement) -> bool:
        return (
            self.interface == requirement.interface
            and requirement.capabilities.issubset(self.capabilities)
        )


@dataclass(frozen=True)
class StrategyRequirements:
    """Distinct service requirements for indexing and retrieval."""

    indexing: tuple[ServiceRequirement, ...] = ()
    retrieval: tuple[ServiceRequirement, ...] = ()
