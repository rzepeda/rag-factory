"""Pure offline manifest and mapping regressions."""

import pytest

from rag_factory.core.index_manifest import IndexManifest, IndexRequirement, validate_index_compatibility
from rag_factory.core.mapping import (
    LogicalEntity, LogicalModel, EntityMapping, StorageMapping, validate_operational_support,
)
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer
from tests.mocks.services import MockKeywordStore


def test_keyword_manifest_is_compatible_with_another_retrieval_strategy():
    store = MockKeywordStore()
    manifest = KeywordIndexer(store).index_with_manifest({"a": "cat"}, "lexical-1")
    validate_index_compatibility(manifest, IndexRequirement(
        frozenset({"keywords"}), schema_version="1", analyzer="word-lowercase"
    ))
    assert store.search(["cat"], 1) == ["a"]
    with pytest.raises(ValueError, match="Artifact"):
        KeywordIndexer(store).index_with_manifest({}, "")


def test_provenance_and_access_must_match_explicit_requirements():
    artifact = IndexManifest(
        "vectors", frozenset({"vectors"}), "1",
        embedding_model="small", embedding_dimensions=2,
        embedding_revision="v2", resource_locator="memory://vectors",
        access_scope="test-tenant",
    )
    validate_index_compatibility(artifact, IndexRequirement(
        frozenset({"vectors"}), embedding_revision="v2",
        resource_locator="memory://vectors", access_scope="test-tenant",
    ))
    for key, value in (
        ("embedding_revision", "v3"),
        ("resource_locator", "memory://other"),
        ("access_scope", "other-tenant"),
    ):
        with pytest.raises(ValueError, match=key):
            validate_index_compatibility(
                artifact, IndexRequirement(frozenset({"vectors"}), **{key: value})
            )
    with pytest.raises(ValueError, match="access_scope"):
        IndexManifest("x", frozenset(), "1", access_scope=" ")


def test_mapping_needs_provider_advertised_operations():
    model = LogicalModel(
        (LogicalEntity("Chunk", frozenset({"content"})),),
        frozenset({"search", "upsert"}),
    )
    mapped = StorageMapping(
        {"Chunk": EntityMapping("chunks", {"content": "body"})},
        frozenset({"search", "upsert"}),
    )
    validate_operational_support(model, mapped, frozenset({"search", "upsert"}))
    with pytest.raises(ValueError, match="Provider does not support"):
        validate_operational_support(model, mapped, frozenset({"search"}))
