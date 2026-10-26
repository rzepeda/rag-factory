"""Offline, reproducible metric deltas across two compatible experiment runs.

Comparisons are informational by default. An explicit quality gate is opt-in.
A negative delta indicates that a higher-is-better retrieval score regressed.
"""
import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping

from rag_factory.core.artifact_catalog import _atomic_write_json
from rag_factory.evaluation.experiment import ExperimentRun


METRICS = (
    "recall_at_k", "precision_at_k",
    "mean_reciprocal_rank_at_k", "mean_ndcg_at_k",
)


@dataclass(frozen=True)
class MetricChange:
    metric: str
    baseline: float
    candidate: float
    delta: float
    regression: bool


@dataclass(frozen=True)
class StrategyChange:
    strategy: str
    metrics: tuple[MetricChange, ...]
    baseline_latency_ms: float | None = None
    candidate_latency_ms: float | None = None


@dataclass(frozen=True)
class ExperimentComparison:
    dataset: str
    version: str
    dataset_sha256: str
    k: int
    baseline_revision: str
    candidate_revision: str
    changes: tuple[StrategyChange, ...]

    @property
    def regressions(self) -> tuple[str, ...]:
        return tuple(
            f"{change.strategy}.{metric.metric}"
            for change in self.changes
            for metric in change.metrics if metric.regression
        )

    def require_no_regressions(self) -> None:
        """Optional quality gate; never called implicitly during evaluation."""
        if self.regressions:
            raise AssertionError("Retrieval quality regressions: " + ", ".join(self.regressions))

    def to_dict(self) -> dict:
        return {"format_version": 1, **asdict(self), "regressions": list(self.regressions)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, allow_nan=False) + "\n"

    def save(self, path: str | Path) -> None:
        _atomic_write_json(path, self.to_dict())


def _mean_latency(evaluation) -> float | None:
    values = [q.latency_ms for q in evaluation.queries]
    return sum(values) / len(values) if values and all(x is not None for x in values) else None


def compare_runs(
    baseline: ExperimentRun,
    candidate: ExperimentRun,
    *,
    tolerated_drops: Mapping[str, float] | None = None,
) -> ExperimentComparison:
    """Compare matching datasets, cutoff k, strategy names and query sets."""
    if not isinstance(baseline, ExperimentRun) or not isinstance(candidate, ExperimentRun):
        raise TypeError("ExperimentRun values are required")
    if ((baseline.dataset, baseline.dataset_version, baseline.dataset_sha256, baseline.config.k)
        != (candidate.dataset, candidate.dataset_version, candidate.dataset_sha256, candidate.config.k)):
        raise ValueError("Incompatible evaluation dataset fingerprint, version or k")
    baseline_by_name = {r.summary.strategy: r for r in baseline.results}
    candidate_by_name = {r.summary.strategy: r for r in candidate.results}
    if not baseline_by_name or set(baseline_by_name) != set(candidate_by_name):
        raise ValueError("Strategy names must match for cross-version comparison")
    thresholds = {} if tolerated_drops is None else tolerated_drops
    if not isinstance(thresholds, Mapping) or set(thresholds) - set(METRICS):
        raise ValueError("Unknown regression tolerance metric")
    for metric, tolerance in thresholds.items():
        if (type(tolerance) not in (float, int) or not isfinite(tolerance)
            or tolerance < 0):
            raise ValueError(f"Invalid regression tolerance for {metric}")
    changes = []
    for strategy in sorted(baseline_by_name):
        old = baseline_by_name[strategy]
        new = candidate_by_name[strategy]
        if ({q.query for q in old.queries} != {q.query for q in new.queries}
            or len(old.queries) != len(new.queries)):
            raise ValueError("Comparisons require identical evaluated queries")
        metrics = []
        for metric in METRICS:
            previous = getattr(old.summary, metric)
            current = getattr(new.summary, metric)
            if not all(isfinite(value) for value in (previous, current)):
                raise ValueError("Comparison scores must be finite")
            delta = current - previous
            metrics.append(MetricChange(
                metric, previous, current, delta, delta < -thresholds.get(metric, 0.0),
            ))
        changes.append(StrategyChange(
            strategy=strategy,
            metrics=tuple(metrics),
            baseline_latency_ms=_mean_latency(old),
            candidate_latency_ms=_mean_latency(new),
        ))
    return ExperimentComparison(
        dataset=baseline.dataset, version=baseline.dataset_version,
        dataset_sha256=baseline.dataset_sha256,
        k=baseline.config.k,
        baseline_revision=baseline.config.code_revision,
        candidate_revision=candidate.config.code_revision,
        changes=tuple(changes),
    )
