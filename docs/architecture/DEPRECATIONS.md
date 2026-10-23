# Superseded designs and migration register

**Scope: dev architecture reset.** Deprecated means no longer a design requirement; it does not mean existing code has been deleted or migrated.

| Former assumption | Status | Replacement |
| --- | --- | --- |
| One indivisible end-to-end RAG strategy | Superseded | Independent indexing and retrieval and composable pipelines |
| Same strategy must index and retrieve | Superseded | Compatible index artifacts reused across strategies |
| Every strategy requires relational models/repositories/migrations | Superseded | Logical models and persistence operations only where needed |
| Mandatory SQLAlchemy/dynamic model generation | Superseded as universal rule | Optional adapter-specific implementation |
| Physical schema defined by strategy | Superseded | Strategy defines logical model; service configuration maps physical structures |
| Database/model deployment bundled or started by framework | Superseded | External managed infrastructure; optional in-process providers |
| Strategies import concrete providers | Superseded | Interfaces, adapters, configured provider instances |
| Mandatory components/processors/handlers layer | Superseded | Direct strategy operations; reusable processors only on demonstrated need |
| Implicit schema creation on factory construction | Prohibited by default | Separate explicit schema validation and migration action |
| Capability labels alone guarantee index compatibility | Insufficient | Validate model/version, dimensions, schema, analyzers, operations and permissions |
| One global service object for all strategies | Superseded | Named configured instances with safe optional reuse |
| DAG and agent runtime as mandatory core | Deferred | Simple pipelines first, add branching/loops when needed |
| Placeholder files imply functionality | Incorrect | Only executable, tested code counts |

## Retain

Keep the good ideas: strategy-owned logical entity requirements; separate indexing/retrieval; shared service interfaces; configurable physical mappings; explicit dependency injection; optional provider-specific migrations; and artifact compatibility.

## Migration guardrails

1. Do not delete old scaffolds merely because their approach is deprecated; remove them with tested replacements.
2. Distinguish *proposed design*, *implemented behavior* and *verified tests*.
3. Never store credentials, model binaries, or live infrastructure in the repository.
4. Provisioning and migrations must not be side effects of loading configuration or constructing a strategy.
5. When changing an accepted boundary, update the canonical architecture and this register together.
