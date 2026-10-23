"""Small offline experiment runner over fixed query judgments."""

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from rag_factory.evaluation.metrics import recall_at_k, reciprocal_rank_at_k, ndcg_at_k


@dataclass(frozen=True)
class ExperimentResult:
    strategy: str
    queries: int
    recall_at_k: float
    mean_reciprocal_rank_at_k: float
    k: int
    mean_ndcg_at_k: float = 0.0


def compare_strategies(
    strategies: Mapping[str, Callable[[str, int], Sequence[str]]],
    judgments: Mapping[str, set[str] | Mapping[str, int]],
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
        ndcgs = []
        for query, relevance in judgments.items():
            grades = ({key: 1 for key in relevance} if isinstance(relevance, set)
                      else dict(relevance))
            relevant = {key for key, grade in grades.items() if grade > 0}
            ranked = list(retrieve(query, k))
            recalls.append(recall_at_k(ranked, relevant, k))
            reciprocal_ranks.append(reciprocal_rank_at_k(ranked, relevant, k))
            ndcgs.append(ndcg_at_k(ranked, grades, k))
        results.append(ExperimentResult(
            strategy=name,
            queries=len(judgments),
            recall_at_k=sum(recalls) / len(recalls),
            mean_reciprocal_rank_at_k=sum(reciprocal_ranks) / len(reciprocal_ranks),
            k=k,
            mean_ndcg_at_k=sum(ndcgs) / len(ndcgs),
        ))
    return results
