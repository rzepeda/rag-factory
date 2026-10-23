"""Offline regression checks for parity features absent from the initial twelve."""
import pytest
from rag_factory.strategies.chunking.semantic import SemanticBoundaryChunker
from rag_factory.strategies.query_expansion.hyde import HyDERetriever
from rag_factory.strategies.knowledge_graph.extraction import GraphRelationshipExtractor, ExtractedGraphIndexer
from rag_factory.strategies.knowledge_graph.hybrid import GraphVectorHybridRetriever
from rag_factory.strategies.knowledge_graph.indexer import KnowledgeGraphIndexer
from tests.mocks.services import MockLLM, MockDocumentStore, MockGraphStore

class SemanticVectors:
    def embed(self, texts):
        return [[1, 0], [1, 0], [0, 1]][:len(texts)]

def test_semantic_boundaries_and_size_cap():
    assert SemanticBoundaryChunker(SemanticVectors(), threshold=.5).chunk(
        "Cats purr. Cats sleep. Rockets launch."
    ) == ["Cats purr. Cats sleep.", "Rockets launch."]
    assert len(SemanticBoundaryChunker(SemanticVectors(), max_sentences=1).chunk(
        "Cats purr. Cats sleep. Rockets launch."
    )) == 3

def test_hyde_passes_generated_passage_not_raw_query():
    prompts, inputs = [], []
    llm = MockLLM("A hypothetical passage about cats.")
    def search(query, limit):
        inputs.append(query)
        return ["a", "a", "b"]
    assert HyDERetriever(llm, search).retrieve("Why cats?", 2) == ["a", "b"]
    assert inputs == ["A hypothetical passage about cats."]
    assert "Why cats?" in llm.prompts[0]

def test_graph_extractor_rejects_unknown_document_ids():
    documents = {"a": "cat", "b": "dog"}
    llm = MockLLM('[["a", "b"], ["a", "b"]]')
    assert GraphRelationshipExtractor(llm).extract(documents) == [("a", "b")]
    indexer = ExtractedGraphIndexer(GraphRelationshipExtractor(llm),
                                    KnowledgeGraphIndexer(MockGraphStore(), MockDocumentStore()))
    assert "graph" in indexer.index(documents, "graph-artifact").capabilities
    with pytest.raises(ValueError, match="known documents"):
        GraphRelationshipExtractor(MockLLM('[["a", "other"]]')).extract(documents)

def test_graph_vector_rank_fusion():
    result = GraphVectorHybridRetriever(
        lambda q, n: ["a", "b"], lambda q, n: ["b", "c"],
    ).retrieve("question", 3)
    assert result == ["b", "a", "c"]


def test_unified_hyde_and_graph_vector_hybrid():
    from rag_factory.factory.unified import (
        StrategySpec, UnifiedConfiguration, build_unified
    )
    from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
    from rag_factory.core.service_contracts import ProviderDescriptor
    from tests.mocks.services import MockKeywordStore, MockTokenizer
    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("llm", "mock", frozenset({"generate"})),
                      lambda: MockLLM("keyword"))
    registry.register(ProviderDescriptor("keyword_store", "mock",
                                         frozenset({"upsert", "search"})), MockKeywordStore)
    registry.register(ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})),
                      MockTokenizer)
    config = UnifiedConfiguration(
        {"llm": ServiceConfig("llm", "mock"),
         "keywords": ServiceConfig("keyword_store", "mock"),
         "tokens": ServiceConfig("tokenizer", "mock")},
        {
            "lexical": StrategySpec("keyword", {"keyword_store": "keywords"},
                                    {"keyword_store": "keywords", "tokenizer": "tokens"}),
            "hyde": StrategySpec("hyde", retrieval={"llm": "llm"},
                                  parameters={"source": "lexical"}),
            "hybrid": StrategySpec("graph_vector_hybrid",
                                   parameters={"sources": ["lexical", "hyde"]}),
        },
    )
    with build_unified(config, registry) as pipeline:
        pipeline.index("lexical", {"documents": {"a": "keyword document"}})
        assert pipeline.retrieve("hyde", "cat")[0].document_id == "a"
        assert pipeline.retrieve("hybrid", "keyword")[0].document_id == "a"


def test_unified_semantic_boundary_chunk_indexing():
    from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified
    from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
    from rag_factory.core.service_contracts import ProviderDescriptor
    from tests.mocks.services import MockVectorStore
    class Embedding:
        def embed(self, texts):
            return [[1., 0.] for _ in texts]
    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("embedding", "mock", frozenset({"embed"})), Embedding)
    registry.register(ProviderDescriptor("vector_store", "mock", frozenset({"upsert", "search"})),
                      MockVectorStore)
    config = UnifiedConfiguration(
        {"embedding": ServiceConfig("embedding", "mock"),
         "vectors": ServiceConfig("vector_store", "mock")},
        {"chunks": StrategySpec("semantic_chunking",
             {"embedding": "embedding", "vector_store": "vectors"},
             {"embedding": "embedding", "vector_store": "vectors"},
             {"embedding_model": "mock", "max_sentences": 1})},
    )
    with build_unified(config, registry) as pipeline:
        pipeline.index("chunks", {"documents": {"doc": "One sentence. Second sentence."}})
        hits = pipeline.retrieve("chunks", "sentence", 5)
        assert {hit.document_id for hit in hits} == {"doc::0", "doc::1"}
