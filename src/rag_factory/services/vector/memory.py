"""Ephemeral Euclidean vector index for offline development, not production."""
from dataclasses import dataclass, field
from typing import Mapping, Sequence
from math import isfinite

@dataclass
class MemoryVectorStore:
    vectors: dict[str, tuple[float, ...]] = field(default_factory=dict)

    def upsert(self, records: Mapping[str, Sequence[float]]) -> None:
        for identifier, values in records.items():
            vector = tuple(values)
            if not identifier or not vector or any(not isfinite(x) for x in vector):
                raise ValueError("Vector records require identifiers and finite coordinates")
            if self.vectors and len(vector) != len(next(iter(self.vectors.values()))):
                raise ValueError("Incompatible vector dimensions")
            self.vectors[identifier] = vector

    def search(self, vector: Sequence[float], limit: int) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if any(len(value) != len(vector) for value in self.vectors.values()):
            raise ValueError("Incompatible vector dimensions")
        return sorted(
            self.vectors, key=lambda key: (
                sum((a-b)**2 for a, b in zip(self.vectors[key], vector)), key
            )
        )[:limit]
