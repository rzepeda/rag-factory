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

## Framework-first roadmap (2026-10-26)

This roadmap supersedes the earlier algorithm-parity ordering above. Baseline algorithms remain intentionally unchanged until the experimental infrastructure is established.

### P0 — Framework correctness and integration

**Completed for the supported offline unified-factory scope (6/6).** This is
a deterministic, mock/in-memory framework acceptance gate, **not** a claim of
transactional writes, durable external-provider data, or provider authorization.

| Requirement | Status | Evidence / acceptance |
| --- | --- | --- |
| Configuration and dependency validation | **Done** | Pre-construction capability and reference/cycle validation; supported numeric bounds and required artifact metadata validated; `test_p0_configuration_validation.py` |
| Unified factory lifecycle and cleanup | **Done** | Reverse-order cleanup, all closers attempted, original constructor/context errors preserved; `test_p0_lifecycle.py` |
| Standardized indexing and retrieval contracts | **Done** | Preflight validation for all seven indexed kinds, `IndexManifest` returned only on success, typed `RetrievalHit` output with positive integer limits; `test_p0_index_contracts.py` |
| Artifact persistence and compatibility | **Done (metadata scope)** | Versioned atomic manifest/hierarchy catalogs and single-file artifact bundle; configured artifact identity/scope/locator checks; cross-execution attach and compatibility tests; `test_p0_artifact_bundle.py`, `test_p0_hierarchy_catalog.py` |
| Failure injection and recovery | **Done (fail-closed scope)** | Constructor/close errors, catalog replacement failures and partial provider writes covered; failed index quarantined until successful rebuild; `test_p0_multistore_failures.py`, `test_p0_index_contracts.py` |
| End-to-end offline acceptance | **Done** | All 16 supported unified strategy kinds exercised together with deterministic mocks, and a separate-execution artifact handoff tested; `test_p0_all_variants_acceptance.py`, `test_p0_artifact_bundle.py` |

**Boundary:** Providers can leave partially written physical data when they
raise. P0 prevents publishing/reusing the affected metadata *within the
current pipeline*; it does not roll back database writes or prove that an
external index is safe after a process restart. Real service adapters,
provider-owned transactions, index inspection and authorization belong to
later integration/production work. Index algorithms are left as baselines.

### P1 — Experimental infrastructure (current phase)

**Completed for the supported offline scope (4/4).** Retrieval-quality metrics
remain informational by default; only explicit opt-in quality gates can fail
on a lower score. Implementations of retrieval algorithms remain unchanged.

| Requirement | Status | Evidence / acceptance |
| --- | --- | --- |
| Versioned datasets and graded relevance judgments | **Done** | Immutable snapshots, strict versioned JSON load/save, content SHA-256, checked-in fixture; `evaluation/dataset.py`, `test_p1_metrics_and_datasets.py` |
| Recall@K, Precision@K, MRR@K, nDCG@K | **Done** | Shared top-k/deduplication/grade semantics, per-query and aggregate scores, graded nDCG; `evaluation/metrics.py`, `evaluation/runner.py`, `test_p1_metrics_and_datasets.py` |
| Reproducible experiment configurations, execution, artifacts and metadata | **Done** | Versioned standalone config, source revision and strategy settings, dataset/config fingerprints, deterministic per-query report JSON, opt-in latency, offline unified-factory example; `evaluation/experiment.py`, `test_p1_experiment_workflow.py` |
| Strategy comparison and cross-version regression detection | **Done** | Compatible dataset/query/k checks, per-metric deltas, tolerance thresholds, advisory regressions and explicit opt-in gates; `evaluation/comparison.py`, `test_p1_experiment_workflow.py` |

See `docs/EVALUATION_EXPERIMENTS.md` and run
`python examples/offline_evaluation_example.py`.
This is an **offline experimental harness**, not evidence that a model, provider,
or retrieval strategy is production-grade. Real-run nondeterminism, statistical
significance/confidence intervals, and provider costs are future extensions,
not P1 completion prerequisites.

### P2 — Developer experience and integration readiness (current phase)

**Completed for the supported offline integration-readiness scope (7/7).**
The CLI is intentionally ephemeral with built-in memory providers; physical
provider persistence, external accounts, and live connectivity are NOT part of
this acceptance gate.

| Requirement | Status | Evidence / acceptance |
| --- | --- | --- |
| Runnable offline index → retrieve → evaluate walkthrough | **Done** | Existing `examples/offline_evaluation_example.py`; command-based replay and versioned fixtures in `examples/offline_cli.yaml` and `examples/evaluation/` |
| YAML config examples and schema diagnostics | **Done** | Side-effect-free `validate_unified_configuration`, strict YAML top-level/service/strategy fields and stage bindings, source-path diagnostics; `test_p2_cli.py` |
| CLI validate / index / retrieve / evaluate | **Done (offline)** | Installable `rag-factory` command, JSON outputs, clear exit codes, temporary in-memory indexing and optional artifact metadata bundle; `test_p2_cli.py` |
| Reusable provider conformance suite | **Done** | Behavioral checks for eight service interfaces, exercised with mock and memory adapters; `rag_factory.testing.provider_contracts`, `test_p2_provider_conformance.py` |
| Offline vs. opt-in live integration test boundary | **Done (harness)** | Core CI is mock/memory-only; `tests/integration/test_live_provider_contracts.py` runs only when external constructor/interface env vars are specified; skip and mock opt-in tested in `test_p2_live_boundary.py` |
| Structured observability and failure diagnostics | **Done** | Opt-in stage/strategy/duration/status/error-type events, observer isolation and `--trace` CLI JSON stderr without query/document text; `test_p2_observability.py` and `test_p2_cli.py` |
| Provider/strategy extension guides | **Done** | Concrete registration, descriptor/conformance and lifecycle examples, strategy integration checklist in `docs/EXTENDING_UNIFIED_FRAMEWORK.md` |

See `docs/CLI_OFFLINE.md` and `docs/EXTENDING_UNIFIED_FRAMEWORK.md`.
No evaluation score gates are enabled by default. The local CLI replays source
payloads on each execution because memory stores do not survive process exit;
metadata bundles do not contain physical indexes. The opt-in live harness is
not evidence that a real provider has been tested.

### P3 — Strategy algorithm improvements (next phase; all pending)

Before changing any strategy, save an immutable P1 experiment baseline with
the same dataset, k, provider configuration and code revision. Preserve old
behavior for comparisons and report per-metric deltas; never fail core CI on
low quality by default.

| Workstream | Status | Experiment-led acceptance criteria |
| --- | --- | --- |
| Semantic boundary chunking and chunk-size/token alignment | **Pending** | Compare chunk-level recall/rank quality and index sizes against retained baseline |
| HyDE and multi-query query expansion quality | **Pending** | Compare prompt/query variants with stable dataset, latency and recall/nDCG metrics |
| Typed entity extraction and knowledge-graph retrieval | **Pending** | Add typed entity/relation schema, extraction validation and compare graph search vs document-link baseline |
| Self-reflection, query refinement and agentic routing | **Pending** | Compare bounded retries, tool choice, failure rates and quality against old behavior |
| Reranking and hybrid/graph-vector score fusion | **Pending** | Compare rank metrics/latency to lexical/vector/hybrid baseline with per-query reports |
| Late chunking, hierarchy and contextual retrieval refinements | **Pending** | Measure token alignment, hierarchy expansion, context value, index costs and ranking improvements |

P4 remains optional production throughput, batching, cost and scaling
optimization **after** live providers and the P3 measured improvements.
