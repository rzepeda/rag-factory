# Historical process-centric principles (superseded)

> **SUPERSEDED on 2026-10-23.** This document records the prior architectural direction only. Do not use it as implementation guidance. The normative design is [RAG_FACTORY_DESIGN.md](RAG_FACTORY_DESIGN.md); see [DEPRECATIONS.md](DEPRECATIONS.md).

The former proposal made `processors/`, `handlers/`, `strategies/` and strategy-local entities/migrations a mandatory layering pattern. That was useful for considering single-responsibility operations, but it introduced unnecessary indirection for the chosen framework.

## Principles retained

- Small, testable operations and clear contracts.
- Separate orchestration from provider implementation.
- Prefer stateless logic and explicit dependency injection.
- Independent unit, integration and benchmark tests.
- No circular dependencies and no infrastructure provisioning inside core.

## Principles superseded

- A mandatory `components/` or `processors/` directory for every processing step.
- Universal `Processor` / `Handler` interfaces and an obligatory wrapper between strategies and services.
- Treating every strategy as one end-to-end index-and-query object.
- Requiring one physical entity schema or automatic migration per strategy.
- Treating model servers and databases as assets to bundle, load, install or start as part of factory creation.
- Treating a directory scaffold as proof of implemented functionality.

## Current rule

Strategies define distinct indexing and retrieval behavior, service capability requirements and logical models. Service interfaces and their provider implementations are reusable. Configuration chooses provider instances and physical mappings. The factory resolves and validates compatibility. Pipelines compose operations. Experiments measure configurations.

See the canonical design for precise boundaries and lifecycle responsibilities.
