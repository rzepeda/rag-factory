"""Small deterministic relevance metrics for offline comparison."""

from typing import Sequence


def recall_at_k(found: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        raise ValueError("At least one relevant document is required")
    return len(set(found[:k]) & relevant) / len(relevant)


def reciprocal_rank_at_k(found: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    for rank, identifier in enumerate(found[:k], start=1):
        if identifier in relevant:
            return 1.0 / rank
    return 0.0
