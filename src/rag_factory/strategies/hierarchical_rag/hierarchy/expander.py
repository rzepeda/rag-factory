"""Expand child search hits into associated original parent documents."""

from dataclasses import dataclass

from rag_factory.core.interfaces.services import DocumentStoreService
from rag_factory.strategies.hierarchical_rag.hierarchy.builder import Hierarchy


@dataclass
class ParentExpander:
    hierarchy: Hierarchy
    documents: DocumentStoreService

    def expand(self, child_ids: list[str]) -> list[tuple[str, str]]:
        parents = []
        seen = set()
        for child_id in child_ids:
            parent_id = self.hierarchy.parent_of(child_id)
            if parent_id not in seen:
                text = self.documents.get(parent_id)
                if text is None:
                    raise ValueError(f"Missing parent document: {parent_id}")
                parents.append((parent_id, text))
                seen.add(parent_id)
        return parents
