"""Provider cleanup remains reliable when multiple services fail."""
import pytest
from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified

def config():
    return UnifiedConfiguration(
        {"store": ServiceConfig("keyword_store", "mock"), "token": ServiceConfig("tokenizer", "mock")},
        {"keyword": StrategySpec("keyword", {"keyword_store": "store"},
                                  {"keyword_store": "store", "tokenizer": "token"})})

def registry(events, *, fail_construct=False):
    r = ServiceRegistry()
    class Store:
        def close(self):
            events.append("store-close")
            raise RuntimeError("store-close-failed")
    class Token:
        def __init__(self):
            if fail_construct:
                raise ValueError("token-construction-failed")
        def close(self):
            events.append("token-close")
    r.register(ProviderDescriptor("keyword_store", "mock", frozenset({"upsert", "search"})), Store)
    r.register(ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})), Token)
    return r

def test_close_attempts_every_provider_and_is_idempotent():
    events = []
    pipeline = build_unified(config(), registry(events))
    with pytest.raises(RuntimeError, match="store-close-failed"):
        pipeline.close()
    assert events == ["token-close", "store-close"]
    pipeline.close()
    assert events == ["token-close", "store-close"]

def test_constructor_error_survives_cleanup_failure():
    events = []
    with pytest.raises(ValueError, match="token-construction-failed"):
        build_unified(config(), registry(events, fail_construct=True))
    assert events == ["store-close"]

def test_context_body_error_survives_cleanup_failure():
    events = []
    with pytest.raises(ValueError, match="body-failed"):
        with build_unified(config(), registry(events)):
            raise ValueError("body-failed")
    assert events == ["token-close", "store-close"]
