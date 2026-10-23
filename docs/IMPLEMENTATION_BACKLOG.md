# Implementation backlog (2026-10-23)

Tracked implementation priorities on `dev`. The first item is the currently selected delivery slice. All early slices run offline; real providers remain deferred.

| Priority | Work | Acceptance criteria | Status |
| --- | --- | --- | --- |
| 1 | Contextual retrieval | LLM-generated bounded chunk context, index/search via interfaces, preserve original text, tests with mocks | Implemented in this change |
| 2 | Hierarchical retrieval | Parent/child indexing and expansion with deterministic mock storage and validated relationships | Pending |
| 3 | Retrieval strategy registry and configuration | Generic strategy selection and composition from config rather than manually constructed callables | Pending |
| 4 | Shared provider behavioral contracts | Parameterized conformance tests for each interface including lifecycle and error semantics | Pending |
| 5 | Index artifact and mapping hardening | Keyword manifests, persistence locators, permissions, embedding revision, operational mapping validation | Pending |
| 6 | Evaluations and reproducibility | Versioned datasets, judgments, nDCG, experiment metadata and saved reports | Pending |
| 7 | Remaining advanced strategies | Reranking, graph, self-reflective, late-chunking and agentic vertical slices, scoped individually | Pending |
| 8 | Real service adapters | Postgres FTS/vector, model/LLM providers and opt-in integration tests | Deferred until infrastructure is available |

A checked-in source file containing only a stub is not an implemented feature. Tests in `tests/unit/core` are the current correctness gate on Python 3.12.
