# Project coding standards and architecture guardrails

Use PEP 8, Black and meaningful type annotations. Avoid circular imports and shell commands in core logic.

## Implementation guardrails

1. Strategy code must depend on service **interfaces**, not concrete provider SDKs.
2. Indexing and retrieval requirements are independent.
3. Define logical models and required operations in strategies; configure physical database mappings in service instances.
4. Configuration must not trigger infrastructure provisioning, model downloading or implicit database schema migrations.
5. Service implementations are reusable; service **instances** are named/configurable and only shared when safe.
6. Keep external infrastructure optional for unit tests. Provider integration tests need explicit external setup.
7. Validate service capabilities, structural and operational mappings, and index/retriever compatibility before execution.
8. Mark configuration examples as proposed until actually executable and tested.
9. A dedicated processor/component layer is optional—not a universal interface every operation must implement.
10. Don't introduce strategy-specific database schemas or migrations for strategies that have no persistence need.

See [canonical architecture](../architecture/RAG_FACTORY_DESIGN.md) and [deprecations](../architecture/DEPRECATIONS.md).

## Testing

Follow the [testing standard](TESTING.md) for test categories, fixtures, provider contracts, safe external integration, CI scope and definition of done.
