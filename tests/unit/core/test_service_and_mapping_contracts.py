"""Pure-contract tests; no provider or database dependency."""

import pytest

from rag_factory.core.mapping import (
    EntityMapping, LogicalEntity, LogicalModel, StorageMapping,
    validate_entity_mapping, validate_storage_mapping,
)
from rag_factory.core.service_contracts import (
    ProviderDescriptor, ServiceRequirement, StrategyRequirements,
    validate_service_bindings,
)
from rag_factory.core.index_manifest import (
    IndexManifest, IndexRequirement, validate_index_compatibility,
)


def test_provider_support_and_stage_separation():
    descriptor = ProviderDescriptor("llm", "ollama", frozenset({"generate", "stream"}))
    assert descriptor.satisfies(ServiceRequirement("llm", frozenset({"generate"})))
    assert not descriptor.satisfies(ServiceRequirement("llm", frozenset({"tools"})))
    phases = StrategyRequirements(indexing=(ServiceRequirement("llm"),),
                                  retrieval=(ServiceRequirement("vector_store"),))
    assert phases.for_stage("indexing")[0].interface == "llm"
    assert phases.for_stage("retrieval")[0].interface == "vector_store"
    with pytest.raises(ValueError, match="Unknown stage"):
        phases.for_stage("other")


def test_named_provider_binding():
    reqs = (ServiceRequirement("llm", frozenset({"generate"})),)
    services = {"writer": ProviderDescriptor("llm", "ollama", frozenset({"generate"}))}
    validate_service_bindings(reqs, {"llm": "writer"}, services)
    with pytest.raises(ValueError, match="Missing configured"):
        validate_service_bindings(reqs, {"llm": "missing"}, services)
    with pytest.raises(ValueError, match="does not satisfy"):
        validate_service_bindings(
            (ServiceRequirement("llm", frozenset({"tools"})),),
            {"llm": "writer"}, services,
        )


def test_logical_mapping_and_operation_contracts():
    chunk = LogicalEntity("Chunk", frozenset({"id", "content"}),
                          frozenset({"document"}))
    model = LogicalModel((chunk,), frozenset({"keyword_search", "save"}))
    physical = StorageMapping(
        {"Chunk": EntityMapping("chunks", {"id": "chunk_id", "content": "body"},
                                {"document": "document_fk"})},
        frozenset({"keyword_search", "save"}),
    )
    validate_storage_mapping(model, physical)
    validate_entity_mapping(chunk, physical.entities["Chunk"])
    with pytest.raises(ValueError, match="Missing storage operations"):
        validate_storage_mapping(model, StorageMapping(physical.entities, frozenset({"save"})))
    with pytest.raises(ValueError, match="missing relationships"):
        validate_entity_mapping(chunk, EntityMapping("chunks", {
            "id": "chunk_id", "content": "body",
        }))
    with pytest.raises(ValueError, match="missing mappings"):
        validate_entity_mapping(chunk, EntityMapping("chunks", {"id": "chunk_id"}))
    with pytest.raises(ValueError, match="Missing physical mapping"):
        validate_storage_mapping(model, StorageMapping({}, physical.operations))


def test_invalid_names_rejected():
    with pytest.raises(ValueError):
        ProviderDescriptor("llm", "")
    with pytest.raises(ValueError):
        EntityMapping("")
    with pytest.raises(ValueError):
        LogicalModel((LogicalEntity("Chunk", frozenset({"id"})),
                      LogicalEntity("Chunk", frozenset({"content"}))))


def test_index_artifact_compatibility_across_strategies():
    artifact = IndexManifest("idx-1", frozenset({"vectors", "chunks"}), "1",
                             "embed-v1", 384, "cosine")
    validate_index_compatibility(
        artifact, IndexRequirement(frozenset({"vectors"}), "1", "embed-v1", 384, "cosine")
    )
    with pytest.raises(ValueError, match="embedding_dimensions"):
        validate_index_compatibility(
            artifact, IndexRequirement(frozenset({"vectors"}), embedding_dimensions=768)
        )
    with pytest.raises(ValueError, match="Missing index capabilities"):
        validate_index_compatibility(artifact, IndexRequirement(frozenset({"keywords"})))
