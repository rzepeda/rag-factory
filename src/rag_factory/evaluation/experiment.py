"""Reproducible offline experiment configurations, executions, and reports.

No strategy is instantiated here: callers inject preconfigured retriever functions.
Default reports exclude wall-clock timing so identical experiments serialize alike.
Opt-in latency uses a monotonic injected clock for testability.
"""
import hashlib
import json
from dataclasses import asdict, dataclass, field
from math import isfinite
from pathlib import Path
from time import perf_counter
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from rag_factory.core.artifact_catalog import _atomic_write_json
from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.metrics import (
    _ranked_unique, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank_at_k,
)
from rag_factory.evaluation.runner import ExperimentResult


def _fingerprint(data: dict) -> str:
    source = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _strings(values, description: str) -> None:
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f"{description} must contain nonempty strings")


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    k: int
    strategies: tuple[str, ...]
    code_revision: str
    strategy_settings: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Experiment name is required")
        if type(self.k) is not int or self.k <= 0:
            raise ValueError("k must be a positive integer")
        if not isinstance(self.code_revision, str) or not self.code_revision.strip():
            raise ValueError("code_revision is required for reproducibility")
        if not isinstance(self.strategies, (tuple, list)) or not self.strategies:
            raise ValueError("At least one strategy is required")
        _strings(self.strategies, "Strategies")
        if len(set(self.strategies)) != len(self.strategies):
            raise ValueError("Duplicate experiment strategy names")
        if not isinstance(self.strategy_settings, Mapping) or not isinstance(self.metadata, Mapping):
            raise ValueError("Experiment settings and metadata must be mappings")
        if set(self.strategy_settings).difference(self.strategies):
            raise ValueError("Settings refer to an unknown strategy")
        settings = {}
        for name, params in self.strategy_settings.items():
            if not isinstance(params, Mapping):
                raise ValueError("Strategy settings must be mappings")
            _strings(params, "Setting keys")
            _strings(params.values(), "Setting values")
            settings[name] = MappingProxyType(dict(sorted(params.items())))
        _strings(self.metadata, "Metadata keys")
        _strings(self.metadata.values(), "Metadata values")
        object.__setattr__(self, "strategies", tuple(self.strategies))
        object.__setattr__(self, "strategy_settings", MappingProxyType(dict(sorted(settings.items()))))
        object.__setattr__(self, "metadata", MappingProxyType(dict(sorted(self.metadata.items()))))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "k": self.k,
            "strategies": list(self.strategies),
            "code_revision": self.code_revision,
            "strategy_settings": {
                name: dict(settings) for name, settings in self.strategy_settings.items()
            },
            "metadata": dict(self.metadata),
        }

    def save(self, path: str | Path) -> None:
        """Persist the declared strategy settings separately from run results."""
        _atomic_write_json(path, {"format_version": 1, **self.to_dict()})

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        required = {"format_version", "name", "k", "strategies", "code_revision",
                    "strategy_settings", "metadata"}
        if not isinstance(payload, dict) or set(payload) != required:
            raise ValueError("Invalid experiment configuration format")
        if type(payload["format_version"]) is not int or payload["format_version"] != 1:
            raise ValueError("Unsupported experiment configuration version")
        return cls(**{name: value for name, value in payload.items()
                      if name != "format_version"})


@dataclass(frozen=True)
class QueryEvaluation:
    query: str
    document_ids: tuple[str, ...]
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank_at_k: float
    ndcg_at_k: float
    latency_ms: float | None = None


@dataclass(frozen=True)
class StrategyEvaluation:
    summary: ExperimentResult
    queries: tuple[QueryEvaluation, ...]


@dataclass(frozen=True)
class ExperimentRun:
    dataset: str
    dataset_version: str
    dataset_sha256: str
    config: ExperimentConfig
    config_sha256: str
    results: tuple[StrategyEvaluation, ...]

    def to_dict(self) -> dict:
        return {
            "format_version": 1,
            "dataset": self.dataset,
            "dataset_version": self.dataset_version,
            "dataset_sha256": self.dataset_sha256,
            "config": self.config.to_dict(),
            "config_sha256": self.config_sha256,
            "results": [
                {
                    "summary": asdict(item.summary),
                    "queries": [
                        {**asdict(q), "document_ids": list(q.document_ids)}
                        for q in item.queries
                    ],
                }
                for item in self.results
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"

    def save(self, path: str | Path) -> None:
        _atomic_write_json(path, self.to_dict())

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentRun":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {
            "format_version", "dataset", "dataset_version", "dataset_sha256",
            "config", "config_sha256", "results",
        } or type(data["format_version"]) is not int or data["format_version"] != 1:
            raise ValueError("Invalid experiment report format")
        if not isinstance(data["config"], dict) or set(data["config"]) != {
            "name", "k", "strategies", "code_revision", "strategy_settings", "metadata",
        }:
            raise ValueError("Invalid experiment configuration")
        config = ExperimentConfig(**data["config"])
        if any(not isinstance(data[key], str) or not data[key].strip()
               for key in ("dataset", "dataset_version", "dataset_sha256", "config_sha256")):
            raise ValueError("Missing report provenance")
        if _fingerprint({"dataset_sha256": data["dataset_sha256"], "config": config.to_dict()}) != data["config_sha256"]:
            raise ValueError("Experiment configuration fingerprint mismatch")
        if not isinstance(data["results"], list):
            raise ValueError("Invalid experiment results")
        evaluations = []
        for result in data["results"]:
            if not isinstance(result, dict) or set(result) != {"summary", "queries"}:
                raise ValueError("Invalid strategy evaluation")
            summary = ExperimentResult(**result["summary"])
            if not isinstance(result["queries"], list) or not result["queries"]:
                raise ValueError("Missing per-query evaluations")
            queries = []
            for entry in result["queries"]:
                if not isinstance(entry, dict) or set(entry) != set(QueryEvaluation.__dataclass_fields__):
                    raise ValueError("Invalid query evaluation")
                ids = entry["document_ids"]
                if not isinstance(ids, list):
                    raise ValueError("Invalid ranked document IDs")
                normalized = _ranked_unique(ids, config.k)
                if normalized != ids or len(ids) > config.k:
                    raise ValueError("Invalid ranked result ordering")
                queries.append(QueryEvaluation(**{**entry, "document_ids": tuple(ids)}))
            if (summary.k != config.k or summary.queries != len(queries)
                or len(set(q.query for q in queries)) != len(queries)):
                raise ValueError("Inconsistent query evaluation summary")
            evaluations.append(StrategyEvaluation(summary, tuple(queries)))
        if [item.summary.strategy for item in evaluations] != list(config.strategies):
            raise ValueError("Experiment strategy results do not match configuration")
        return cls(
            data["dataset"], data["dataset_version"], data["dataset_sha256"],
            config, data["config_sha256"], tuple(evaluations),
        )


def run_experiment(
    dataset: EvaluationDataset,
    config: ExperimentConfig,
    retrievers: Mapping[str, Callable[[str, int], Sequence[str]]],
    *,
    capture_latency: bool = False,
    clock: Callable[[], float] = perf_counter,
) -> ExperimentRun:
    """Run each declared strategy against exactly the same sorted queries and k."""
    if not isinstance(dataset, EvaluationDataset) or not isinstance(config, ExperimentConfig):
        raise TypeError("EvaluationDataset and ExperimentConfig are required")
    if not isinstance(retrievers, Mapping):
        raise ValueError("Retrievers must be a mapping")
    if any(name not in retrievers or not callable(retrievers[name]) for name in config.strategies):
        raise ValueError("Missing callable for a configured strategy")
    evaluations = []
    for name in config.strategies:
        queries = []
        for query, grades in dataset.judgments.items():
            start = clock() if capture_latency else None
            results = list(retrievers[name](query, config.k))
            elapsed_ms = (clock() - start) * 1000 if capture_latency else None
            if elapsed_ms is not None and (not isfinite(elapsed_ms) or elapsed_ms < 0):
                raise ValueError("Clock must provide finite, monotonic durations")
            ranked = tuple(_ranked_unique(results, config.k))
            relevant = {key for key, grade in grades.items() if grade > 0}
            queries.append(QueryEvaluation(
                query=query, document_ids=ranked,
                recall_at_k=recall_at_k(ranked, relevant, config.k),
                precision_at_k=precision_at_k(ranked, relevant, config.k),
                reciprocal_rank_at_k=reciprocal_rank_at_k(ranked, relevant, config.k),
                ndcg_at_k=ndcg_at_k(ranked, grades, config.k),
                latency_ms=elapsed_ms,
            ))
        length = len(queries)
        summary = ExperimentResult(
            strategy=name, queries=length, k=config.k,
            recall_at_k=sum(q.recall_at_k for q in queries) / length,
            precision_at_k=sum(q.precision_at_k for q in queries) / length,
            mean_reciprocal_rank_at_k=sum(q.reciprocal_rank_at_k for q in queries) / length,
            mean_ndcg_at_k=sum(q.ndcg_at_k for q in queries) / length,
        )
        evaluations.append(StrategyEvaluation(summary, tuple(queries)))
    return ExperimentRun(
        dataset=dataset.name, dataset_version=dataset.version,
        dataset_sha256=dataset.sha256, config=config,
        config_sha256=_fingerprint({
            "dataset_sha256": dataset.sha256, "config": config.to_dict(),
        }), results=tuple(evaluations),
    )
