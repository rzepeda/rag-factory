"""Ephemeral directed graph store; neighbors are stable and deduplicated."""
from dataclasses import dataclass, field

@dataclass
class MemoryGraphStore:
    edges: dict[str, set[str]] = field(default_factory=dict)

    def add_edge(self, source: str, target: str) -> None:
        if not source or not target:
            raise ValueError("Graph endpoints must be nonempty")
        self.edges.setdefault(source, set()).add(target)

    def neighbors(self, node: str) -> list[str]:
        return sorted(self.edges.get(node, ()))
