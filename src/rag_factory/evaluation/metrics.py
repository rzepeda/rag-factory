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

def ndcg_at_k(found: Sequence[str], grades: dict[str, int], k: int) -> float:
    """Graded normalized discounted cumulative gain (binary grades also work)."""
    import math

    if k <= 0:
        raise ValueError("k must be positive")
    def dcg(values):
        return sum((2 ** grade - 1) / math.log2(rank + 2)
                   for rank, grade in enumerate(values))
    observed = dcg([grades.get(identifier, 0) for identifier in found[:k]])
    ideal = dcg(sorted(grades.values(), reverse=True)[:k])
    return observed / ideal if ideal else 0.0
