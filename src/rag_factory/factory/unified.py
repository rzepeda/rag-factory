"""Provider-neutral strategy composition for all twelve offline strategy families.

This is an opt-in unified API. The older keyword/semantic runtime remains
unchanged while callers migrate. No provider provisioning occurs here.
"""
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Callable
from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.index_payloads import validate_index_payload
from rag_factory.core.service_contracts import ServiceRequirement, validate_service_bindings
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry, default_registry
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever
from rag_factory.strategies.semantic_search.indexer import SemanticIndexer
from rag_factory.strategies.semantic_search.retriever import SemanticRetriever
from rag_factory.strategies.contextual_retrieval.enrichment.context_generator import ContextGenerator
from rag_factory.strategies.contextual_retrieval.indexer import ContextualIndexer
from rag_factory.strategies.contextual_retrieval.retriever import ContextualRetriever
from rag_factory.strategies.hierarchical_rag.indexer import HierarchicalIndexer
from rag_factory.strategies.hierarchical_rag.retriever import HierarchicalRetriever
from rag_factory.strategies.knowledge_graph.indexer import KnowledgeGraphIndexer
from rag_factory.strategies.knowledge_graph.retriever import KnowledgeGraphRetriever
from rag_factory.strategies.late_chunking.indexer import LateChunkingIndexer
from rag_factory.strategies.late_chunking.retriever import LateChunkingRetriever
from rag_factory.strategies.reranking.retriever import RerankingRetriever
from rag_factory.strategies.query_expansion.retriever import QueryExpansionRetriever
from rag_factory.strategies.multi_query.retriever import MultiQueryRetriever
from rag_factory.strategies.query_expansion.expansion.expander import QueryExpander
from rag_factory.strategies.self_reflective.retriever import SelfReflectiveRetriever
from rag_factory.strategies.self_reflective.grading.grader import RelevanceGrader
from rag_factory.strategies.agentic_rag.retriever import AgenticRAGRetriever
from rag_factory.pipelines.retrieval import RetrievalPipeline, RetrievalSource
from rag_factory.strategies.hybrid_search.retriever import HybridRetriever
from rag_factory.strategies.query_expansion.hyde import HyDERetriever
from rag_factory.strategies.self_reflective.refinement import QueryRefinementRetriever
from rag_factory.strategies.chunking.semantic import SemanticBoundaryChunker
from rag_factory.strategies.knowledge_graph.hybrid import GraphVectorHybridRetriever


REQUIRES: dict[str, dict[str, tuple[ServiceRequirement, ...]]] = {
    "keyword": {"indexing": (ServiceRequirement("keyword_store", frozenset({"upsert"})),),
                "retrieval": (ServiceRequirement("keyword_store", frozenset({"search"})),
                              ServiceRequirement("tokenizer", frozenset({"tokenize"})))},
    "semantic": {"indexing": (ServiceRequirement("embedding", frozenset({"embed"})),
                                 ServiceRequirement("vector_store", frozenset({"upsert"}))),
                 "retrieval": (ServiceRequirement("embedding", frozenset({"embed"})),
                               ServiceRequirement("vector_store", frozenset({"search"})))},
    "contextual": {"indexing": (ServiceRequirement("llm", frozenset({"generate"})),
                                   ServiceRequirement("keyword_store", frozenset({"upsert"})),
                                   ServiceRequirement("document_store", frozenset({"upsert"}))),
                   "retrieval": (ServiceRequirement("keyword_store", frozenset({"search"})),
                                 ServiceRequirement("tokenizer", frozenset({"tokenize"})),
                                 ServiceRequirement("document_store", frozenset({"get"})))},
    "hierarchical": {"indexing": (ServiceRequirement("keyword_store", frozenset({"upsert"})),
                                     ServiceRequirement("document_store", frozenset({"upsert"}))),
                     "retrieval": (ServiceRequirement("keyword_store", frozenset({"search"})),
                                   ServiceRequirement("tokenizer", frozenset({"tokenize"})),
                                   ServiceRequirement("document_store", frozenset({"get"})))},
    "knowledge_graph": {"indexing": (ServiceRequirement("graph_store", frozenset({"add_edge"})),
                                        ServiceRequirement("document_store", frozenset({"upsert"}))),
                        "retrieval": (ServiceRequirement("graph_store", frozenset({"neighbors"})),
                                      ServiceRequirement("document_store", frozenset({"get"})))},
    "late_chunking": {"indexing": (ServiceRequirement("contextual_token_encoder", frozenset({"encode_tokens"})),
                                     ServiceRequirement("vector_store", frozenset({"upsert"}))),
                      "retrieval": (ServiceRequirement("embedding", frozenset({"embed"})),
                                    ServiceRequirement("vector_store", frozenset({"search"})))},
    "reranking": {"indexing": (), "retrieval": (ServiceRequirement("document_store", frozenset({"get"})),
                                                 ServiceRequirement("reranker", frozenset({"rerank"})))},
    "multi_query": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),)},
    "query_expansion": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),)},
    "self_reflective": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),
                                                       ServiceRequirement("document_store", frozenset({"get"})))},
    "agentic": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),)},
    "hybrid": {"indexing": (), "retrieval": ()},
    "semantic_chunking": {"indexing": (ServiceRequirement("embedding", frozenset({"embed"})), ServiceRequirement("vector_store", frozenset({"upsert"}))), "retrieval": (ServiceRequirement("embedding", frozenset({"embed"})), ServiceRequirement("vector_store", frozenset({"search"})))},
    "query_refinement": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),)},
    "hyde": {"indexing": (), "retrieval": (ServiceRequirement("llm", frozenset({"generate"})),)},
    "graph_vector_hybrid": {"indexing": (), "retrieval": ()},
}
INDEXED = frozenset({"keyword", "semantic", "semantic_chunking", "contextual", "hierarchical",
                      "knowledge_graph", "late_chunking"})
REFERENCED = frozenset({"reranking", "multi_query", "query_expansion", "self_reflective", "hyde", "query_refinement"})
COMPOSITES = REFERENCED | {"agentic", "hybrid", "graph_vector_hybrid"}


@dataclass(frozen=True)
class StrategySpec:
    kind: str
    indexing: Mapping[str, str] = field(default_factory=dict)
    retrieval: Mapping[str, str] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UnifiedConfiguration:
    services: Mapping[str, ServiceConfig]
    strategies: Mapping[str, StrategySpec]

    def __post_init__(self):
        if not self.strategies:
            raise ValueError("At least one strategy is required")
        for name, spec in self.strategies.items():
            if not isinstance(name, str) or not name.strip() or spec.kind not in REQUIRES:
                raise ValueError(f"Unknown strategy: {name}")


@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    text: str | None = None


def normalize_hits(values: list[Any]) -> list[RetrievalHit]:
    hits = []
    seen = set()
    for value in values:
        if isinstance(value, RetrievalHit):
            hit = value
        elif isinstance(value, str):
            hit = RetrievalHit(value)
        elif isinstance(value, tuple) and len(value) == 2 and all(isinstance(v, str) for v in value):
            hit = RetrievalHit(value[0], value[1])
        else:
            raise TypeError("Retriever must return IDs, (ID, text), or RetrievalHit")
        if not hit.document_id.strip():
            raise ValueError("Retrieval document IDs must be nonempty")
        if hit.document_id not in seen:
            hits.append(hit)
            seen.add(hit.document_id)
    return hits


class UnifiedPipeline:
    def __init__(self, config: UnifiedConfiguration, registry: ServiceRegistry):
        self.config = config
        self._instances = {}
        self._owned = []
        self._artifacts: dict[str, IndexManifest] = {}
        self._hierarchies = {}
        self._closed = False
        self._validate(registry)
        try:
            for name in self._service_names():
                _, obj = registry.resolve(config.services[name])
                self._instances[name] = obj
                self._owned.append(obj)
        except BaseException:
            try:
                self.close()
            except Exception:
                pass  # Preserve the construction failure.
            raise

    def _service_names(self):
        return tuple(dict.fromkeys(
            spec.indexing[req.interface] if stage == "indexing" else spec.retrieval[req.interface]
            for spec in self.config.strategies.values()
            for stage in ("indexing", "retrieval")
            for req in REQUIRES[spec.kind][stage]
        ))

    def _validate(self, registry):
        used_names = {
            binding.get(req.interface)
            for spec in self.config.strategies.values()
            for stage, binding in (("indexing", spec.indexing), ("retrieval", spec.retrieval))
            for req in REQUIRES[spec.kind][stage]
        }
        descriptors = {
            name: registry.descriptor(self.config.services[name])
            for name in used_names if name is not None and name in self.config.services
        }
        for name, spec in self.config.strategies.items():
            for stage, bindings in (("indexing", spec.indexing), ("retrieval", spec.retrieval)):
                validate_service_bindings(REQUIRES[spec.kind][stage], bindings, descriptors)
            for option in ("source",):
                if spec.kind in REFERENCED:
                    self._check_reference(name, spec.parameters.get(option))
            if spec.kind in {"hybrid", "agentic", "graph_vector_hybrid"}:
                names = spec.parameters.get("sources")
                if not isinstance(names, list) or not names:
                    raise ValueError(f"Strategy {name} needs nonempty sources")
                for source in names:
                    self._check_reference(name, source)
            if spec.kind in {"semantic", "late_chunking", "semantic_chunking"}:
                model = spec.parameters.get("embedding_model")
                if not isinstance(model, str) or not model.strip():
                    raise ValueError(f"Strategy {name} needs embedding_model")
        # Reject malformed strategy parameters before any provider is constructed.
        for name, spec in self.config.strategies.items():
            params = spec.parameters
            positive = {
                "max_variants": {"multi_query", "query_expansion"},
                "candidate_multiplier": {"reranking"},
                "rank_constant": {"multi_query", "hybrid", "graph_vector_hybrid"},
                "max_steps": {"agentic"},
                "max_hops": {"knowledge_graph"},
                "max_sentences": {"semantic_chunking"},
            }
            nonnegative = {
                "max_rewrites": {"query_refinement"},
                "max_attempts": {"self_reflective"},
            }
            for key, kinds in positive.items():
                if spec.kind in kinds and key in params and (
                    type(params[key]) is not int or params[key] <= 0
                ):
                    raise ValueError(f"Strategy {name}: {key} must be a positive integer")
            for key, kinds in nonnegative.items():
                if spec.kind in kinds and key in params and (
                    type(params[key]) is not int or params[key] < 0
                ):
                    raise ValueError(f"Strategy {name}: {key} must be a nonnegative integer")
            if spec.kind == "semantic_chunking" and "threshold" in params and (
                type(params["threshold"]) not in (int, float) or
                not 0 <= params["threshold"] <= 1
            ):
                raise ValueError(f"Strategy {name}: threshold must be between 0 and 1")
            if spec.kind == "graph_vector_hybrid" and len(params["sources"]) != 2:
                raise ValueError(f"Strategy {name}: graph_vector_hybrid requires exactly two sources")
            if spec.kind in {"hybrid", "agentic", "graph_vector_hybrid"}:
                if len(set(params["sources"])) != len(params["sources"]):
                    raise ValueError(f"Strategy {name}: duplicate source references")
        # Detect cycles before construction or retrieval.
        for name in self.config.strategies:
            self._validate_references(name, set())

    def _check_reference(self, owner, reference):
        if not isinstance(reference, str) or reference not in self.config.strategies or reference == owner:
            raise ValueError(f"Strategy {owner} has an invalid source reference")

    def _validate_references(self, name, visiting):
        if name in visiting:
            raise ValueError("Cyclic strategy references")
        spec = self.config.strategies[name]
        refs = spec.parameters.get("sources", []) if spec.kind in {"hybrid", "agentic", "graph_vector_hybrid"} else (
            [spec.parameters["source"]] if spec.kind in REFERENCED else [])
        for ref in refs:
            self._validate_references(ref, visiting | {name})

    def _service(self, name, stage, interface):
        spec = self.config.strategies[name]
        binding = spec.indexing if stage == "indexing" else spec.retrieval
        return self._instances[binding[interface]]

    def _require_open(self):
        if self._closed:
            raise RuntimeError("Pipeline is closed")

    def index(self, name: str, payload: Mapping[str, Any]) -> IndexManifest:
        """Index one strategy using explicit payloads; never mutate shared stores automatically."""
        self._require_open()
        if name not in self.config.strategies:
            raise ValueError(f"Unknown strategy: {name}")
        spec = self.config.strategies[name]
        kind = spec.kind
        validate_index_payload(kind, payload)
        artifact_id = payload.get("artifact_id", spec.parameters.get("artifact_id", name + "-index"))
        if "artifact_id" in spec.parameters and artifact_id != spec.parameters["artifact_id"]:
            raise ValueError(f"Strategy {name}: index artifact_id does not match configuration")
        get = lambda interface: self._service(name, "indexing", interface)
        self._artifacts.pop(name, None)
        self._hierarchies.pop(name, None)
        if kind == "keyword":
            manifest = KeywordIndexer(get("keyword_store")).index_with_manifest(payload["documents"], artifact_id)
        elif kind == "semantic":
            manifest = SemanticIndexer(get("embedding"), get("vector_store"), spec.parameters["embedding_model"]).index(
                payload["documents"], artifact_id)
        elif kind == "semantic_chunking":
            chunks = {}
            splitter = SemanticBoundaryChunker(get("embedding"),
                spec.parameters.get("threshold", 0.6), spec.parameters.get("max_sentences", 5))
            for document_id, text in payload["documents"].items():
                for chunk_number, chunk in enumerate(splitter.chunk(text)):
                    chunks[f"{document_id}::{chunk_number}"] = chunk
            if not chunks:
                raise ValueError("Semantic chunking produced no chunks")
            manifest = SemanticIndexer(get("embedding"), get("vector_store"),
                spec.parameters["embedding_model"]).index(chunks, artifact_id)
        elif kind == "contextual":
            manifest = ContextualIndexer(ContextGenerator(get("llm")), get("keyword_store"),
                                        get("document_store")).index(
                payload["chunks"], payload["source_document"], artifact_id)
        elif kind == "hierarchical":
            manifest, hierarchy = HierarchicalIndexer(get("keyword_store"), get("document_store")).index(
                payload["parents"], payload["children"], payload["child_to_parent"], artifact_id)
            self._hierarchies[name] = hierarchy
        elif kind == "knowledge_graph":
            manifest = KnowledgeGraphIndexer(get("graph_store"), get("document_store")).index(
                payload["documents"], payload["edges"], artifact_id)
        else:
            manifest = LateChunkingIndexer(get("contextual_token_encoder"), get("vector_store"),
                                          spec.parameters["embedding_model"]).index(
                payload["tokens"], payload["spans"], artifact_id)
        self._artifacts[name] = manifest
        return manifest

    def attach_artifacts(self, artifacts: Mapping[str, IndexManifest], *, hierarchies=None):
        self._require_open()
        from rag_factory.core.index_manifest import IndexRequirement, validate_index_compatibility
        # Transactional metadata update: validate the complete batch first.
        for name, artifact in artifacts.items():
            if name not in self.config.strategies or self.config.strategies[name].kind not in INDEXED:
                raise ValueError(f"Unknown indexed strategy: {name}")
            spec = self.config.strategies[name]
            caps = {
                "keyword": {"keywords"}, "semantic": {"vectors"}, "semantic_chunking": {"vectors"},
                "contextual": {"keywords", "contextual", "chunks"},
                "hierarchical": {"keywords", "hierarchy", "chunks"},
                "knowledge_graph": {"graph", "documents"},
                "late_chunking": {"vectors", "late_chunking"},
            }[spec.kind]
            req = IndexRequirement(frozenset(caps), schema_version="1",
                                   embedding_model=spec.parameters.get("embedding_model"))
            validate_index_compatibility(artifact, req)
            if spec.kind == "hierarchical" and (
                not hierarchies or name not in hierarchies
            ) and name not in self._hierarchies:
                raise ValueError("Hierarchical index requires child-to-parent relationship metadata")
        self._artifacts.update(artifacts)
        if hierarchies:
            self._hierarchies.update(hierarchies)

    def retrieve(self, name: str, query: str, limit: int = 5) -> list[RetrievalHit]:
        self._require_open()
        if name not in self.config.strategies:
            raise ValueError(f"Unknown strategy: {name}")
        if limit <= 0:
            raise ValueError("limit must be positive")
        spec = self.config.strategies[name]
        kind = spec.kind
        params = spec.parameters
        get = lambda interface: self._service(name, "retrieval", interface)
        if kind in INDEXED and name not in self._artifacts:
            raise ValueError(f"Missing index artifact for {name}")
        manifest = self._artifacts.get(name)
        source = lambda q, n: [h.document_id for h in self.retrieve(params["source"], q, n)]
        if kind == "keyword":
            result = KeywordRetriever(get("keyword_store"), get("tokenizer")).retrieve(query, limit)
        elif kind == "semantic":
            result = SemanticRetriever(get("embedding"), get("vector_store"),
                                       params["embedding_model"]).retrieve(query, manifest, limit)
        elif kind == "semantic_chunking":
            result = SemanticRetriever(get("embedding"), get("vector_store"),
                params["embedding_model"]).retrieve(query, manifest, limit)
        elif kind == "contextual":
            result = ContextualRetriever(get("keyword_store"), get("document_store"),
                                         get("tokenizer")).retrieve(query, manifest, limit)
        elif kind == "hierarchical":
            result = HierarchicalRetriever(get("keyword_store"), get("document_store"),
                                           get("tokenizer"), self._hierarchies[name]).retrieve(query, manifest, limit)
        elif kind == "knowledge_graph":
            result = KnowledgeGraphRetriever(get("graph_store"), get("document_store")).retrieve(
                query, manifest, limit, params.get("max_hops", 1))
        elif kind == "late_chunking":
            result = LateChunkingRetriever(get("embedding"), get("vector_store"),
                                           params["embedding_model"]).retrieve(query, manifest, limit)
        elif kind == "reranking":
            result = RerankingRetriever(source, get("document_store"), get("reranker"),
                                        params.get("candidate_multiplier", 3)).retrieve(query, limit)
        elif kind == "multi_query":
            result = MultiQueryRetriever(
                QueryExpander(get("llm"), params.get("max_variants", 3)),
                source, params.get("rank_constant", 60)).retrieve(query, limit)
        elif kind == "query_expansion":
            result = QueryExpansionRetriever(
                get("llm"), source, params.get("max_variants", 3)).retrieve(query, limit)
        elif kind == "self_reflective":
            result = SelfReflectiveRetriever(
                source, get("document_store"), RelevanceGrader(get("llm")),
                params.get("max_attempts", 2)).retrieve(query, limit)
        elif kind == "query_refinement":
            result = QueryRefinementRetriever(get("llm"), source,
                params.get("max_rewrites", 2)).retrieve(query, limit)
        elif kind == "hyde":
            result = HyDERetriever(get("llm"), source).retrieve(query, limit)
        elif kind == "graph_vector_hybrid":
            refs = params["sources"]
            if len(refs) != 2:
                raise ValueError("Graph/vector hybrid requires two source strategies")
            result = GraphVectorHybridRetriever(
                lambda q, n: [h.document_id for h in self.retrieve(refs[0], q, n)],
                lambda q, n: [h.document_id for h in self.retrieve(refs[1], q, n)],
                params.get("rank_constant", 60),
            ).retrieve(query, limit)
        elif kind == "agentic":
            tools = {ref: (lambda q, n, ref=ref: [h.document_id for h in self.retrieve(ref, q, n)])
                     for ref in params["sources"]}
            result = AgenticRAGRetriever(get("llm"), tools,
                                         params.get("max_steps", 2)).retrieve(query, limit)
        else:
            retrieval = RetrievalPipeline(tuple(RetrievalSource(
                ref, (lambda q, n, ref=ref: [h.document_id for h in self.retrieve(ref, q, n)])
            ) for ref in params["sources"]))
            result = HybridRetriever(retrieval, params.get("rank_constant", 60)).retrieve(query, limit)
        return normalize_hits(list(result))

    def close(self):
        if self._closed:
            return
        self._closed = True
        first_error = None
        for instance in reversed(self._owned):
            try:
                closer = getattr(instance, "close", None)
                if callable(closer):
                    closer()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        self._owned.clear()
        if first_error is not None:
            raise first_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.close()
        else:
            try:
                self.close()
            except Exception:
                pass  # Preserve the exception raised inside the context.


def build_unified(config: UnifiedConfiguration, registry: ServiceRegistry | None = None):
    return UnifiedPipeline(config, registry if registry is not None else default_registry())
