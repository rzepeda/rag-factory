"""Explicitly ephemeral document storage implementing DocumentStoreService."""
from dataclasses import dataclass, field
from typing import Mapping

@dataclass
class MemoryDocumentStore:
    documents: dict[str, str] = field(default_factory=dict)

    def upsert(self, documents: Mapping[str, str]) -> None:
        self.documents.update(documents)

    def get(self, document_id: str) -> str | None:
        return self.documents.get(document_id)
