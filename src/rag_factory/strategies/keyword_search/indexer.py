"""Keyword indexing strategy; depends on interfaces, not provider SDKs."""

from dataclasses import dataclass
from typing import Mapping

from rag_factory.core.interfaces.services import KeywordStoreService, TokenizerService
from rag_factory.core.service_contracts import ServiceRequirement, StrategyRequirements


REQUIREMENTS = StrategyRequirements(
    indexing=(
        ServiceRequirement("tokenizer", frozenset({"tokenize"})),
        ServiceRequirement("keyword_store", frozenset({"upsert", "search"})),
    ),
    retrieval=(
        ServiceRequirement("tokenizer", frozenset({"tokenize"})),
        ServiceRequirement("keyword_store", frozenset({"search"})),
    ),
)


@dataclass
class KeywordIndexer:
    """Indexes supplied document identifiers and text into a configured store."""

    store: KeywordStoreService

    def index(self, documents: Mapping[str, str]) -> int:
        if any(not identifier or not isinstance(text, str) for identifier, text in documents.items()):
            raise ValueError("Documents require nonempty IDs and string text")
        self.store.upsert(documents)
        return len(documents)
