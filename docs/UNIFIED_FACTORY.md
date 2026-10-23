# Unified offline factory (12 strategy families)

The opt-in `rag_factory.factory.unified` runtime supports all twelve existing strategy families through a single provider-neutral constructor. This API is intentionally separate from the earlier `factory.runtime` keyword/semantic API while migration and compatibility testing continue.

## Configuration

Each named strategy declares its `kind`, independent **indexing** and **retrieval** interface-to-service bindings, and strategy-specific `parameters`.

```yaml
services:
  writer: {interface: keyword_store, implementation: memory}
  reader: {interface: keyword_store, implementation: memory}
  tokens: {interface: tokenizer, implementation: regex}
strategies:
  lexical:
    kind: keyword
    indexing: {keyword_store: writer}
    retrieval: {keyword_store: reader, tokenizer: tokens}
```

```python
from rag_factory.factory.unified_config import load_unified_config
from rag_factory.factory.unified import build_unified

cfg = load_unified_config("rag.yaml")
with build_unified(cfg) as pipeline:
    manifest = pipeline.index("lexical", {"documents": {"a": "cat"}})
    hits = pipeline.retrieve("lexical", "cat")
```

The example deliberately binds separate **in-memory** stores. Its retrieval results will be empty unless the reader has been populated; production use should configure reader and writer against the same externally managed persistent index, or bind both stages to a single in-memory instance.

Each `retrieve(name, query, limit)` returns `list[RetrievalHit]` where each hit has a required `document_id` and optional `text`. Existing strategy APIs remain unchanged and an adapter normalizes their IDs or `(ID, text)` tuples. The runtime deduplicates per-strategy hits.

## The twelve strategy kinds

| Kind | Index payload | Additional parameters |
| --- | --- | --- |
| `keyword` | `documents` | none |
| `semantic` | `documents` | `embedding_model` |
| `contextual` | `chunks`, `source_document` | none |
| `hierarchical` | `parents`, `children`, `child_to_parent` | none |
| `knowledge_graph` | `documents`, `edges` | `max_hops` |
| `late_chunking` | `tokens`, `spans` | `embedding_model` |
| `reranking` | no own index | `source`, optional `candidate_multiplier` |
| `multi_query` | no own index | `source`, optional `max_variants` and `rank_constant` |
| `query_expansion` | no own index | `source`, optional `max_variants` |
| `self_reflective` | no own index | `source`, optional `max_attempts` |
| `agentic` | no own index | `sources`, optional `max_steps` |
| `hybrid` | no own index | `sources`, optional `rank_constant` |

Indexed strategies require explicit payload data. The factory does not invent document chunking, entity extraction, or data models. A `hybrid` configuration combines the results of independently indexed sources. Composite references are validated and cycles rejected before service construction.

The `UnifiedPipeline.attach_artifacts()` method validates a batch of index manifests before updating in-memory metadata. For a hierarchical artifact, the external child-to-parent mapping must also be supplied with `hierarchies=`. The `core.artifact_catalog` JSON serialization persists manifests only; it does not persist hierarchy relationships, chunks, or vectors.

## Boundaries

This integration is tested using deterministic offline providers; **real infrastructure remains deferred**. Provider metadata is checked before adapters are created, and constructed instances are owned and closed by the pipeline. Registry descriptors still cannot prove real endpoint connectivity, enforce access scope, or guarantee physical schema compatibility. Index writes are not transactional across multiple strategy calls, and externally managed persistent storage must be configured independently.

Existing strategy algorithms are initial baselines, and some are purposely limited (e.g. agentic routing selects only allowed tool names, late chunking requires full-document token vectors, graph traversal begins from a supplied node). The unified factory does not silently turn these into more complete algorithms.
