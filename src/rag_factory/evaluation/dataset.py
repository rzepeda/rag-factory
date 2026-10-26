"""Versioned offline judgments with immutable snapshots and portable JSON.

Datasets are reusable across strategies and runs. An explicitly zero-grade
document is judged irrelevant; unlisted documents are assumed irrelevant for
these retrieval metrics. Every question needs at least one positive judgment.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from rag_factory.core.artifact_catalog import _atomic_write_json


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    version: str
    judgments: Mapping[str, Mapping[str, int]]

    def __post_init__(self):
        if (not isinstance(self.name, str) or not self.name.strip()
            or not isinstance(self.version, str) or not self.version.strip()
            or not isinstance(self.judgments, Mapping) or not self.judgments):
            raise ValueError("Dataset name, version and judgments are required")
        snapshot = {}
        for query, relevance in self.judgments.items():
            if (not isinstance(query, str) or not query.strip()
                or not isinstance(relevance, Mapping) or not relevance):
                raise ValueError("Each query needs nonempty relevance judgments")
            if any(not isinstance(key, str) or not key.strip()
                   or type(score) is not int or score < 0
                   for key, score in relevance.items()):
                raise ValueError("Relevance grades must be nonnegative integers")
            if not any(score > 0 for score in relevance.values()):
                raise ValueError("Each query needs a positively relevant document")
            snapshot[query] = MappingProxyType(dict(sorted(relevance.items())))
        object.__setattr__(self, "judgments", MappingProxyType(dict(sorted(snapshot.items()))))

    def to_dict(self) -> dict:
        return {
            "format_version": 1,
            "name": self.name,
            "version": self.version,
            "judgments": {
                query: dict(relevance) for query, relevance in self.judgments.items()
            },
        }

    @property
    def sha256(self) -> str:
        """Content fingerprint, independent of JSON whitespace and key insertion order."""
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(self, path: str | Path) -> None:
        _atomic_write_json(path, self.to_dict())

    @classmethod
    def load(cls, path: str | Path) -> "EvaluationDataset":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {
            "format_version", "name", "version", "judgments"
        }:
            raise ValueError("Invalid evaluation dataset format")
        if type(payload["format_version"]) is not int or payload["format_version"] != 1:
            raise ValueError("Unsupported evaluation dataset version")
        return cls(payload["name"], payload["version"], payload["judgments"])


def save_dataset(path: str | Path, dataset: EvaluationDataset) -> None:
    if not isinstance(dataset, EvaluationDataset):
        raise ValueError("Expected an EvaluationDataset")
    dataset.save(path)


def load_dataset(path: str | Path) -> EvaluationDataset:
    return EvaluationDataset.load(path)
