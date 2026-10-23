"""Retrieve children then deduplicate and expand associated parents."""

from dataclasses import dataclass

from rag_factory.core.index_manifest import IndexManifest, IndexRequirement, validate_index_compatibility
from rag_factory.core.interfaces.services import DocumentStoreService, KeywordStoreService, TokenizerService
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy
from rag_factory.strategies.hierarchical_rag.hierarchy.expander import ParentExpander


@dataclass
class HierarchicalRetriever:
    keywords: KeywordStoreService
    documents: DocumentStoreService
    tokenizer: TokenizerService
    hierarchy: Hierarchy

    def retrieve(self, query: str, manifest: IndexManifest, limit: int = 5) -> list[tuple[str, str]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        validate_index_compatibility(
            manifest,
            IndexRequirement(frozenset({"keywords", "hierarchy", "chunks"}),
                             schema_version="1", analyzer="word-lowercase"),
        )
        if not query.strip():
            return []
        child_ids = list(self.keywords.search(self.tokenizer.tokenize(query), limit))
        return ParentExpander(self.hierarchy, self.documents).expand(child_ids)
