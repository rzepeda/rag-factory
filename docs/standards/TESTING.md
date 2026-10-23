# Testing standard

**Status:** Accepted on `dev` (2026-10-23). This is the normative guidance for tests in RAG Factory. The current CI tests only the implemented core-contract area; other test directories contain scaffolds and must not be counted as verified coverage.

## Principles

- Tests verify observable behavior and architecture contracts, not implementation details.
- Every changed behavior needs a focused test. Every bug fix should include a regression test reproducing the failure.
- Make tests deterministic, order-independent, repeatable, and safe to run locally.
- Never require real APIs, databases, credentials, model downloads, GPU hardware or network access to run **unit tests**.
- Do not treat placeholder test files as coverage. A passing suite does not prove untested strategies work.
- Test the separately declared indexing and retrieval requirements, as well as compatible index reuse across strategies.

## Test categories and locations

| Category | Location | What it checks | Default environment |
| --- | --- | --- | --- |
| Unit | `tests/unit/` | Pure logic, contracts, validation, algorithms | Offline |
| Adapter contract | `tests/contracts/` (add when adapters exist) | Each provider obeys the same interface semantics | In-memory/fake locally; real adapter suites explicit |
| Integration | `tests/integration/` | Real adapter + externally provisioned service | Explicit isolated test infrastructure |
| End-to-end | `tests/e2e/` | Config → factory → independent indexing/retrieval → result | Explicit opt-in until local self-contained slice exists |
| Performance/evaluation | `tests/performance/` | Reproducible speed, quality, cost, provenance | Separate from correctness gate |

Within a category, mirror the source package where useful (e.g., `tests/unit/core/test_mapping.py`). Test filenames must be `test_*.py`; test functions must be `test_*`. Give names that state observable outcomes (`test_missing_field_mapping_is_rejected`).

## Fixtures, fakes and mocks

Prefer concrete tiny in-memory implementations or purpose-built fakes that implement the **service interface**. Use mocks only where interaction verification matters (such as confirming cleanup or preventing a remote call). Centralize broadly reusable fixtures in `tests/conftest.py` or `tests/fixtures/`; keep domain-specific fixtures close to their tests.

Provider contract suites must exercise the same operations, failure semantics, returned types and lifecycle behavior against each implementation, not merely inspect subclass declarations. Parameterize fixtures by provider. Providers backed by external resources run these tests with explicitly configured test-only endpoints.

## Data models and mappings

Test: missing logical fields; unmapped relations; required operations absent from a provider mapping; invalid names; multiple independent mappings of the same model; no implicit schema modification. Provider integration tests additionally validate physical column/types/indexes and supported query semantics on an isolated schema.

## Artifacts and pipeline compatibility

Cover missing index capabilities, schema mismatch, embedding model and dimension mismatch, distance metric/analyzer mismatch, and known valid cross-strategy reuse. Validate incompatible combinations **before** starting a pipeline; do not assume a capability set alone proves compatibility.

## Infrastructure safety

- Integration tests use dedicated disposable databases/collections or namespaces, not production.
- Never assume PostgreSQL, Ollama or another service is running on the contributor's machine.
- No secrets, credentials or real customer data in fixtures, recordings or CI logs.
- External provider calls and migrations must be explicitly opted into; cleanup all resources created by tests.
- Unit test imports and constructors must not initiate model downloads, schema migrations, network calls or subprocess-driven provisioning.

## Execution and CI

Install from the repository root:

```bash
python -m pip install -e ".[test]"
python -m pytest tests/unit/core -v
python -m build
```

The **current baseline** is `tests/unit/core`, on Python 3.10, 3.11 and 3.12. GitHub Actions builds wheel/sdist, runs this directory, and verifies installable wheel imports. As implementation expands, extend CI's explicitly included test paths. Do not replace it with an unrestricted `pytest` run until legacy placeholders have been triaged.

Use markers for new opt-in test suites: `integration`, `e2e`, `external`, `performance`. The CI correctness gate should run offline unit and fake-backed contract tests; external integration and performance jobs require separate infrastructure and are not part of the default gate.

## Coverage policy

Do not impose an arbitrary global percentage while most source files remain placeholders. Record and publish coverage only for executable modules under test when coverage tooling is added. Require meaningful branches and failure cases for new contracts; set minimum thresholds only after collecting a reliable baseline. Do not inflate metrics with scaffold files or empty tests.

## Definition of done for a feature

1. Unit tests cover success, validation failures and error paths.
2. Adapter implementation passes its shared contract tests.
3. If dependent on external infrastructure, integration tests are available and documented with safe setup/teardown.
4. CI includes the feature's offline tests and passes supported Python versions.
5. Architecture and config examples updated to match actual behavior, with unimplemented examples explicitly labeled.
6. For persisted indexes, compatibility and artifact reuse behavior are tested.

See [canonical architecture](../architecture/RAG_FACTORY_DESIGN.md) and [coding guardrails](style_and_restrictions.md).


## Implemented first vertical slice

`tests/mocks/services.py` contains eight **test-only** deterministic implementations of the currently introduced service interfaces: LLM, tokenizer, embedding, vector store, keyword store, graph store, reranker and document store. They avoid networking and real infrastructure, and are not substitutes for real provider adapters.

`strategies/keyword_search/indexer.py` and `retriever.py` implement the first small strategy against injected `KeywordStoreService` and `TokenizerService` protocols. `tests/unit/core/test_keyword_strategy.py` checks behavior, deterministic mocks and invalid inputs. Its in-memory keyword backend counts term occurrences; it is **not BM25, PostgreSQL FTS, or a production search implementation**. Strategy-level indexing/retrieval manifests and the configuration-driven factory remain future work.

Run these tests through the offline core suite:

```bash
python -m pytest tests/unit/core -v
```
