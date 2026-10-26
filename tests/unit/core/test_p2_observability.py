"""P2 trace events are structured, optional and content-safe."""
from dataclasses import asdict
import json

import pytest

from rag_factory.factory.unified import UnifiedConfiguration, build_unified
from rag_factory.observability import OperationEvent
from tests.unit.core.test_unified_all_strategies import setup, spec


def _config(services):
    return UnifiedConfiguration(services, {
        "lexical": spec("keyword", ["keyword_store"], ["keyword_store", "tokenizer"]),
    })


def test_events_capture_success_error_and_duration_without_text():
    registry, services = setup()
    events = []
    moments = iter([1., 1.01, 2., 2.02, 3., 3.001])
    with build_unified(
        _config(services), registry, observer=events.append,
        clock=lambda: next(moments),
    ) as pipeline:
        pipeline.index("lexical", {"documents": {"secret": "secret cat content"}})
        assert pipeline.retrieve("lexical", "secret cat")[0].document_id == "secret"
        with pytest.raises(ValueError, match="limit"):
            pipeline.retrieve("lexical", "secret cat", 0)

    assert len(events) == 3
    assert events[0].stage == "indexing"
    assert events[0].strategy == "lexical"
    assert events[0].status == "success"
    assert events[0].duration_ms == pytest.approx(10.)
    assert events[1].stage == "retrieval"
    assert events[1].status == "success"
    assert events[1].duration_ms == pytest.approx(20.)
    assert events[2].status == "error"
    assert events[2].error_type == "ValueError"
    assert events[2].duration_ms == pytest.approx(1.)
    raw = json.dumps([asdict(event) for event in events])
    assert "secret" not in raw
    assert "cat" not in raw


def test_observer_errors_never_override_pipeline_results():
    registry, services = setup()
    def broken_observer(event):
        raise RuntimeError("reporter failed")
    with build_unified(_config(services), registry, observer=broken_observer) as pipeline:
        pipeline.index("lexical", {"documents": {"a": "cat"}})
        assert pipeline.retrieve("lexical", "cat")[0].document_id == "a"
        with pytest.raises(ValueError, match="limit"):
            pipeline.retrieve("lexical", "cat", limit=0)


def test_tracing_disabled_by_default():
    registry, services = setup()
    def should_never_be_called():
        raise AssertionError("clock should not be used without observer")
    with build_unified(_config(services), registry, clock=should_never_be_called) as pipeline:
        pipeline.index("lexical", {"documents": {"a": "cat"}})
        assert pipeline.retrieve("lexical", "cat")


def test_trace_event_invariants():
    with pytest.raises(ValueError, match="status"):
        OperationEvent("indexing", "lexical", 0., "unknown")
    with pytest.raises(ValueError, match="Error events"):
        OperationEvent("retrieval", "lexical", 0., "error")
    with pytest.raises(ValueError, match="Successful events"):
        OperationEvent("retrieval", "lexical", 0., "success", "Oops")
