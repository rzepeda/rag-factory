"""Offline contextual indexing and retrieval contract tests."""

import pytest

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.strategies.contextual_retrieval.enrichment.context_generator import ContextGenerator
from rag_factory.strategies.contextual_retrieval.indexer import ContextualIndexer, REQUIREMENTS
from rag_factory.strategies.contextual_retrieval.retriever import ContextualRetriever
from tests.mocks.services import MockLLM, MockKeywordStore, MockDocumentStore, MockTokenizer


def test_contextual_keyword_index_retains_original_text():
    llm = MockLLM("astronomy planets")
    keywords, documents = MockKeywordStore(), MockDocumentStore()
    original = "Jupiter is large"
    manifest = ContextualIndexer(
        ContextGenerator(llm), keywords, documents
    ).index({"chunk1": original}, "This is a long astronomy lesson", "artifact-1")
    assert len(llm.prompts) == 1
    assert "Jupiter is large" in llm.prompts[0]
    assert documents.get("chunk1") == original
    assert "astronomy planets" in keywords.documents["chunk1"]
    results = ContextualRetriever(keywords, documents, MockTokenizer()).retrieve(
        "astronomy", manifest
    )
    assert results == [("chunk1", original)]
    assert REQUIREMENTS.indexing != REQUIREMENTS.retrieval


def test_contextual_retrieval_rejects_incompatible_manifest():
    retriever = ContextualRetriever(MockKeywordStore(), MockDocumentStore(), MockTokenizer())
    manifest = IndexManifest("wrong", frozenset({"keywords"}), "1")
    with pytest.raises(ValueError, match="Missing index capabilities"):
        retriever.retrieve("topic", manifest)


def test_contextual_invalid_inputs_and_context_limits():
    generator = ContextGenerator(MockLLM("abcdefgh"), max_context_chars=4)
    assert generator.generate("chunk", "document") == "abcd"
    with pytest.raises(ValueError, match="positive"):
        ContextGenerator(MockLLM(), 0).generate("chunk", "document")
    with pytest.raises(ValueError, match="nonempty"):
        ContextGenerator(MockLLM(" "), 10).generate("chunk", "document")
    indexer = ContextualIndexer(generator, MockKeywordStore(), MockDocumentStore())
    with pytest.raises(ValueError, match="required"):
        indexer.index({}, "document", "artifact")
    with pytest.raises(ValueError, match="nonempty"):
        indexer.index({"x": ""}, "document", "artifact")


def test_missing_original_chunk_fails_explicitly():
    keywords = MockKeywordStore()
    keywords.upsert({"x": "astronomy text"})
    manifest = IndexManifest("a", frozenset({"keywords", "contextual", "chunks"}), "1",
                             analyzer="word-lowercase")
    with pytest.raises(ValueError, match="Missing original"):
        ContextualRetriever(keywords, MockDocumentStore(), MockTokenizer()).retrieve(
            "astronomy", manifest
        )
