"""Retrieve original chunks using a contextual keyword index."""

from dataclasses import dataclass

from rag_factory.core.index_manifest import (
    IndexManifest, IndexRequirement, validate_index_compatibility,
)
from rag_factory.core.interfaces.services import (
    DocumentStoreService, KeywordStoreService, TokenizerService,
)


@dataclass
class ContextualRetriever:
    keywords: KeywordStoreService
    documents: DocumentStoreService
    tokenizer: TokenizerService

    def retrieve(self, query: str, manifest: IndexManifest, limit: int = 5) -> list[tuple[str, str]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        validate_index_compatibility(
            manifest,
            IndexRequirement(
                capabilities=frozenset({"keywords", "contextual", "chunks"}),
                schema_version="1",
                analyzer="word-lowercase",
            ),
        )
        if not query.strip():
            return []
        results = []
        for identifier in self.keywords.search(self.tokenizer.tokenize(query), limit):
            original = self.documents.get(identifier)
            if original is None:
                raise ValueError(f"Missing original chunk: {identifier}")
            results.append((identifier, original))
        return results
