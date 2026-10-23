# Implementation backlog (2026-10-23)

Tracked implementation priorities on `dev`. The first item is the currently selected delivery slice. All early slices run offline; real providers remain deferred.

| Priority | Work | Acceptance criteria | Status |
| --- | --- | --- | --- |
| 1 | Contextual retrieval | LLM-generated bounded chunk context, index/search via interfaces, preserve original text, tests with mocks | Implemented in this change |
| 2 | Hierarchical retrieval | Parent/child indexing and expansion with deterministic mock storage and validated relationships | Implemented (mock-backed baseline) |
| 3 | Retrieval strategy registry and configuration | Named retrieval strategies selected via YAML and explicitly registered builders; composable sources | Implemented (initial retrieval-only baseline) |
| 4 | Shared provider behavioral contracts | Parameterized offline behavioral checks across mock/in-memory keyword and tokenizer providers; mock-only tests for other six interfaces | Implemented (initial offline baseline; lifecycle/external adapters pending) |
| 5 | Index artifact and mapping hardening | Keyword manifest API, optional locator/access/revision metadata, provider-advertised operation coverage | Implemented (declarative baseline; physical inspection/authorization pending) |
| 6 | Evaluations and reproducibility | Versioned graded judgments, mean nDCG@k, deterministic JSON experiment reports, caller-supplied provenance metadata | Implemented (offline baseline; provenance collection and timing/cost pending) |
| 7 | Remaining advanced strategies | Reranking, graph, self-reflective, late-chunking and agentic vertical slices, scoped individually | Reranking, explicit-graph traversal and bounded relevance grading implemented (mock-backed); all twelve strategy families now have initial baselines |
| 8 | Real service adapters | Postgres FTS/vector, model/LLM providers and opt-in integration tests | Deferred until infrastructure is available |

A checked-in source file containing only a stub is not an implemented feature. Tests in `tests/unit/core` are the current correctness gate on Python 3.12.

## Advanced strategy inventory

The source tree contains 11 original strategy families. Seven currently have an executable baseline (keyword, semantic, hybrid retrieval, multi-query, query expansion, contextual, hierarchical). Late chunking now implements full-document contextual token encoding followed by span pooling, with a reference mock encoder. Agentic RAG now has a bounded allowlisted retrieval-routing baseline; knowledge graph traversal and self-reflective grading have executable offline baselines. Reranking is a twelfth family newly introduced as an executable mock-backed retrieval strategy; all **twelve strategy families have initial executable baselines**. The hybrid indexing stub is not implemented (only hybrid retrieval/fusion is), and the other baselines are not production-complete.


## Service-free integration work (2026-10-23)

New runtime slice: `factory/runtime.py` and `factory/runtime_config.py` build and validate keyword, semantic or hybrid pipelines from one YAML definition, using shared provider instances and consistent cleanup. `core/artifact_catalog.py` saves/loads versioned JSON index manifests for separate execution runs, and `RuntimePipeline.attach_artifacts()` validates externally produced metadata. Tests exercise full offline YAML indexing/retrieval and cross-execution manifest reuse against a shared mock store. See `docs/OFFLINE_RUNTIME.md`.

**Still pending without real services:** extend the unified factory to all other strategy families; reconcile common retrieval result contracts (IDs versus document tuples); make indexing/retrieval bindings individually configurable; support provider-defined physical mappings in the unified runtime; enforce configuration-defined artifact locators, integrity/authorization as separate concerns, and atomic or rollback-aware multi-index runs; broader mock end-to-end tests and robust lifecycle behavior. Real adapter implementation and external integration tests remain deferred.

## Unified factory integration (2026-10-23)

The opt-in `factory/unified.py` and `factory/unified_config.py` cover all 12 strategy families with independent indexing and retrieval bindings per named strategy. Retrieval outputs are normalized into `RetrievalHit(document_id, text=None)`; composite dependencies are checked for missing references and cycles. Services are validated before construction, shared by instance name and closed on exit or failed construction. Manifest attachment validates the entire supplied batch before mutation. The offline tests `test_unified_all_strategies.py` exercise all 12 kinds and YAML stage bindings, as well as cleanup and negative contract cases. See `docs/UNIFIED_FACTORY.md`.

**Next refinements, still possible offline:** durable relationship metadata for hierarchy, configuration-specific artifact identity and reuse checks, richer per-stage plan/config validation, adapter conformance fixtures, structured error reporting, and realistic end-to-end datasets. This is a separate opt-in API; the prior keyword/semantic runtime remains available.


## ragTools algorithm parity (2026-10-23)

Implemented new offline components in `dev`:

- `strategies/chunking/semantic.py`: sentence-boundary semantic chunking with injected embeddings, threshold and maximum-sentence limits; available as `semantic_chunking` indexing/retrieval kind in the unified factory.
- `strategies/query_expansion/hyde.py`: hypothetical-document expansion over an allowlisted source strategy; configured as `hyde` in the unified factory.
- `strategies/knowledge_graph/extraction.py`: explicit JSON link extraction from an injected LLM, allowlisting existing document IDs; separate `ExtractedGraphIndexer` composes it with the existing graph indexer. This is **document-link extraction**, not an ontology/entity database.
- `strategies/knowledge_graph/hybrid.py`: graph/vector reciprocal-rank fusion; configured as `graph_vector_hybrid` using two existing source strategies.
- `services/{document,graph,vector}/memory.py`: offline adapters, registered in the default service registry.

Remaining parity enhancements: first-class LLM entity extraction and typed knowledge graphs, self-reflective query refinement, richer agentic planning, HyDE embedding-specific transformations, distinct reranking implementations, production-grade chunk token alignment, fine-tuned model loading, evaluation benchmarks, and external providers. No real model or database services are provisioned.

An additional opt-in `query_refinement` retriever now performs bounded LLM rewriting after empty retrieval, without changing the default `self_reflective` grading algorithm. Existing query-refinement behavior is deliberately a separate composable strategy, not a full Self-RAG reasoning loop.
