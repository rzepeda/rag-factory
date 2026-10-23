"""Configuration-selected service instances and a first keyword pipeline builder."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.service_contracts import validate_service_bindings
from rag_factory.core.interfaces.services import KeywordStoreService, TokenizerService
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry, default_registry
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer, REQUIREMENTS
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever


@dataclass
class KeywordPipeline:
    indexer: KeywordIndexer
    retriever: KeywordRetriever


class RAGFactory:
    def __init__(self, registry: ServiceRegistry | None = None):
        self.registry = registry if registry is not None else default_registry()

    def build_keyword(
        self,
        services: Mapping[str, ServiceConfig],
        bindings: Mapping[str, str],
    ) -> KeywordPipeline:
        """Bind interfaces to named configured instances, verifying before use.

        The same named store is shared by indexing and retrieval. No backend
        infrastructure is installed or provisioned.
        """
        instances: dict[str, object] = {}
        descriptors = {}
        for name, config in services.items():
            descriptor, instance = self.registry.resolve(config)
            descriptors[name] = descriptor
            instances[name] = instance

        validate_service_bindings(REQUIREMENTS.indexing, bindings, descriptors)
        validate_service_bindings(REQUIREMENTS.retrieval, bindings, descriptors)
        store = instances[bindings["keyword_store"]]
        tokenizer = instances[bindings["tokenizer"]]
        if not isinstance(store, KeywordStoreService):
            raise TypeError("Configured keyword store does not implement its interface")
        if not isinstance(tokenizer, TokenizerService):
            raise TypeError("Configured tokenizer does not implement its interface")
        return KeywordPipeline(
            indexer=KeywordIndexer(store),
            retriever=KeywordRetriever(store, tokenizer),
        )
