"""Constrained document-link extraction; never executes model output."""
import json
from dataclasses import dataclass
from typing import Mapping
from rag_factory.core.interfaces.services import LLMService
from rag_factory.strategies.knowledge_graph.indexer import KnowledgeGraphIndexer
from rag_factory.core.index_manifest import IndexManifest

@dataclass
class GraphRelationshipExtractor:
    llm: LLMService

    def extract(self, documents: Mapping[str, str]) -> list[tuple[str, str]]:
        prompt = (
            "Identify directed relationships among these document IDs. "
            "Respond ONLY with a JSON array of [source_id, target_id] pairs.\n"
            + json.dumps(documents, sort_keys=True)
        )
        try:
            pairs = json.loads(self.llm.generate(prompt))
        except (ValueError, TypeError) as exc:
            raise ValueError("Graph extractor requires valid JSON") from exc
        if not isinstance(pairs, list):
            raise ValueError("Graph extractor requires an array")
        result = []
        for pair in pairs:
            if (not isinstance(pair, list) or len(pair) != 2 or
                any(not isinstance(node, str) or node not in documents for node in pair)):
                raise ValueError("Graph relationships must refer to known documents")
            edge = (pair[0], pair[1])
            if edge not in result:
                result.append(edge)
        return result

@dataclass
class ExtractedGraphIndexer:
    extractor: GraphRelationshipExtractor
    indexer: KnowledgeGraphIndexer

    def index(self, documents: Mapping[str, str], artifact_id: str) -> IndexManifest:
        edges = self.extractor.extract(documents)
        return self.indexer.index(documents, edges, artifact_id)
