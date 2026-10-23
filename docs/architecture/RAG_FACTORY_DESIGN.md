# RAG Factory architecture — initial decision record

Status: accepted as implementation direction (2026-10-23).

## Purpose

RAG Factory constructs, validates, executes and benchmarks composable RAG indexing and retrieval pipelines with interchangeable service implementations. The framework does not provision databases or model servers.

## Boundaries

1. **Strategy**: indexing or retrieval behavior, required service capabilities, logical entities and persistence operations. Indexing and retrieval requirements are declared separately.
2. **Service interface**: provider-neutral operations (LLM, tokenizer, embeddings, keyword store, vector store, database, etc.).
3. **Service adapter**: code that implements an interface for a provider. Defined once, reusable across strategies.
4. **Service configuration**: named provider instance, endpoint/credentials references, model choices, and logical-to-physical model mappings.
5. **Factory**: resolves providers, validates requirements and mappings, creates adapters, and manages owned connections.
6. **Pipeline**: composes strategy operations; indexing can run independently of retrieval.
7. **Index manifest**: describes produced artifacts (schema, model/version, embedding space, analyzers, physical locations) for compatibility checking.
8. **Evaluation**: reproducible comparisons of valid strategy/provider configurations including quality, latency, cost and indexing expense.

## Persistence rules

The strategy defines logical entities, fields, relationships and required operations, **not physical table names**.
The configured provider binds logical entities and fields to externally managed tables, collections, properties and indexes.
Mapping compatibility checks **both structural fields and required operations**. A matching column alone does not prove keyword or vector search is supported.
Schema validation is separate from migration; strategy instantiation must not silently create/alter storage.

## Service lifecycle

The framework owns adapter instances/connections it constructs, not the databases, model deployments or other infrastructure behind them. Reuse a service instance only when its configuration and safety/lifetime constraints permit it. Allow an in-memory backend as an explicit provider.

## Delivery order

1. Establish contracts, mapping schema, packaging and unit tests.
2. Complete keyword indexing/retrieval with an in-memory provider.
3. Configure a second keyword provider (e.g. external PostgreSQL FTS) without modifying strategy code.
4. Add semantic retrieval and index manifests, then cross-strategy and hybrid retrieval.
5. Implement experimental runs with reproducible measurements and artifact reuse.

Avoid introducing mandatory relational ORM models, automatic migrations, a universal DAG executor or an agent framework before the corresponding use case demands them.

## Example configuration (proposed; not yet executable)

```yaml
services:
  keyword_store_main:
    interface: keyword_store
    implementation: postgres_fts
    connection:
      dsn: ${DATABASE_URL}
    mapping:
      Document:
        table: documents
        fields:
          id: document_id
          content: body
      Chunk:
        table: chunks
        fields:
          id: chunk_id
          document_id: document_fk
          content: chunk_text
    search:
      language: english
      ranking: ts_rank_cd
pipelines:
  index:
    strategy: keyword
    services:
      keyword_store: keyword_store_main
  retrieve:
    strategy: keyword
    services:
      keyword_store: keyword_store_main
```

No secrets or infrastructure state belong in repository configuration.
