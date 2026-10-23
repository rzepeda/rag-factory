"""Configuration-driven keyword builder with validated, owned service instances."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.service_contracts import validate_service_bindings
from rag_factory.core.interfaces.services import KeywordStoreService, TokenizerService
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry, default_registry
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer, REQUIREMENTS
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever


def _close_owned(instances: list[object]) -> None:
    for instance in reversed(instances):
        close = getattr(instance, "close", None)
        if callable(close):
            close()


@dataclass
class KeywordPipeline:
    indexer: KeywordIndexer
    retriever: KeywordRetriever
    _owned: tuple[object, ...] = ()
    _closed: bool = False

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            _close_owned(list(self._owned))

    def __enter__(self) -> "KeywordPipeline":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class RAGFactory:
    def __init__(self, registry: ServiceRegistry | None = None):
        self.registry = registry if registry is not None else default_registry()

    def build_keyword(
        self,
        services: Mapping[str, ServiceConfig],
        bindings: Mapping[str, str],
    ) -> KeywordPipeline:
        """Validate provider declarations first, construct only used services."""
        descriptors = {name: self.registry.descriptor(cfg) for name, cfg in services.items()}
        validate_service_bindings(REQUIREMENTS.indexing, bindings, descriptors)
        validate_service_bindings(REQUIREMENTS.retrieval, bindings, descriptors)

        instances: dict[str, object] = {}
        owned: list[object] = []
        try:
            for interface in ("keyword_store", "tokenizer"):
                name = bindings[interface]
                if name not in instances:
                    _, instance = self.registry.resolve(services[name])
                    instances[name] = instance
                    owned.append(instance)
            store = instances[bindings["keyword_store"]]
            tokenizer = instances[bindings["tokenizer"]]
            if not isinstance(store, KeywordStoreService):
                raise TypeError("Configured keyword store does not implement its interface")
            if not isinstance(tokenizer, TokenizerService):
                raise TypeError("Configured tokenizer does not implement its interface")
            return KeywordPipeline(KeywordIndexer(store), KeywordRetriever(store, tokenizer), tuple(owned))
        except BaseException:
            _close_owned(owned)
            raise
