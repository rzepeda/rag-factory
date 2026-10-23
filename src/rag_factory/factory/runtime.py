"""Offline-capable, configuration-driven keyword/semantic/hybrid runtime.

This is the first unified vertical slice. It shares adapter instances and
separates preconstruction validation from execution. It provisions nothing.
"""
from dataclasses import dataclass, field
from typing import Mapping

from rag_factory.core.index_manifest import IndexManifest, IndexRequirement, validate_index_compatibility
from rag_factory.core.interfaces.services import (
    EmbeddingService, KeywordStoreService, TokenizerService, VectorStoreService,
)
from rag_factory.core.service_contracts import validate_service_bindings
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry, default_registry
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer, REQUIREMENTS as KEYWORD
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever
from rag_factory.strategies.semantic_search.indexer import SemanticIndexer, REQUIREMENTS as SEMANTIC
from rag_factory.strategies.semantic_search.retriever import SemanticRetriever
from rag_factory.pipelines.retrieval import RetrievalPipeline, RetrievalSource
from rag_factory.strategies.hybrid_search.retriever import HybridRetriever


@dataclass(frozen=True)
class PipelineConfiguration:
    services: Mapping[str, ServiceConfig]
    bindings: Mapping[str, str]
    strategies: tuple[str, ...]
    embedding_model: str | None = None

    def __post_init__(self):
        if not self.strategies or len(set(self.strategies)) != len(self.strategies):
            raise ValueError("Strategies must be nonempty and unique")
        if set(self.strategies) - {"keyword", "semantic"}:
            raise ValueError("Unsupported strategy in unified runtime")
        if "semantic" in self.strategies and not (self.embedding_model and self.embedding_model.strip()):
            raise ValueError("Semantic pipelines require embedding_model")


@dataclass
class RuntimePipeline:
    keyword: KeywordIndexer | None
    keyword_retriever: KeywordRetriever | None
    semantic: SemanticIndexer | None
    semantic_retriever: SemanticRetriever | None
    _owned: tuple[object, ...] = ()
    _artifacts: dict[str, IndexManifest] = field(default_factory=dict)
    _closed: bool = False

    def index(self, documents: Mapping[str, str]) -> dict[str, IndexManifest]:
        if self._closed:
            raise RuntimeError("Pipeline is closed")
        if not documents:
            raise ValueError("Documents must be nonempty")
        new_artifacts = {}
        if self.keyword:
            new_artifacts["keyword"] = self.keyword.index_with_manifest(documents, "keyword-index")
        if self.semantic:
            new_artifacts["semantic"] = self.semantic.index(documents, "semantic-index")
        self._artifacts.update(new_artifacts)
        return dict(new_artifacts)

    def attach_artifacts(self, artifacts: Mapping[str, IndexManifest]) -> None:
        """Adopt external index metadata after compatibility validation.

        The configured services must already point to the underlying persisted
        index; attaching a manifest never creates or copies an index.
        """
        if self._closed:
            raise RuntimeError("Pipeline is closed")
        for strategy, artifact in artifacts.items():
            if strategy == "keyword" and self.keyword_retriever:
                requirement = IndexRequirement(frozenset({"keywords"}), schema_version="1")
            elif strategy == "semantic" and self.semantic_retriever:
                requirement = IndexRequirement(
                    frozenset({"vectors"}), schema_version="1",
                    embedding_model=self.semantic_retriever.embedding_model,
                    distance_metric=self.semantic_retriever.distance_metric,
                )
            else:
                raise ValueError(f"Unknown or unconfigured artifact strategy: {strategy}")
            validate_index_compatibility(artifact, requirement)
        self._artifacts.update(artifacts)

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if self._closed:
            raise RuntimeError("Pipeline is closed")
        if limit <= 0:
            raise ValueError("limit must be positive")
        sources = []
        if self.keyword_retriever:
            sources.append(RetrievalSource("keyword", self.keyword_retriever.retrieve))
        if self.semantic_retriever:
            if "semantic" not in self._artifacts:
                raise ValueError("Semantic index artifact is not available; index first")
            manifest = self._artifacts["semantic"]
            sources.append(RetrievalSource(
                "semantic", lambda q, n: self.semantic_retriever.retrieve(q, manifest, n)
            ))
        if len(sources) == 1:
            return list(sources[0].search(query, limit))
        return HybridRetriever(RetrievalPipeline(tuple(sources))).retrieve(query, limit)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for instance in reversed(self._owned):
            closer = getattr(instance, "close", None)
            if callable(closer):
                closer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def build_pipeline(
    config: PipelineConfiguration, registry: ServiceRegistry | None = None,
) -> RuntimePipeline:
    registry = registry if registry is not None else default_registry()
    required = []
    for strategy in config.strategies:
        declarations = KEYWORD if strategy == "keyword" else SEMANTIC
        required.extend(declarations.indexing)
        required.extend(declarations.retrieval)
    # Validate all providers before opening any adapter connection.
    used_names = {config.bindings.get(requirement.interface) for requirement in required}
    descriptors = {
        name: registry.descriptor(config.services[name])
        for name in used_names if name is not None and name in config.services
    }
    validate_service_bindings(tuple(required), config.bindings, descriptors)
    instances = {}
    owned = []
    try:
        for requirement in required:
            name = config.bindings[requirement.interface]
            if name not in instances:
                _, instance = registry.resolve(config.services[name])
                instances[name] = instance
                owned.append(instance)
        def service(interface, protocol):
            instance = instances[config.bindings[interface]]
            if not isinstance(instance, protocol):
                raise TypeError(f"Provider does not implement {interface}")
            return instance
        keyword = keyword_retriever = semantic = semantic_retriever = None
        if "keyword" in config.strategies:
            store = service("keyword_store", KeywordStoreService)
            tokenizer = service("tokenizer", TokenizerService)
            keyword = KeywordIndexer(store)
            keyword_retriever = KeywordRetriever(store, tokenizer)
        if "semantic" in config.strategies:
            embedding = service("embedding", EmbeddingService)
            vectors = service("vector_store", VectorStoreService)
            semantic = SemanticIndexer(embedding, vectors, config.embedding_model)
            semantic_retriever = SemanticRetriever(embedding, vectors, config.embedding_model)
        return RuntimePipeline(keyword, keyword_retriever, semantic, semantic_retriever, tuple(owned))
    except BaseException:
        for instance in reversed(owned):
            closer = getattr(instance, "close", None)
            if callable(closer):
                closer()
        raise
