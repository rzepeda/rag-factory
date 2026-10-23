"""Contract tests requiring no model server or database."""

import pytest

from rag_factory.core.mapping import EntityMapping, LogicalEntity, validate_entity_mapping
from rag_factory.core.service_contracts import (
    ProviderDescriptor,
    ServiceRequirement,
    StrategyRequirements,
)


def test_provider_capability_resolution():
    req = ServiceRequirement("llm", frozenset({"text_generation"}))
    provider = ProviderDescriptor("llm", "ollama", frozenset({"text_generation", "stream"}))
    assert provider.satisfies(req)
    assert not provider.satisfies(ServiceRequirement("llm", frozenset({"tool_calls"})))
    assert not provider.satisfies(ServiceRequirement("embedding", frozenset()))


def test_indexing_and_retrieval_requirements_are_independent():
    reqs = StrategyRequirements(
        indexing=(ServiceRequirement("llm"),),
        retrieval=(ServiceRequirement("vector_store"),),
    )
    assert reqs.indexing[0].interface == "llm"
    assert reqs.retrieval[0].interface == "vector_store"


def test_logical_entity_is_independent_of_physical_columns():
    entity = LogicalEntity("Chunk", frozenset({"id", "document_id", "content"}))
    mapping = EntityMapping("my_chunks", {
        "id": "chunk_id", "document_id": "doc_fk", "content": "body"
    })
    validate_entity_mapping(entity, mapping)


def test_required_field_missing_from_mapping_fails():
    entity = LogicalEntity("Chunk", frozenset({"id", "content"}))
    with pytest.raises(ValueError, match="content"):
        validate_entity_mapping(entity, EntityMapping("my_chunks", {"id": "chunk_id"}))


def test_empty_provider_and_mapping_names_fail():
    with pytest.raises(ValueError):
        ProviderDescriptor("llm", "")
    with pytest.raises(ValueError):
        EntityMapping("")
