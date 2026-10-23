"""Versioned offline judgments, graded ranking quality and stable reports."""

import json

import pytest

from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.report import EvaluationReport
from rag_factory.evaluation.runner import compare_strategies
from rag_factory.evaluation.metrics import ndcg_at_k


def test_graded_ndcg_orders_more_relevant_first():
    grades = {"a": 3, "b": 1, "c": 0}
    assert ndcg_at_k(["a", "b"], grades, 2) == 1.0
    assert ndcg_at_k(["b", "a"], grades, 2) < 1.0
    assert ndcg_at_k(["c"], grades, 1) == 0.0


def test_versioned_evaluation_and_deterministic_json(tmp_path):
    dataset = EvaluationDataset("toy", "1", {
        "animal": {"cat": 3, "dog": 1},
        "planet": {"mars": 2, "cat": 0},
    })
    strategies = {
        "baseline": lambda query, k: (["dog", "cat"] if query == "animal" else ["cat", "mars"])[:k],
        "better": lambda query, k: (["cat", "dog"] if query == "animal" else ["mars", "cat"])[:k],
    }
    results = compare_strategies(strategies, dataset.judgments, k=2)
    assert results[1].mean_ndcg_at_k > results[0].mean_ndcg_at_k
    report = EvaluationReport(dataset.name, dataset.version, 2, tuple(results),
                              {"code_revision": "test-commit", "provider": "mock"})
    filename = tmp_path / "report.json"
    report.save(filename)
    assert filename.read_text() == report.to_json()
    assert json.loads(filename.read_text())["dataset"] == "toy"


def test_invalid_grades_rejected():
    with pytest.raises(ValueError, match="nonnegative integers"):
        EvaluationDataset("toy", "1", {"q": {"a": -1}})
    with pytest.raises(ValueError, match="positively relevant"):
        EvaluationDataset("toy", "1", {"q": {"a": 0}})
    with pytest.raises(ValueError, match="positive"):
        ndcg_at_k(["a"], {"a": 1}, 0)
