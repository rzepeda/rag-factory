"""Comparative offline evaluation with fixed judgments."""

import pytest

from rag_factory.evaluation.runner import compare_strategies


def test_compare_strategies_with_shared_relevance_judgments():
    results = compare_strategies(
        {
            "baseline": lambda query, k: ["irrelevant", "doc-a"][:k],
            "expanded": lambda query, k: ["doc-a", "doc-b"][:k],
        },
        {"find a": {"doc-a"}, "find b": {"doc-b"}},
        k=2,
    )
    baseline, expanded = results
    assert baseline.queries == 2
    assert baseline.recall_at_k == expanded.recall_at_k == 1.0
    assert expanded.mean_reciprocal_rank_at_k > baseline.mean_reciprocal_rank_at_k


def test_evaluation_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="positive"):
        compare_strategies({"s": lambda q, k: []}, {"q": {"a"}}, 0)
    with pytest.raises(ValueError, match="required"):
        compare_strategies({}, {"q": {"a"}})
    with pytest.raises(ValueError, match="relevant"):
        compare_strategies({"s": lambda q, k: []}, {"q": set()})
