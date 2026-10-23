"""Immutable validated child-to-parent hierarchy declarations."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Hierarchy:
    child_to_parent: Mapping[str, str]

    def __post_init__(self):
        if not self.child_to_parent:
            raise ValueError("Hierarchy requires child relationships")
        for child, parent in self.child_to_parent.items():
            if not isinstance(child, str) or not child.strip() or not isinstance(parent, str) or not parent.strip():
                raise ValueError("Hierarchy identifiers must be nonempty strings")
            if child == parent:
                raise ValueError("A child cannot be its own parent")

    def parent_of(self, child: str) -> str:
        if child not in self.child_to_parent:
            raise ValueError(f"Unknown child: {child}")
        return self.child_to_parent[child]
