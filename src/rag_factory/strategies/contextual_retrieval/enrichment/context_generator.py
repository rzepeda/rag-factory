"""Generate contextual labels for chunks without provider-specific imports."""

from dataclasses import dataclass
from rag_factory.core.interfaces.services import LLMService


@dataclass
class ContextGenerator:
    llm: LLMService
    max_context_chars: int = 500

    def generate(self, chunk: str, document: str) -> str:
        if self.max_context_chars <= 0:
            raise ValueError("max_context_chars must be positive")
        if not chunk.strip() or not document.strip():
            raise ValueError("Chunk and source document must be nonempty")
        prompt = (
            "Describe the context of this chunk within its source document in one brief "
            "passage. Return only the context.\nDocument:\n" + document
            + "\nChunk:\n" + chunk
        )
        response = self.llm.generate(prompt)
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Context provider must return nonempty text")
        return response.strip()[: self.max_context_chars]
