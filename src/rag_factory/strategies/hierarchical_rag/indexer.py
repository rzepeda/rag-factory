"""Index child passages and store unmodified parent documents."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.interfaces.services import DocumentStoreService, KeywordStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("keyword_store", frozenset({"upsert"})),
        ServiceRequirement("document_store", frozenset({"upsert", "get"})),
    ),
    retrieval=(
        ServiceRequirement("keyword_store", frozenset({"search"})),
        ServiceRequirement("document_store", frozenset({"get"})),
        ServiceRequirement("tokenizer", frozenset({"tokenize"})),
    ),
)


@dataclass
class HierarchicalIndexer:
    keywords: KeywordStoreService
    documents: DocumentStoreService

    def index(
        self,
        parents: Mapping[str, str],
        children: Mapping[str, str],
        child_to_parent: Mapping[str, str],
        artifact_id: str,
    ) -> tuple[IndexManifest, Hierarchy]:
        if not artifact_id.strip() or not parents or not children:
            raise ValueError("Artifact ID, parents and children are required")
        hierarchy = Hierarchy(dict(child_to_parent))
        if set(hierarchy.child_to_parent) != set(children):
            raise ValueError("Every indexed child requires exactly one parent mapping")
        if any(parent not in parents for parent in hierarchy.child_to_parent.values()):
            raise ValueError("Child mapping references an unknown parent")
        if any(not isinstance(key, str) or not key.strip()
               or not isinstance(text, str) or not text.strip()
               for group in (parents, children) for key, text in group.items()):
            raise ValueError("Identifiers and documents must be nonempty strings")
        self.documents.upsert(parents)
        self.keywords.upsert(children)
        return (
            IndexManifest(artifact_id, frozenset({"keywords", "hierarchy", "chunks"}), "1",
                          analyzer="word-lowercase"),
            hierarchy,
        )
