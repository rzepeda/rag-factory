# RAG Factory

**Status: architecture reset / early implementation on `dev`.** Most strategy, factory, provider and test modules are scaffolds, not functioning features. Do not interpret file presence, example code or dependency names as evidence of a released, working API.

RAG Factory is a **configuration-driven framework for constructing, validating, running and benchmarking composable RAG indexing and retrieval pipelines** with interchangeable provider adapters and externally managed services.

## Canonical documentation

- [Architecture and boundaries](docs/architecture/RAG_FACTORY_DESIGN.md) — normative design.
- [Project structure](docs/PROJECT_STRUCTURE.md) — current vs target layout.
- [Superseded concepts](docs/architecture/DEPRECATIONS.md) — migration guidance and deprecated assumptions.
- [Architecture decision records](docs/architecture/decisions/README.md).
- [Testing standard](docs/standards/TESTING.md) — how tests are written, isolated and run in CI.

When older documents, examples or scaffolds conflict, follow the canonical architecture document. Do not implement placeholder descriptions as product requirements.

## Key concepts

- **Strategy** defines algorithmic indexing/retrieval behavior, required capabilities, logical entities and persistence operations.
- **Service interface** defines reusable operations, implemented once per provider adapter (OpenAI, Ollama, PostgreSQL, etc.).
- **Service configuration** selects a named provider instance, its endpoint/model settings, and logical-to-physical mappings where required.
- **Factory** resolves and validates dependencies and creates adapters; it does not start model servers or provision databases.
- **Pipeline** composes independently executable indexing and retrieval strategies. A compatible index may be reused by different retrieval strategies.
- **Index manifest** records what was produced and the compatibility metadata needed for reuse.
- **Evaluation** tests valid combinations under reproducible quality, latency, cost and resource constraints.

Infrastructure is externally managed by default. Local in-process providers are allowed as explicit choices.

## Development

The first vertical slice is keyword indexing/retrieval with an in-memory provider, followed by a second externally configured provider. After that: semantic and cross-strategy retrieval, then experimentation.

**Installation examples and APIs from the original scaffold are not verified and have been removed from this README until packaging and an executable quick start are established.**

See the [architecture document](docs/architecture/RAG_FACTORY_DESIGN.md) for a proposed YAML example. It is not yet runnable.
