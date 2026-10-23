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
| 7 | Remaining advanced strategies | Reranking, graph, self-reflective, late-chunking and agentic vertical slices, scoped individually | Reranking implemented (mock-backed); four remaining |
| 8 | Real service adapters | Postgres FTS/vector, model/LLM providers and opt-in integration tests | Deferred until infrastructure is available |

A checked-in source file containing only a stub is not an implemented feature. Tests in `tests/unit/core` are the current correctness gate on Python 3.12.

## Advanced strategy inventory

The source tree contains 11 original strategy families. Seven currently have an executable baseline (keyword, semantic, hybrid retrieval, multi-query, query expansion, contextual, hierarchical). Four have only placeholder indexer/retriever implementations: knowledge graph, late chunking, self-reflective, and agentic RAG. Reranking is a twelfth family newly introduced as an executable mock-backed retrieval strategy; the advanced-strategy backlog now has **four missing families**. The hybrid indexing stub is not implemented (only hybrid retrieval/fusion is), and the other baselines are not production-complete.
