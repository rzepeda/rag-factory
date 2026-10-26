# P2 offline CLI and YAML configuration

The unified CLI uses only the providers registered in `default_registry()`.
It deliberately does **not** provision hosted LLMs or external databases.
All examples run on Python 3.12 without credentials or network access.

## Install and run

```bash
python -m pip install -e ".[test]"
rag-factory validate --config examples/offline_cli.yaml

rag-factory index \
  --config examples/offline_cli.yaml \
  --payloads examples/evaluation/offline_payloads.v1.json \
  --bundle /tmp/rag-indexes.bundle.json

rag-factory retrieve \
  --config examples/offline_cli.yaml \
  --payloads examples/evaluation/offline_payloads.v1.json \
  --strategy lexical --query "cats" --limit 3

rag-factory evaluate \
  --config examples/offline_cli.yaml \
  --payloads examples/evaluation/offline_payloads.v1.json \
  --dataset examples/evaluation/animals.v1.json \
  --experiment examples/evaluation/cli_experiment.v1.json \
  --output /tmp/rag-experiment.json
```

`python -m rag_factory.cli.main` works without invoking the installed script.
All four commands return machine-readable JSON to stdout on success, with
configuration errors on stderr and exit status 2.

## What each command does

| Command | Behavior |
| --- | --- |
| `validate` | Parses YAML and validates stage bindings, provider declarations, strategy references, cycles and supported parameter bounds **without constructing provider instances** |
| `index` | Builds an ephemeral pipeline, indexes each named payload, and optionally saves an atomic *metadata-only* bundle |
| `retrieve` | Builds a fresh pipeline, **replays** the supplied index payloads in process, then returns ranked IDs and optional text |
| `evaluate` | Replays payloads, runs the P1 experiment for the named strategy functions, and atomically saves a reproducible JSON report |

**Important:** In-memory providers lose their contents after every CLI invocation.
An artifact bundle is **not** a persistent index. It holds index manifests and
hierarchy mappings but **not** document text, keyword postings, embeddings, or
graph data. `retrieve` and `evaluate` therefore require `--payloads` and
re-index on every invocation. This is an honest, deterministic local-dev
workflow, not a production persistence or restore implementation.

## Configuration and payload shapes

`--config` uses the unified YAML schema with `services` and `strategies`.
Each strategy has `kind`, stage-separated `indexing` and `retrieval`
interface-to-service bindings, and optional `parameters`. A small example:

```yaml
services:
  store: {interface: keyword_store, implementation: memory}
  tokens: {interface: tokenizer, implementation: regex}
strategies:
  lexical:
    kind: keyword
    indexing: {keyword_store: store}
    retrieval: {keyword_store: store, tokenizer: tokens}
```

`--payloads` is a versioned JSON mapping of indexed strategy names to the
same payloads accepted by `UnifiedPipeline.index(name, payload)`:

```json
{
  "format_version": 1,
  "indexes": {
    "lexical": {
      "documents": {
        "cat-document": "Cats purr and are pets",
        "dog-document": "Dogs bark and are pets"
      }
    }
  }
}
```

All seven index payload kinds can be represented; `late_chunking` token-span
pairs use JSON arrays and the CLI converts them to Python tuples. However,
the built-in offline registry intentionally supports only memory keyword,
vector, document, graph and regex tokenizer providers; embedding, LLM,
reranker and contextual-token encoder implementations must be supplied by
custom Python integration. The shipped CLI example is keyword-only.

YAML diagnostics identify the source file, unknown top-level/service/strategy
fields, unknown stage interface bindings and unsatisfied provider capabilities.
The CLI validates without constructing providers; it does not validate remote
connectivity or authorize artifact access.

## Reproducibility

`evaluate` loads the P1 versioned dataset and experiment configuration,
records dataset/configuration fingerprints and per-query metrics, and writes
identical JSON for repeatable offline runs when latency capture is disabled.
Add `--capture-latency` to record variable timing measurements.
Retrieval-quality scores remain advisory; CI does not fail due to low scores.
See [EVALUATION_EXPERIMENTS.md](EVALUATION_EXPERIMENTS.md).

## Structured diagnostics (opt-in)

Add `--trace` to `index`, `retrieve` or `evaluate`. Each pipeline
operation emits one JSON event on **stderr** containing only:

- `stage` (`indexing` or `retrieval`)
- `strategy` (configured name)
- `duration_ms` (monotonic elapsed time)
- `status` (`success` or `error`)
- `error_type` (exception class name, only on failure)

There is **no query, document text, response, or raw exception message** in
the trace events. CLI success JSON remains on stdout so it can be parsed
separately. Nested/composite retrieval calls generate their own events.
Timing varies by run and is not part of deterministic relevance reports.

Programmatic use accepts `build_unified(config, registry, observer=callback)`.
Observers receive immutable `OperationEvent` instances. Exceptions raised
inside an observer are ignored so tracing cannot change retrieval outcomes.

## Explicit opt-in live adapter tests

Live integration testing is **not** part of the Python 3.12 offline core gate.
Adapters can be checked separately with:

```bash
RAG_FACTORY_LIVE_INTERFACE=keyword_store \
RAG_FACTORY_LIVE_FACTORY=my_test_provider:create_keyword_store \
python -m pytest tests/integration/test_live_provider_contracts.py -m external -v
```

`RAG_FACTORY_LIVE_FACTORY` uses an importable Python `module:callable`
defined by the integrator. Without **both** environment variables, the suite
skips. The core tests verify this skip behavior and opt-in execution against a
mock, not a real service. Only run it against disposable test data:
**conformance deliberately writes records**. This suite is not run by the
core GitHub Actions workflow; no secrets or live endpoints are provisioned
here.

## Provider conformance for integrations

New provider implementations can be checked without creating a full RAG
pipeline:

```python
from rag_factory.testing.provider_contracts import check_provider_contract
from rag_factory.services.keyword.memory import MemoryKeywordStore

check_provider_contract("keyword_store", MemoryKeywordStore)
```

The factory argument constructs an isolated instance. The conformance harness
checks expected operations and behavior and calls `close()` if available.
It does **not** prove remote endpoint reachability, performance, data
persistence, access control or production safety.
