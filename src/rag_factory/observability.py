"""Structured, opt-in stage events with no query text or document contents.

Events capture operational outcomes, not retrieval quality. Callbacks are optional
and must never turn a successful pipeline operation into a failure.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class OperationEvent:
    stage: str
    strategy: str
    duration_ms: float
    status: str
    error_type: str | None = None

    def __post_init__(self):
        if self.stage not in {"indexing", "retrieval"}:
            raise ValueError("Unknown event stage")
        if not isinstance(self.strategy, str) or not self.strategy.strip():
            raise ValueError("Event strategy is required")
        if self.status not in {"success", "error"}:
            raise ValueError("Unknown event status")
        if self.duration_ms < 0:
            raise ValueError("Event duration must be nonnegative")
        if self.status == "success" and self.error_type is not None:
            raise ValueError("Successful events cannot contain errors")
        if self.status == "error" and not self.error_type:
            raise ValueError("Error events must contain an error type")
