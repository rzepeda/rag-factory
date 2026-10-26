"""P1: reproducible experiment artifacts and advisory cross-version comparisons."""
import json

import pytest

from rag_factory.evaluation.comparison import compare_runs
from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.experiment import (
    ExperimentConfig, ExperimentRun, run_experiment,
)
from rag_factory.factory.unified import UnifiedConfiguration, build_unified
from tests.unit.core.test_unified_all_strategies import setup, spec


def dataset():
    return EvaluationDataset("animals", "v1", {
        "cats": {"cat": 3, "dog": 0},
        "dogs": {"dog": 2, "cat": 0},
    })


def config(revision, *, names=("lexical",), k=2):
    return ExperimentConfig(
        name="offline-regression", k=k, strategies=names, code_revision=revision,
        strategy_settings={"lexical": {"kind": "keyword", "store": "memory"}},
        metadata={"provider": "mock", "dataset_source": "checked-in"},
    )


def test_reports_are_stable_and_comparable_after_json_reload(tmp_path):
    records = dataset()
    retrieval = {"lexical": lambda query, k: (["cat", "dog"] if query == "cats"
                                               else ["dog", "cat"])[:k]}
    run = run_experiment(records, config("baseline-sha"), retrieval)
    again = run_experiment(
        EvaluationDataset("animals", "v1", {
            "dogs": {"cat": 0, "dog": 2},
            "cats": {"dog": 0, "cat": 3},
        }),
        config("baseline-sha"),
        retrieval,
    )
    assert run.to_json() == again.to_json()
    assert run.dataset_sha256 == records.sha256
    assert run.config_sha256 == again.config_sha256
    assert len(run.results[0].queries) == 2
    assert run.results[0].queries[0].query == "cats"
    assert run.results[0].summary.recall_at_k == 1.0
    assert run.results[0].summary.precision_at_k == 0.5

    report = tmp_path / "experiment.json"
    run.save(report)
    loaded = ExperimentRun.load(report)
    assert loaded.to_json() == run.to_json()
    assert loaded.config.code_revision == "baseline-sha"
    assert json.loads(report.read_text())["format_version"] == 1
    comparison = compare_runs(loaded, again)
    assert comparison.regressions == ()
    comparison.require_no_regressions()


def test_regression_detection_tolerance_and_explicit_gate(tmp_path):
    old = run_experiment(dataset(), config("original"), {
        "lexical": lambda q, k: ["cat"] if q == "cats" else ["dog"],
    })
    new = run_experiment(dataset(), config("modified"), {
        "lexical": lambda q, k: ["other", "cat"] if q == "cats" else [],
    })
    comparison = compare_runs(old, new)
    assert set(comparison.regressions) == {
        "lexical.recall_at_k",
        "lexical.precision_at_k",
        "lexical.mean_reciprocal_rank_at_k",
        "lexical.mean_ndcg_at_k",
    }
    assert comparison.baseline_revision == "original"
    assert comparison.candidate_revision == "modified"
    assert all(metric.delta < 0 for metric in comparison.changes[0].metrics)
    comparison.save(tmp_path / "comparison.json")
    assert json.loads((tmp_path / "comparison.json").read_text())["regressions"]
    with pytest.raises(AssertionError, match="Retrieval quality regressions"):
        comparison.require_no_regressions()

    tolerated = compare_runs(old, new, tolerated_drops={
        "recall_at_k": 1.0, "precision_at_k": 1.0,
        "mean_reciprocal_rank_at_k": 1.0, "mean_ndcg_at_k": 1.0,
    })
    assert tolerated.regressions == ()
    tolerated.require_no_regressions()


def test_compare_rejects_different_datasets_and_k():
    first = run_experiment(dataset(), config("a"), {"lexical": lambda q, k: []})
    changed_dataset = EvaluationDataset("animals", "v1", {
        "cats": {"different": 1},
        "dogs": {"dog": 2},
    })
    second = run_experiment(changed_dataset, config("b"), {
        "lexical": lambda q, k: [],
    })
    with pytest.raises(ValueError, match="Incompatible"):
        compare_runs(first, second)
    third = run_experiment(dataset(), config("b", k=1), {
        "lexical": lambda q, k: [],
    })
    with pytest.raises(ValueError, match="Incompatible"):
        compare_runs(first, third)
    with pytest.raises(ValueError, match="tolerance"):
        compare_runs(first, first, tolerated_drops={"precision_at_k": -1})
    with pytest.raises(ValueError, match="tolerance"):
        compare_runs(first, first, tolerated_drops={"other_metric": 0.1})


def test_explicit_latency_measurement_with_mock_clock():
    times = iter([1.0, 1.012, 2.0, 2.034])
    result = run_experiment(
        dataset(), config("timed"), {"lexical": lambda q, k: ["cat"]},
        capture_latency=True, clock=lambda: next(times),
    )
    assert [round(query.latency_ms) for query in result.results[0].queries] == [12, 34]
    stable = run_experiment(dataset(), config("timed"), {
        "lexical": lambda q, k: ["cat"]
    })
    assert all(query.latency_ms is None for query in stable.results[0].queries)
    comparison = compare_runs(result, result)
    assert comparison.changes[0].baseline_latency_ms == pytest.approx(23.0)
    assert comparison.changes[0].candidate_latency_ms == pytest.approx(23.0)


def test_invalid_configurations_and_rankings_fail_fast():
    with pytest.raises(ValueError, match="code_revision"):
        config("")
    with pytest.raises(ValueError, match="Duplicate"):
        config("rev", names=("lexical", "lexical"))
    with pytest.raises(ValueError, match="positive"):
        config("rev", k=True)
    with pytest.raises(ValueError, match="unknown strategy"):
        ExperimentConfig(
            "example", 2, ("lexical",), "rev",
            strategy_settings={"not-registered": {"x": "y"}},
        )
    with pytest.raises(ValueError, match="Missing callable"):
        run_experiment(dataset(), config("rev"), {})
    with pytest.raises(ValueError, match="document IDs"):
        run_experiment(dataset(), config("rev"), {"lexical": lambda q, k: [""]})


def test_experiment_report_validation_and_atomicity(tmp_path, monkeypatch):
    run = run_experiment(dataset(), config("rev"), {"lexical": lambda q, k: ["cat"]})
    path = tmp_path / "experiment.json"
    run.save(path)
    original = path.read_text()
    data = json.loads(original)
    data["config_sha256"] = "bad"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="fingerprint"):
        ExperimentRun.load(path)
    path.write_text(original)
    monkeypatch.setattr("rag_factory.core.artifact_catalog.os.replace",
                        lambda *args: (_ for _ in ()).throw(OSError("disk error")))
    with pytest.raises(OSError, match="disk error"):
        run.save(path)
    assert path.read_text() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_experiment_runs_over_unified_offline_pipeline(tmp_path):
    registry, services = setup()
    spec_config = UnifiedConfiguration(services, {
        "lexical": spec("keyword", ["keyword_store"],
                        ["keyword_store", "tokenizer"]),
    })
    with build_unified(spec_config, registry) as pipeline:
        pipeline.index("lexical", {"documents": {
            "cat": "cats purr", "dog": "dogs bark",
        }})
        evaluation = run_experiment(
            EvaluationDataset("animals", "1", {
                "cats": {"cat": 3}, "dogs": {"dog": 3},
            }),
            ExperimentConfig(
                "keyword-smoke", 2, ("lexical",), "dev-offline",
                strategy_settings={"lexical": {"kind": "keyword"}},
            ),
            {"lexical": lambda q, k: [
                hit.document_id for hit in pipeline.retrieve("lexical", q, k)
            ]},
        )
        assert evaluation.results[0].summary.recall_at_k == 1.0
        evaluation.save(tmp_path / "offline-experiment.json")
        assert ExperimentRun.load(tmp_path / "offline-experiment.json").to_json() == evaluation.to_json()


def test_standalone_config_and_checked_in_example(tmp_path):
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    checked_in = root / "examples" / "evaluation"
    example_dataset = EvaluationDataset.load(checked_in / "animals.v1.json")
    example_config = ExperimentConfig.load(checked_in / "experiment.v1.json")
    assert len(example_dataset.judgments) == 3
    assert example_config.strategies == ("lexical", "fusion")
    assert example_config.k == 3

    filename = tmp_path / "config.json"
    example_config.save(filename)
    assert ExperimentConfig.load(filename) == example_config
    assert ExperimentConfig.load(filename).to_dict() == example_config.to_dict()

    output = subprocess.run(
        [sys.executable, str(root / "examples" / "offline_evaluation_example.py")],
        capture_output=True, text=True, cwd=root, check=True,
    )
    assert "Dataset: offline-animals v1" in output.stdout
    assert "Precision@3" in output.stdout


def test_config_format_version_checked(tmp_path):
    path = tmp_path / "config.json"
    config("revision").save(path)
    data = json.loads(path.read_text())
    data["format_version"] = 2
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="version"):
        ExperimentConfig.load(path)
