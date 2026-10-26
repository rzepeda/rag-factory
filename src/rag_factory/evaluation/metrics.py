"""Deterministic information-retrieval metrics with consistent top-k semantics.

All metrics de-duplicate ranked document IDs in first-occurrence order before
applying k. Missing judgments imply grade zero; a positive grade is relevant.
Precision@k uses k as the denominator, even when fewer results are returned.
"""

from math import log2
from typing import Mapping, Sequence


def _validated_k(k: int) -> None:
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")


def _ranked_unique(found: Sequence[str], k: int) -> list[str]:
    _validated_k(k)
    if isinstance(found, (str, bytes)):
        raise ValueError("Rankings must be sequences of document IDs")
    ranked = []
    seen = set()
    for identifier in found:
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Rankings must contain nonempty string document IDs")
        if identifier not in seen:
            seen.add(identifier)
            ranked.append(identifier)
            if len(ranked) == k:
                break
    return ranked


def _positive_relevance(relevant: set[str]) -> None:
    if not isinstance(relevant, (set, frozenset)) or not relevant:
        raise ValueError("At least one relevant document is required")
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in relevant):
        raise ValueError("Relevance IDs must be nonempty strings")


def recall_at_k(found: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of all relevant documents retrieved among the first k unique IDs."""
    _positive_relevance(relevant)
    return len(set(_ranked_unique(found, k)) & relevant) / len(relevant)


def precision_at_k(found: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of k slots containing a relevant document (missing slots count as misses)."""
    _positive_relevance(relevant)
    return len(set(_ranked_unique(found, k)) & relevant) / k


def reciprocal_rank_at_k(found: Sequence[str], relevant: set[str], k: int) -> float:
    """Reciprocal rank of the first relevant item, or zero if none was retrieved."""
    _positive_relevance(relevant)
    for rank, identifier in enumerate(_ranked_unique(found, k), start=1):
        if identifier in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(found: Sequence[str], grades: Mapping[str, int], k: int) -> float:
    """Graded nDCG with gain 2**grade - 1 and log2(rank + 1) discount."""
    _validated_k(k)
    if not isinstance(grades, Mapping) or not grades:
        raise ValueError("Graded relevance judgments are required")
    if any(not isinstance(identifier, str) or not identifier.strip()
           or type(grade) is not int or grade < 0 for identifier, grade in grades.items()):
        raise ValueError("Grades must map nonempty IDs to nonnegative integers")

    def dcg(values):
        return sum((2 ** grade - 1) / log2(rank + 2)
                   for rank, grade in enumerate(values))

    observed = dcg([grades.get(identifier, 0) for identifier in _ranked_unique(found, k)])
    ideal = dcg(sorted(grades.values(), reverse=True)[:k])
    return observed / ideal if ideal else 0.0
