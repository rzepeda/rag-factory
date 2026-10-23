# Offline unified runtime

This is a working **keyword, semantic and hybrid** configuration-driven vertical slice. It uses the existing `ServiceRegistry` and validates all required provider capability declarations before constructing any adapter.

Example YAML:

```yaml
services:
  keywords: {interface: keyword_store, implementation: memory}
  tokens: {interface: tokenizer, implementation: regex}
pipeline:
  strategies: [keyword]
  bindings:
    keyword_store: keywords
    tokenizer: tokens
```

Usage:

```python
from rag_factory.factory.runtime_config import load_pipeline_config
from rag_factory.factory.runtime import build_pipeline

configuration = load_pipeline_config("rag.yaml")
with build_pipeline(configuration) as pipeline:
    manifests = pipeline.index({"a": "Example content", "b": "Other material"})
    print(pipeline.retrieve("example"))
```

For semantic or hybrid composition, register implementations of `embedding` and `vector_store` in a `ServiceRegistry`, set `pipeline.strategies` to `[semantic]` or `[keyword, semantic]`, and provide `pipeline.embedding_model`. The test suite demonstrates this with offline mocks. By design, the default production registry does not register a fake semantic encoder as a real provider.

**Current limitations:** This is not yet a universal factory for all twelve strategy families, and it does not provision services or persist index manifests. Semantic retrieval in this runtime needs the index produced during the current pipeline execution. Full artifact reuse, cross-process storage identities, standardized result types, and configuration-driven orchestration for graph/agentic/contextual strategies remain unfinished.
