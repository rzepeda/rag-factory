"""Small offline experiment runner over fixed query judgments."""

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from rag_factory.evaluation.metrics import recall_at_k, reciprocal_rank_at_k


@dataclass(frozen=True)
class ExperimentResult:
    strategy: str
    queries: int
    recall_at_k: float
    mean_reciprocal_rank_at_k: float
    k: int


def compare_strategies(
    strategies: Mapping[str, Callable[[str, int], Sequence[str]]],
    judgments: Mapping[str, set[str]],
    k: int = 5,
) -> list[ExperimentResult]:
    """Calculate aggregate relevance metrics; no networking or runtime effects."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not strategies or not judgments:
        raise ValueError("Strategies and relevance judgments are required")
    if any(not relevant for relevant in judgments.values()):
        raise ValueError("Every query needs at least one relevant document")
    results = []
    for name, retrieve in strategies.items():
        recalls = []
        reciprocal_ranks = []
        for query, relevant in judgments.items():
            ranked = list(retrieve(query, k))
            recalls.append(recall_at_k(ranked, relevant, k))
            reciprocal_ranks.append(reciprocal_rank_at_k(ranked, relevant, k))
        results.append(ExperimentResult(
            strategy=name,
            queries=len(judgments),
            recall_at_k=sum(recalls) / len(recalls),
            mean_reciprocal_rank_at_k=sum(reciprocal_ranks) / len(reciprocal_ranks),
            k=k,
        ))
    return results
