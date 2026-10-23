"""Bounded graph traversal retrieving original document contents."""

from collections import deque
from dataclasses import dataclass

from rag_factory.core.index_manifest import IndexManifest, IndexRequirement, validate_index_compatibility
from rag_factory.core.interfaces.services import DocumentStoreService, GraphStoreService


@dataclass
class KnowledgeGraphRetriever:
    graph: GraphStoreService
    documents: DocumentStoreService

    def retrieve(
        self, start_node: str, manifest: IndexManifest, limit: int = 5,
        max_hops: int = 1,
    ) -> list[tuple[str, str]]:
        if limit <= 0 or max_hops < 0:
            raise ValueError("limit must be positive and max_hops nonnegative")
        validate_index_compatibility(
            manifest, IndexRequirement(frozenset({"graph", "documents"}), schema_version="1")
        )
        if not start_node.strip():
            return []
        results = []
        visited = {start_node}
        queue = deque([(start_node, 0)])
        while queue and len(results) < limit:
            node, depth = queue.popleft()
            text = self.documents.get(node)
            if text is None:
                raise ValueError(f"Missing graph document: {node}")
            results.append((node, text))
            if depth < max_hops:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
        return results
