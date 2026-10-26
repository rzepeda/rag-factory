"""P1: shared metric definitions, versioned judgments, and offline reproducibility."""
from dataclasses import FrozenInstanceError
import json

import pytest

from rag_factory.evaluation.dataset import EvaluationDataset, load_dataset, save_dataset
from rag_factory.evaluation.metrics import (
    ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank_at_k,
)
from rag_factory.evaluation.runner import compare_strategies


def test_metrics_are_consistent_on_duplicate_hits_and_short_results():
    relevant = {"a", "b"}
    # The repeated "a" is counted only once; "b" is promoted into top-2.
    assert recall_at_k(["a", "a", "b"], relevant, 2) == 1.0
    assert precision_at_k(["a", "a", "b"], relevant, 2) == 1.0
    assert reciprocal_rank_at_k(["none", "b"], relevant, 2) == 0.5
    assert ndcg_at_k(["a", "a", "b"], {"a": 3, "b": 1}, 2) == 1.0
    # Fixed-k denominator penalizes missing results, even with perfect precision@1.
    assert precision_at_k(["a"], relevant, 5) == 0.2
    assert precision_at_k([], relevant, 5) == 0.0
    assert recall_at_k([], relevant, 5) == 0.0
    assert reciprocal_rank_at_k([], relevant, 5) == 0.0
    assert ndcg_at_k([], {"a": 1}, 5) == 0.0


@pytest.mark.parametrize("k", [0, -1, True, 2.5, "3"])
def test_metrics_reject_invalid_k(k):
    for metric, relevance in (
        (recall_at_k, {"a"}),
        (precision_at_k, {"a"}),
        (reciprocal_rank_at_k, {"a"}),
        (ndcg_at_k, {"a": 1}),
    ):
        with pytest.raises(ValueError, match="positive"):
            metric(["a"], relevance, k)


def test_metrics_reject_invalid_rankings_and_grades():
    with pytest.raises(ValueError, match="document IDs"):
        precision_at_k([""], {"a"}, 1)
    with pytest.raises(ValueError, match="document IDs"):
        recall_at_k(["a", 9], {"a"}, 2)
    with pytest.raises(ValueError, match="nonnegative"):
        ndcg_at_k(["a"], {"a": -1}, 1)
    with pytest.raises(ValueError, match="nonnegative"):
        ndcg_at_k(["a"], {"a": True}, 1)


def test_compare_reports_all_four_aggregates():
    results = compare_strategies(
        {"lexical": lambda q, k: ["a"]},
        {"q1": {"a": 2, "b": 1}, "q2": {"b": 1}},
        k=2,
    )
    result = results[0]
    assert result.queries == 2
    assert result.k == 2
    assert result.recall_at_k == 0.25
    assert result.precision_at_k == 0.25
    assert result.mean_reciprocal_rank_at_k == 0.5
    assert 0 < result.mean_ndcg_at_k < 1


def test_dataset_roundtrip_fingerprint_order_and_immutability(tmp_path):
    source = {"q2": {"b": 2}, "q1": {"a": 3, "irrelevant": 0}}
    dataset = EvaluationDataset("animals", "v1", source)
    fingerprint = dataset.sha256
    source["q2"]["b"] = 999
    assert dataset.judgments["q2"]["b"] == 2
    with pytest.raises(TypeError):
        dataset.judgments["q2"]["b"] = 4
    with pytest.raises(FrozenInstanceError):
        dataset.version = "v2"
    equivalent = EvaluationDataset("animals", "v1", {
        "q1": {"irrelevant": 0, "a": 3}, "q2": {"b": 2}
    })
    assert equivalent.sha256 == fingerprint
    filename = tmp_path / "judgments.json"
    save_dataset(filename, dataset)
    loaded = load_dataset(filename)
    assert loaded == equivalent
    assert loaded.sha256 == fingerprint
    assert json.loads(filename.read_text())["format_version"] == 1
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("document", [
    {"format_version": 2, "name": "x", "version": "1", "judgments": {"q": {"a": 1}}},
    {"format_version": 1, "name": "x", "version": "1", "judgments": {"q": {"a": 1}}, "extra": 1},
    {"format_version": 1, "name": "x", "version": "1", "judgments": {"q": {"a": 0}}},
    {"format_version": 1, "name": "x", "version": "1", "judgments": {"q": {"a": True}}},
])
def test_bad_dataset_file_rejected(tmp_path, document):
    filename = tmp_path / "bad.json"
    filename.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        load_dataset(filename)


def test_dataset_atomic_save_preserves_previous_version(tmp_path, monkeypatch):
    path = tmp_path / "dataset.json"
    old = EvaluationDataset("test", "v1", {"q": {"a": 1}})
    old.save(path)
    monkeypatch.setattr("rag_factory.core.artifact_catalog.os.replace",
                        lambda *args: (_ for _ in ()).throw(OSError("disk failure")))
    with pytest.raises(OSError, match="disk failure"):
        EvaluationDataset("test", "v2", {"q": {"b": 1}}).save(path)
    assert load_dataset(path) == old
    assert not list(tmp_path.glob("*.tmp"))
