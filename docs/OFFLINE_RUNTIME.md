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

**Current limitations:** This is not yet a universal factory for all twelve strategy families, and it does not provision services or persist index manifests. Semantic retrieval can use the index produced during the current pipeline execution, or call `pipeline.attach_artifacts({"semantic": manifest})` to connect a separately produced compatible artifact. The underlying vector store must already contain that index; the manifest is metadata only. Full artifact reuse, cross-process storage identities, standardized result types, and configuration-driven orchestration for graph/agentic/contextual strategies remain unfinished.


## Reusing manifests across separate executions

The optional `core.artifact_catalog` module saves and loads named manifests as a versioned JSON document:

```python
from rag_factory.core.artifact_catalog import save_manifests, load_manifests

# In the indexing process:
save_manifests("indexes.json", pipeline.index(documents))

# In a separate retrieval process, with a store connected to the same data:
pipeline.attach_artifacts(load_manifests("indexes.json"))
results = pipeline.retrieve("example")
```

This catalog is **metadata only**, and the provided JSON file should be treated as trusted deployment configuration. It does not contain indexed vectors or document text, create collections, control access, migrate schemas, or guarantee that a physical index exists. Store access and persistence remain adapter responsibilities.
