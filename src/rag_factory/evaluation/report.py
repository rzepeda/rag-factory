"""Portable deterministic JSON reports for offline experiments."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from rag_factory.evaluation.runner import ExperimentResult


@dataclass(frozen=True)
class EvaluationReport:
    dataset: str
    version: str
    k: int
    results: tuple[ExperimentResult, ...]
    metadata: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2) + "\n"

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")
