# RAG Factory — canonical architecture

**Status:** Accepted target architecture, October 23, 2026. **Implementation status:** early scaffolding plus initial contracts; not a released or end-to-end tested framework.

This document is **normative** for new work on `dev`. See [deprecations](DEPRECATIONS.md) for superseded designs and [project structure](../PROJECT_STRUCTURE.md) for placement. Examples below are proposed interfaces/configuration, **not runnable APIs**.

## Objective

Construct, validate, execute and benchmark **composable indexing and retrieval pipelines** with interchangeable, configuration-selected service adapters and externally managed infrastructure. Support many implementations of one strategy, many retrieval strategies over compatible indexes, and reproducible choices for accuracy, latency, cost and resources.

## Concepts and ownership

- **Strategy:** algorithmic behavior, indexing and/or retrieval requirements, logical data model (when needed), relationships and required data operations. No provider imports or physical table names.
- **Service interface:** provider-neutral behavioral contract defined once per capability family (LLM, tokenizer, embedding, vector search, keyword search, graph, persistence, reranking).
- **Provider implementation/adapter:** code implementing a service interface. Shared across strategies; provider-specific logic stays here.
- **Service configuration:** named implementation instances with model/endpoint/credential references, tuning, and logical-to-physical **entity/field/relationship/operation mappings** where a model is needed.
- **Factory:** registers providers, resolves requirements against declared capabilities, verifies mappings and index compatibility, constructs adapters, injects them, manages owned client connections.
- **Pipeline:** explicitly composed indexing or retrieval steps/strategies, without assuming both sides use the same strategy. Start with sequential execution; allow parallel branches and bounded agent loops once required.
- **Index artifact/manifest:** persisted description of what indexing created, including resource references, schema/model versions, analyzer/preprocessing, embedding identity/dimension/metric, and access rights.
- **Experiment:** controlled execution and comparison across valid strategy/provider/configurations; records corpus/query sets, metrics, environment, index versions, costs and reproducible settings.

A **capability** is an operation a service offers, not a concrete provider or infrastructure deployment. Separately, an **index capability** describes what a produced artifact supports. Don't mix these namespaces. A single PostgreSQL deployment may provide relational, keyword and vector operations through one or more interface adapters.

## Indexing and retrieval independence

Each strategy declares requirements separately per phase. Some retrieval strategies (such as multi-query or agentic tool selection) consume pre-existing indexes and need no special indexing path. Retrieval can use artifacts produced by another strategy if compatible. Verify more than the index's feature labels: embedding model identity/revision, dimension, normalization/metric, analyzers/tokenizers, schema, field mappings, operation semantics and permissions.

If a strategy needs persistent data, it declares **logical entities and operations**. The service configuration maps them onto physical tables, collections, fields, relations and search indexes in existing infrastructure. The provider validates **structural and operational compatibility**. A matching column doesn't imply support for a requested ranking/search operation. Share logical models only when their semantics match.

## Separation of source, configuration and infrastructure

**Inside repository:** interfaces, provider adapters, algorithms, validators, factory, pipelines, experiments and safe example configuration. **Configuration:** instance names, provider identifiers, URL/DSN references, model IDs and logical-to-physical mappings. **Outside runtime ownership:** database installations, model servers, model assets, cloud deployments. Explicit in-process local/in-memory providers are allowed.

Factory construction must not silently download a model, start a server, create a database, or migrate a schema. Separate read-only validation from explicit admin/migration commands. Adapters/connections may be shared when configuration, thread safety and lifecycle are compatible; sharing one provider implementation does **not** imply sharing an instance.

## Target ownership layout

```text
src/rag_factory/
  core/             # capability, mapping and artifact contracts
  services/         # interfaces and adapters shared across strategies
  strategies/       # per-phase requirements, algorithm code and logical models
  factory/          # registry, config resolver, validation, lifecycle
  pipelines/        # indexing/retrieval composition and execution
  evaluation/       # datasets, metrics, experiment runs and comparison
  cli/              # optional external-facing adapter
```

Existing `shared/services`, schema generation, migrations, and agent tooling remain in the tree until explicit refactoring. The layout is a target, not current implementation status. A mandatory extra `components/` or `processors/` layer is **not** part of the design.

## Proposed example (not yet executable)

```yaml
services:
  keyword_main:
    interface: keyword_store
    implementation: postgres_fts
    connection:
      dsn: ${DATABASE_URL}
    mapping:
      Document:
        table: documents
        fields: {id: document_id, content: body}
      Chunk:
        table: chunks
        fields: {id: chunk_id, document_id: document_fk, content: chunk_text}
    search:
      language: english
      ranking: ts_rank_cd
pipelines:
  indexing:
    strategy: keyword
    services: {keyword_store: keyword_main}
  retrieval:
    strategy: keyword
    services: {keyword_store: keyword_main}
```

Provider-specific mappings may include relations, types, indexes and query configuration. Mappings are declarations, not schema creation instructions.

## Validation levels

1. **Contract:** provider conforms to interface and implements declared operation capabilities.
2. **Configuration:** required endpoint/model/credentials references and mapping fields are supplied (without exposing secrets).
3. **Environment:** optional preflight tests that external services are reachable and support advertised operations.
4. **Artifact compatibility:** indexed data and retriever agree on model/schema/analyzer/metric semantics and permissions.
5. **Execution:** errors are explicit, with cleanup and reproducible provenance.

## Testing and evaluation

The implementation rules for test placement, isolation, provider-contract suites and CI gates are in [the testing standard](../standards/TESTING.md).

- Unit: algorithms and contracts without a running database/model.
- Adapter contract: at least two providers satisfy one interface.
- Integration: externally provisioned services used only with explicit test setup.
- Cross-strategy: one compatible index used by multiple retrievers without forced reindexing.
- Benchmark: fixed datasets and relevance judgments; measure recall/nDCG, p50/p95 latency, indexing cost, query cost, throughput and infrastructure/model versions; don't compare runs without provenance.

## Incremental delivery

1. Update docs, packaging, contracts and tests.
2. Implement keyword indexing/retrieval with a local in-memory implementation.
3. Switch to a separately configured PostgreSQL FTS provider without altering the strategy.
4. Add semantic indexes, manifests and cross-strategy/hybrid retrieval.
5. Add reproducible experiment orchestration.
6. Expand to contextual, hierarchical, graph and agentic workflows as interfaces prove adequate.

Architectural decisions must be revised in this document before changing their boundaries in implementation.


## Implemented contract baseline (2026-10-23)

The following provider-independent Python modules now exist on `dev`:

- `core/service_contracts.py`: `ServiceRequirement`, `ProviderDescriptor`, `StrategyRequirements`, `validate_service_bindings` for named service instances and separate indexing/retrieval requirements.
- `core/mapping.py`: `LogicalEntity`, `LogicalModel`, `EntityMapping`, `StorageMapping`, `validate_storage_mapping` for required fields, relationships and storage operations.
- `core/index_manifest.py`: `IndexManifest`, `IndexRequirement`, `validate_index_compatibility` for conservative artifact metadata validation.

Unit tests: `tests/unit/core/test_service_and_mapping_contracts.py`.

**Scope limitations:** these are declarative contracts, not a provider registry/factory, physical database schema introspection, executable pipelines or verified environment checks. Index manifest validation compares explicitly declared fields; it does not yet validate all provider-specific semantics or permissions. Existing `core/capabilities.py` and historical interface placeholders remain for incremental migration; do not conflate its legacy index capabilities with new provider service capabilities. Tests were written but have not been executed in this GitHub editing session.


## First configuration-driven keyword factory slice (2026-10-23)

Implemented under `factory/service_registry.py` and `factory/rag_factory.py`:
- Explicit registration of provider descriptors and constructors.
- Named `ServiceConfig` instances, explicit interface-to-instance bindings and declared-capability checks.
- A keyword pipeline builder using injected provider-neutral interfaces.
- Two infrastructure-free production examples: `services/keyword/memory.py` and `services/tokenizer/regex.py`; test mocks remain under `tests/mocks/`.
- Tests in `tests/unit/core/test_factory_keyword.py` exercise swapping providers using configuration without changing strategy code, and invalid configurations.

**Limitations:** this slice uses Python configuration objects, not a YAML loader; it does not yet support external provider adapters, physical mapping validation during factory construction, index manifests emitted from indexing, generic strategy registration, lifecycle/cleanup hooks or preflight checks. The in-memory ranking is simple token frequency matching, not BM25. Factory construction currently resolves configured instances before all requirements have been validated; future work should validate metadata first and manage rollback/cleanup of partially created instances.


## Configuration and lifecycle update

The initial keyword factory now supports a YAML loader at `factory/config.py` using `yaml.safe_load`, environment-variable substitution for complete `${VARIABLE}` scalar values, and named instance bindings. The implementation does **not** yet read the broad illustrative `pipelines:` format shown earlier: the implemented keyword-only YAML format is:

```yaml
services:
  keywords:
    interface: keyword_store
    implementation: memory
  tokens:
    interface: tokenizer
    implementation: regex
keyword:
  bindings:
    keyword_store: keywords
    tokenizer: tokens
```

Use `load_keyword_config(path)`, then `RAGFactory().build_keyword(config.services, config.bindings)`. The keyword pipeline supports a `with` context manager and closes owned adapters exposing `close()`. Provider declarations and requirements are checked **before** any provider constructor is called. Physical mapping support in YAML and generic pipeline definitions remain outstanding.


## Mock-backed composition milestone (2026-10-23)

`pipelines/indexing.py` now composes named indexing steps, while `pipelines/retrieval.py` composes independently configured retrieval sources. `strategies/hybrid_search/retriever.py` implements deterministic reciprocal-rank fusion (RRF) across their ranked result identifiers. `evaluation/metrics.py` provides offline `recall_at_k` and `reciprocal_rank_at_k` for fixed relevance judgments. `tests/unit/core/test_composition.py` exercises these pieces using mock keyword, embedding and vector stores and runs in Python 3.12 CI.

These are **lightweight first implementations**, not a generic pipeline DAG, statistical evaluation framework, vector-model quality benchmark or complete artifact registry. Retrieval sources currently use explicitly supplied Python callables; the semantic retriever checks its manifest at retrieval time. Automatic YAML pipeline construction, indexing manifests for the keyword store, advanced strategies (multi-query, contextual and hierarchical), and full reproducible experiment orchestration are still future milestones. No external infrastructure is required for these tests.


## Mock-only multi-query and offline experiment milestone (2026-10-23)

The query-expansion component `strategies/query_expansion/expansion/expander.py` uses the LLM interface to request a bounded number of textual alternatives, including the original query. `strategies/multi_query/retriever.py` searches each variant through an injected retrieval callable and fuses ranks; `strategies/query_expansion/retriever.py` provides the same behavior as a strategy wrapper. Tests use `MockLLM` and offline retrieval stubs. Responses are parsed as one variant per line; real-LLM prompt robustness remains unvalidated.

`evaluation/runner.py` provides a **minimal, deterministic, offline** comparison of retrieval callables using fixed query relevance sets, mean recall@k and mean reciprocal rank@k. It intentionally does not claim latency/cost measurements, dataset provenance persistence, confidence intervals or reproducible model benchmarks. These require later experiment orchestration and integration work.
