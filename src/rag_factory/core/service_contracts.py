"""Provider-neutral capability declarations. No infrastructure is started."""

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping


@dataclass(frozen=True)
class ServiceRequirement:
    """Required interface and operations for a strategy stage."""

    interface: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.interface, str) or not self.interface.strip():
            raise ValueError("Service interface name must not be empty")
        if any(not isinstance(c, str) or not c.strip() for c in self.capabilities):
            raise ValueError("Capability names must be nonempty strings")


@dataclass(frozen=True)
class ProviderDescriptor:
    """Declared contract support of an adapter, not proof of connectivity."""

    interface: str
    implementation: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.interface, str) or not self.interface.strip():
            raise ValueError("Provider interface name must not be empty")
        if not isinstance(self.implementation, str) or not self.implementation.strip():
            raise ValueError("Provider implementation name must not be empty")
        if any(not isinstance(c, str) or not c.strip() for c in self.capabilities):
            raise ValueError("Capability names must be nonempty strings")

    def satisfies(self, requirement: ServiceRequirement) -> bool:
        return self.interface == requirement.interface and requirement.capabilities.issubset(self.capabilities)


@dataclass(frozen=True)
class StrategyRequirements:
    """Indexing and retrieval requirements are independent."""

    indexing: tuple[ServiceRequirement, ...] = ()
    retrieval: tuple[ServiceRequirement, ...] = ()

    def for_stage(self, stage: str) -> tuple[ServiceRequirement, ...]:
        if stage == "indexing":
            return self.indexing
        if stage == "retrieval":
            return self.retrieval
        raise ValueError(f"Unknown stage: {stage}")


def validate_service_bindings(
    requirements: tuple[ServiceRequirement, ...],
    bindings: Mapping[str, str],
    providers: Mapping[str, ProviderDescriptor],
) -> None:
    """Validate logical interface -> configured instance names and capabilities.

    Does not instantiate a service or verify provider endpoint reachability.
    """
    for requirement in requirements:
        instance_name = bindings.get(requirement.interface)
        if instance_name is None or instance_name not in providers:
            raise ValueError(f"Missing configured service: {requirement.interface}")
        if not providers[instance_name].satisfies(requirement):
            raise ValueError(
                f"Service {instance_name} does not satisfy {requirement.interface} "
                f"capabilities: {', '.join(sorted(requirement.capabilities))}"
            )
