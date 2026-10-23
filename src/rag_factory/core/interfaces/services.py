"""Minimal, technology-neutral service contracts used by RAG strategies."""

from typing import Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class LLMService(Protocol):
    def generate(self, prompt: str) -> str: ...


@runtime_checkable
class TokenizerService(Protocol):
    def tokenize(self, text: str) -> Sequence[str]: ...


@runtime_checkable
class EmbeddingService(Protocol):
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


@runtime_checkable
class VectorStoreService(Protocol):
    def upsert(self, records: Mapping[str, Sequence[float]]) -> None: ...
    def search(self, vector: Sequence[float], limit: int) -> Sequence[str]: ...


@runtime_checkable
class KeywordStoreService(Protocol):
    def upsert(self, documents: Mapping[str, str]) -> None: ...
    def search(self, terms: Sequence[str], limit: int) -> Sequence[str]: ...


@runtime_checkable
class GraphStoreService(Protocol):
    def add_edge(self, source: str, target: str) -> None: ...
    def neighbors(self, node: str) -> Sequence[str]: ...


@runtime_checkable
class RerankerService(Protocol):
    def rerank(self, query: str, documents: Mapping[str, str]) -> Sequence[str]: ...


@runtime_checkable
class DocumentStoreService(Protocol):
    def upsert(self, documents: Mapping[str, str]) -> None: ...
    def get(self, document_id: str) -> str | None: ...
