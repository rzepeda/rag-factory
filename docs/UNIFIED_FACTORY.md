# Unified offline factory (16 strategy kinds)

The opt-in `rag_factory.factory.unified` runtime supports the twelve baseline strategy families and four additional variants through a single provider-neutral constructor. This API is intentionally separate from the earlier `factory.runtime` keyword/semantic API while migration and compatibility testing continue.

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

## Supported strategy kinds

| Kind | Index payload | Additional parameters |
| --- | --- | --- |
| `keyword` | `documents` | none |
| `semantic` | `documents` | `embedding_model` |
| `semantic_chunking` | `documents` | `embedding_model`, optional `threshold`, `max_sentences` |
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
| `hyde` | no own index | `source` |
| `query_refinement` | no own index | `source`, optional `max_rewrites` |
| `graph_vector_hybrid` | no own index | exactly two `sources`, optional `rank_constant` |

Indexed strategies require explicit payload data. The factory does not invent document chunking, entity extraction, or data models. A `hybrid` configuration combines the results of independently indexed sources. Composite references are validated and cycles rejected before service construction.

The `UnifiedPipeline.attach_artifacts()` method validates a batch of index manifests before updating in-memory metadata. For a hierarchical artifact, the child-to-parent mapping must also be supplied via `hierarchies=`. The original `core.artifact_catalog` JSON format persists manifests only; `core.hierarchy_catalog` persists relationships separately.

**Preferred cross-execution handoff:** save manifests and hierarchy relationships together in one atomic, versioned JSON metadata bundle:

```python
# After successfully indexing with the writer pipeline:
writer.export_artifact_bundle("indexes.bundle.json")

# In a separate pipeline instance with access to the SAME indexed provider data:
reader.attach_artifact_bundle("indexes.bundle.json")
hits = reader.retrieve("lexical", "cat")
```

The bundle stores **metadata only**, never document contents, keyword postings, vectors, or graph data. The reader must have access to the underlying indexed data. Corrupt bundles, incomplete hierarchy relationships and mismatched configured artifact metadata are rejected without a partial metadata update.

Optionally set `parameters.artifact_id`, `parameters.resource_locator`, `parameters.access_scope`, or `parameters.embedding_revision` for an indexed strategy. These values become asserted manifest metadata and are validated again on attachment. They are **not** evidence that a provider implements access control or physically holds matching data.

The unified indexing entry point validates every required payload field before writes. Once a write begins, a provider failure invalidates the strategy's previous attached manifest and prevents old metadata from being reattached or exported in that pipeline until a successful re-index. It does **not** undo partial provider writes, and a new process cannot detect unverified physical store corruption.

## Boundaries

This integration is tested using deterministic offline providers; **real infrastructure remains deferred**. Provider metadata is checked before adapters are created, and constructed instances are owned and closed by the pipeline. Registry descriptors still cannot prove real endpoint connectivity, enforce access scope, or guarantee physical schema compatibility. Index writes are not transactional across multiple strategy calls, and externally managed persistent storage must be configured independently.

Existing strategy algorithms are initial baselines, and some are purposely limited (e.g. agentic routing selects only allowed tool names, late chunking requires full-document token vectors, graph traversal begins from a supplied node). The unified factory does not silently turn these into more complete algorithms.
