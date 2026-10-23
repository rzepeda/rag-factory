"""Versioned, immutable-in-practice query judgments for offline evaluation."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    version: str
    judgments: Mapping[str, Mapping[str, int]]

    def __post_init__(self):
        if not self.name.strip() or not self.version.strip() or not self.judgments:
            raise ValueError("Dataset name, version and judgments are required")
        for query, relevance in self.judgments.items():
            if not query.strip() or not relevance:
                raise ValueError("Each query needs nonempty relevance judgments")
            if any(not key.strip() or not isinstance(score, int) or isinstance(score, bool)
                   or score < 0 for key, score in relevance.items()):
                raise ValueError("Relevance grades must be nonnegative integers")
            if not any(score > 0 for score in relevance.values()):
                raise ValueError("Each query needs a positively relevant document")
