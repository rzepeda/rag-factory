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
