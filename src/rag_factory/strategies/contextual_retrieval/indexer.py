"""Enrich chunks for lexical indexing while retaining original chunk text."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.core.interfaces.services import DocumentStoreService, KeywordStoreService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements
from rag_factory.strategies.contextual_retrieval.enrichment.context_generator import ContextGenerator


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("llm", frozenset({"generate"})),
        ServiceRequirement("keyword_store", frozenset({"upsert", "search"})),
        ServiceRequirement("document_store", frozenset({"upsert", "get"})),
    ),
    retrieval=(
        ServiceRequirement("keyword_store", frozenset({"search"})),
        ServiceRequirement("document_store", frozenset({"get"})),
        ServiceRequirement("tokenizer", frozenset({"tokenize"})),
    ),
)


@dataclass
class ContextualIndexer:
    generator: ContextGenerator
    keywords: KeywordStoreService
    documents: DocumentStoreService

    def index(
        self, chunks: Mapping[str, str], source_document: str, artifact_id: str
    ) -> IndexManifest:
        if not chunks or not source_document.strip() or not artifact_id.strip():
            raise ValueError("Chunks, source document and artifact ID are required")
        if any(not isinstance(key, str) or not key.strip()
               or not isinstance(value, str) or not value.strip()
               for key, value in chunks.items()):
            raise ValueError("Chunk IDs and texts must be nonempty strings")
        enriched = {}
        for chunk_id, text in chunks.items():
            context = self.generator.generate(text, source_document)
            enriched[chunk_id] = context + "\n" + text
        self.keywords.upsert(enriched)
        self.documents.upsert(chunks)
        return IndexManifest(
            artifact_id=artifact_id,
            capabilities=frozenset({"keywords", "contextual", "chunks"}),
            schema_version="1",
            analyzer="word-lowercase",
        )
