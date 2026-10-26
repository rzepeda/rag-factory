"""P0 end-to-end contracts: payload preflight, partial writes, artifact identities."""
from dataclasses import replace

import pytest

from rag_factory.core.artifact_catalog import load_manifests, save_manifests
from rag_factory.core.index_manifest import IndexManifest
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified
from rag_factory.core.service_contracts import ProviderDescriptor
from tests.mocks.services import MockKeywordStore, MockTokenizer
from tests.unit.core.test_unified_all_strategies import setup, spec


def all_indexed():
    return {
        "keyword": spec("keyword", ["keyword_store"], ["keyword_store", "tokenizer"]),
        "semantic": spec("semantic", ["embedding", "vector_store"],
                         ["embedding", "vector_store"], embedding_model="mock"),
        "semantic_chunking": spec("semantic_chunking", ["embedding", "vector_store"],
                                  ["embedding", "vector_store"], embedding_model="mock"),
        "contextual": spec("contextual", ["llm", "keyword_store", "document_store"],
                           ["keyword_store", "document_store", "tokenizer"]),
        "hierarchical": spec("hierarchical", ["keyword_store", "document_store"],
                             ["keyword_store", "document_store", "tokenizer"]),
        "knowledge_graph": spec("knowledge_graph", ["graph_store", "document_store"],
                                ["graph_store", "document_store"]),
        "late_chunking": spec("late_chunking", ["contextual_token_encoder", "vector_store"],
                              ["embedding", "vector_store"], embedding_model="mock"),
    }


@pytest.mark.parametrize("kind,payload,error", [
    ("keyword", {"documents": {}}, "documents"),
    ("semantic", {"documents": {"": "cat"}}, "documents"),
    ("semantic_chunking", {"documents": {"a": " "}}, "documents"),
    ("contextual", {"chunks": {"a": "cat"}, "source_document": ""}, "source_document"),
    ("hierarchical", {"parents": {"p": "cat"}, "children": {"c": "cat"},
                       "child_to_parent": {"c": "missing"}}, "child_to_parent"),
    ("knowledge_graph", {"documents": {"a": "cat"}, "edges": [("a", "missing")]}, "edges"),
    ("late_chunking", {"tokens": ["cat"], "spans": {"a": (0, 2)}}, "spans"),
    ("keyword", {"documents": {"a": "cat"}, "artfact_id": "typo"}, "Unexpected"),
])
def test_invalid_payload_has_no_provider_side_effects(kind, payload, error):
    registry, services = setup()
    with build_unified(UnifiedConfiguration(services, all_indexed()), registry) as pipeline:
        with pytest.raises(ValueError, match=error):
            pipeline.index(kind, payload)
        assert pipeline._artifacts == {}
        assert pipeline._hierarchies == {}
        assert pipeline._instances["keyword_store"].documents == {}
        assert pipeline._instances["document_store"].documents == {}
        assert pipeline._instances["vector_store"].records == {}
        assert pipeline._instances["graph_store"].edges == {}
        assert pipeline._instances["llm"].prompts == []


class PartiallyWritingStore(MockKeywordStore):
    fail = False

    def upsert(self, documents):
        super().upsert(documents)
        if self.fail:
            raise RuntimeError("injected partial write")


def test_failed_reindex_does_not_leave_stale_manifest_authorizing_search():
    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("keyword_store", "partial", frozenset({"upsert", "search"})),
        PartiallyWritingStore,
    )
    registry.register(
        ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})),
        MockTokenizer,
    )
    config = UnifiedConfiguration(
        {"store": ServiceConfig("keyword_store", "partial"),
         "tokens": ServiceConfig("tokenizer", "mock")},
        {"lexical": StrategySpec("keyword", {"keyword_store": "store"},
                                 {"keyword_store": "store", "tokenizer": "tokens"})},
    )
    with build_unified(config, registry) as pipeline:
        pipeline.index("lexical", {"documents": {"a": "cat"}})
        assert pipeline.retrieve("lexical", "cat")[0].document_id == "a"
        pipeline._instances["store"].fail = True
        with pytest.raises(RuntimeError, match="injected partial write"):
            pipeline.index("lexical", {"documents": {"b": "dog"}})
        assert "b" in pipeline._instances["store"].documents  # Physical rollback is NOT promised.
        assert "lexical" not in pipeline._artifacts
        with pytest.raises(ValueError, match="Missing index artifact"):
            pipeline.retrieve("lexical", "cat")
        assert "lexical" in pipeline._failed_indexes
        with pytest.raises(ValueError, match="successful rebuild"):
            pipeline.attach_artifacts({"lexical": IndexManifest(
                "lexical-index", frozenset({"keywords"}), "1"
            )})
        with pytest.raises(ValueError, match="Cannot publish"):
            pipeline.export_artifact_bundle("should-not-exist.json")
        pipeline._instances["store"].fail = False
        pipeline.index("lexical", {"documents": {"c": "cat"}})
        assert pipeline._failed_indexes == set()
        assert pipeline.retrieve("lexical", "cat")


def test_preflight_error_keeps_previously_healthy_manifest():
    registry, services = setup()
    with build_unified(UnifiedConfiguration(services, {
        "lexical": all_indexed()["keyword"],
    }), registry) as pipeline:
        old = pipeline.index("lexical", {"documents": {"a": "cat"}})
        with pytest.raises(ValueError, match="documents"):
            pipeline.index("lexical", {"documents": {}})
        assert pipeline._artifacts["lexical"] == old
        assert pipeline.retrieve("lexical", "cat")


def test_configured_artifact_identity_roundtrip_and_atomic_rejection(tmp_path):
    registry, services = setup()
    base = all_indexed()["keyword"]
    config = UnifiedConfiguration(services, {
        "lexical": replace(base, parameters={
            "artifact_id": "dataset-v1-keywords",
            "resource_locator": "memory://dataset-v1",
            "access_scope": "offline-test",
        })
    })
    with build_unified(config, registry) as writer:
        with pytest.raises(ValueError, match="artifact_id"):
            writer.index("lexical", {"documents": {"a": "cat"}, "artifact_id": "wrong"})
        manifest = writer.index("lexical", {"documents": {"a": "cat"}})
        assert manifest.artifact_id == "dataset-v1-keywords"
        assert manifest.resource_locator == "memory://dataset-v1"
        assert manifest.access_scope == "offline-test"
        save_manifests(tmp_path / "indexes.json", {"lexical": manifest})
    with build_unified(config, registry) as reader:
        reader.attach_artifacts(load_manifests(tmp_path / "indexes.json"))
        assert reader._artifacts["lexical"] == manifest
        for invalid in (
            replace(manifest, artifact_id="other"),
            replace(manifest, resource_locator="memory://wrong"),
            replace(manifest, access_scope="other-scope"),
        ):
            with pytest.raises(ValueError, match="artifact_id|resource_locator|access_scope"):
                reader.attach_artifacts({"lexical": invalid})
            assert reader._artifacts["lexical"] == manifest


def test_reject_invalid_hierarchy_handoff_atomically():
    from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy

    registry, services = setup()
    cfg = UnifiedConfiguration(services, {"tree": all_indexed()["hierarchical"]})
    artifact = IndexManifest("tree", frozenset({"keywords", "hierarchy", "chunks"}), "1")
    with build_unified(cfg, registry) as pipeline:
        for invalid in ({"tree": object()}, {"unexpected": Hierarchy({"a": "b"})}):
            with pytest.raises(ValueError, match="Invalid hierarchy"):
                pipeline.attach_artifacts({"tree": artifact}, hierarchies=invalid)
            assert pipeline._artifacts == {}
            assert pipeline._hierarchies == {}
        pipeline.attach_artifacts({"tree": artifact},
                                  hierarchies={"tree": Hierarchy({"c": "p"})})
        assert pipeline._hierarchies["tree"].parent_of("c") == "p"


def test_retrieval_rejects_bad_hit_shapes_and_limits():
    from rag_factory.factory.unified import RetrievalHit, normalize_hits

    with pytest.raises(TypeError, match="document_id"):
        RetrievalHit(42)
    with pytest.raises(TypeError, match="text"):
        RetrievalHit("a", 42)
    with pytest.raises(ValueError, match="nonempty"):
        RetrievalHit(" ")
    with pytest.raises(TypeError):
        normalize_hits([object()])

    registry, services = setup()
    with build_unified(UnifiedConfiguration(services, {
        "lexical": all_indexed()["keyword"],
    }), registry) as pipeline:
        pipeline.index("lexical", {"documents": {"a": "cat"}})
        for limit in (True, 1.5, 0, -1):
            with pytest.raises(ValueError, match="positive integer"):
                pipeline.retrieve("lexical", "cat", limit=limit)
        with pytest.raises(TypeError, match="query"):
            pipeline.retrieve("lexical", 42)
