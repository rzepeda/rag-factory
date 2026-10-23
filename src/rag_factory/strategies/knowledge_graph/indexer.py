"""Provider-neutral indexing of explicit graph relationships and documents."""

from dataclasses import dataclass
from typing import Mapping, Sequence

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.interfaces.services import DocumentStoreService, GraphStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("graph_store", frozenset({"add_edge"})),
        ServiceRequirement("document_store", frozenset({"upsert"})),
    ),
    retrieval=(
        ServiceRequirement("graph_store", frozenset({"neighbors"})),
        ServiceRequirement("document_store", frozenset({"get"})),
    ),
)


@dataclass
class KnowledgeGraphIndexer:
    graph: GraphStoreService
    documents: DocumentStoreService

    def index(
        self,
        documents: Mapping[str, str],
        edges: Sequence[tuple[str, str]],
        artifact_id: str,
    ) -> IndexManifest:
        if not artifact_id.strip() or not documents:
            raise ValueError("Artifact ID and documents are required")
        if any(not isinstance(identifier, str) or not identifier.strip()
               or not isinstance(body, str) or not body.strip()
               for identifier, body in documents.items()):
            raise ValueError("Document identifiers and contents must be nonempty strings")
        if any(len(edge) != 2 or any(not isinstance(node, str) or node not in documents
                                     for node in edge) for edge in edges):
            raise ValueError("Edges must connect known document identifiers")
        self.documents.upsert(documents)
        for source, target in edges:
            self.graph.add_edge(source, target)
        return IndexManifest(
            artifact_id=artifact_id,
            capabilities=frozenset({"graph", "documents"}),
            schema_version="1",
        )
