# Project structure and ownership

**Status:** Target architecture and migration map, not a claim that these modules are implemented.  
**Authority:** [RAG Factory architecture](architecture/RAG_FACTORY_DESIGN.md).  
For discarded assumptions, see [deprecations](architecture/DEPRECATIONS.md).

## Target structure

```text
src/rag_factory/
  core/          # capability / artifact / mapping contracts, pure validation
  services/      # common service interfaces + provider-specific adapters
  strategies/    # indexing and retrieval logic, requirements, logical models
  factory/       # provider registry, configuration resolution, instantiation
  pipelines/     # independent indexing and retrieval composition/execution
  evaluation/    # experiment definitions, metrics, repeatable comparisons
  cli/           # optional application adapter, not core logic
config/          # examples of service instances, mappings, pipelines
tests/           # unit, integration, contract, performance tests
docs/            # normative architecture and ADRs
agent_tools/     # optional developer automation; not runtime dependency
```

This is a **logical ownership layout**. The current repository still contains `shared/services/`, `shared/database/`, `shared/repositories/`, strategy-local `schema/` and `migrations/`, and numerous placeholders. Do not move or delete files solely to match the diagram. Refactor as part of tested vertical slices.

## Ownership rules

| Owner | Defines | Must not own |
| --- | --- | --- |
| Strategy | Index/retrieval algorithms, separate stage requirements, logical entities/relationships and operations | Provider selection, table names, infrastructure provisioning |
| Service interface | Provider-neutral operation contracts and feature semantics | Deployment endpoint or specific implementation |
| Provider adapter | Implementation of interface for a technology | Strategy-specific algorithms or mandatory infrastructure startup |
| Service configuration | Named instances, credentials references, endpoints, models, entity/field/operation mappings | Runtime algorithm implementation |
| Factory | Registration, resolution, validation, instance lifecycle | Database server deployment or implicit schema migrations |
| Pipeline | Composition/execution and input/output contracts | Hardcoded provider choices |
| Evaluation | Reproducible comparisons, provenance and trade-offs | Modifying strategy implementations during experiments |

## Persistence and models

If a strategy requires persistence it defines a **logical model** plus required operations. The chosen provider configuration maps logical entities, fields, relationships and search requirements to an external physical schema. The provider validates mapping coverage **and** operational support. Do not require SQLAlchemy, an entity repository or generated migrations of strategies that do not need them. Shared logical entity definitions may be reused when semantics are identical.

Index artifacts are first-class outputs. Retrieval may use another strategy's compatible artifact; compatibility is more than capability set inclusion (for example embedding model, dimensions, normalization, analyzers, schema and access permissions).

## Tests and delivery

- Unit: contracts, validators and pure algorithm behavior.
- Provider contract: different adapters satisfy one shared interface.
- Integration: external systems only in explicitly configured test environments.
- End-to-end: service swapping by config; retrieval against a compatible independent index.
- Benchmark: reproducible datasets, quality, latency/cost and hardware/provider provenance.

Do not claim a placeholder test is executable. First deliver working packaging and a keyword vertical slice.

## Historical guidance

The old document described processor-first organization, universal entity-repositories, auto-generated SQLAlchemy models and fixed strategy migrations. These are **not** mandatory design requirements; see the deprecation register.
