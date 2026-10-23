"""Keyword retrieval strategy using injected tokenizer and keyword store."""

from dataclasses import dataclass

from rag_factory.core.interfaces.services import KeywordStoreService, TokenizerService


@dataclass
class KeywordRetriever:
    store: KeywordStoreService
    tokenizer: TokenizerService

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if not query.strip():
            return []
        return list(self.store.search(self.tokenizer.tokenize(query), limit))
