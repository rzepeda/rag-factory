"""Small deterministic in-process keyword store for demos and tests.

Not BM25 and not intended as a replacement for production search services.
"""

import re
from collections import Counter
from typing import Mapping, Sequence


class MemoryKeywordStore:
    def __init__(self):
        self.documents: dict[str, str] = {}

    def upsert(self, documents: Mapping[str, str]) -> None:
        self.documents.update(documents)

    def search(self, terms: Sequence[str], limit: int) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        query = Counter(terms)
        if not query:
            return []
        matches = []
        for identifier, content in self.documents.items():
            tokens = Counter(re.findall(r"\w+", content.casefold()))
            score = sum(min(tokens[term.casefold()], count) for term, count in query.items())
            if score:
                matches.append((identifier, score))
        return [key for key, score in sorted(matches, key=lambda entry: (-entry[1], entry[0]))[:limit]]
