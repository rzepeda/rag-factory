"""Fuse graph traversal and semantic search using reciprocal ranks."""
from dataclasses import dataclass
from typing import Callable, Sequence
from rag_factory.pipelines.retrieval import RetrievalPipeline, RetrievalSource
from rag_factory.strategies.hybrid_search.retriever import HybridRetriever

@dataclass
class GraphVectorHybridRetriever:
    graph_search: Callable[[str, int], Sequence[str]]
    vector_search: Callable[[str, int], Sequence[str]]
    rank_constant: int = 60

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        sources = RetrievalPipeline((
            RetrievalSource("graph", self.graph_search),
            RetrievalSource("vector", self.vector_search),
        ))
        return HybridRetriever(sources, self.rank_constant).retrieve(query, limit)
