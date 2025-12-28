# RAG Factory

Modular RAG strategy system with entity-repository pattern.

## Installation

```bash
# Core only
pip install rag-factory

# With local ONNX embeddings (no API keys needed)
pip install rag-factory[embedding-onnx,database-postgres]

# With LM Studio LLM (self-hosted)
pip install rag-factory[llm-local,embedding-onnx,database-postgres]

# Everything (all strategies)
pip install rag-factory[all]
```

## Quick Start

See examples/ directory for usage examples.
All examples use local/self-hosted services - no API keys required!
