"""Deterministic in-memory test doubles for the currently defined service interfaces.

These are test-only implementations, not production providers.
"""

import math
import re
from collections import Counter
from typing import Mapping, Sequence


class MockLLM:
    def __init__(self, response: str = "mock answer"):
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class MockTokenizer:
    def tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.casefold())


class MockEmbedding:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text)), float(sum(map(ord, text)) % 997)] for text in texts]


class MockVectorStore:
    def __init__(self):
        self.records: dict[str, tuple[float, ...]] = {}

    def upsert(self, records: Mapping[str, Sequence[float]]) -> None:
        self.records.update({key: tuple(value) for key, value in records.items()})

    def search(self, vector: Sequence[float], limit: int) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if any(len(value) != len(vector) for value in self.records.values()):
            raise ValueError("incompatible vector dimensions")
        return sorted(self.records, key=lambda key: (
            sum((a - b) ** 2 for a, b in zip(self.records[key], vector)), key
        ))[:limit]


class MockKeywordStore:
    def __init__(self):
        self.documents: dict[str, str] = {}
        self.tokenizer = MockTokenizer()

    def upsert(self, documents: Mapping[str, str]) -> None:
        self.documents.update(documents)

    def search(self, terms: Sequence[str], limit: int) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        query = Counter(terms)
        if not query:
            return []
        scored = []
        for identifier, text in self.documents.items():
            words = Counter(self.tokenizer.tokenize(text))
            score = sum(min(words[term], count) for term, count in query.items())
            if score:
                scored.append((identifier, score))
        return [identifier for identifier, _ in sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:limit]]


class MockGraphStore:
    def __init__(self):
        self.edges: dict[str, set[str]] = {}

    def add_edge(self, source: str, target: str) -> None:
        self.edges.setdefault(source, set()).add(target)

    def neighbors(self, node: str) -> list[str]:
        return sorted(self.edges.get(node, ()))


class MockReranker:
    def rerank(self, query: str, documents: Mapping[str, str]) -> list[str]:
        terms = set(MockTokenizer().tokenize(query))
        return sorted(documents, key=lambda key: (
            -len(terms.intersection(MockTokenizer().tokenize(documents[key]))), key
        ))


class MockDocumentStore:
    def __init__(self):
        self.documents: dict[str, str] = {}

    def upsert(self, documents: Mapping[str, str]) -> None:
        self.documents.update(documents)

    def get(self, document_id: str) -> str | None:
        return self.documents.get(document_id)
