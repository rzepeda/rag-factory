# Extending providers and strategies (P2)

This framework is intentionally provider-neutral. The initial implementation
targets offline tests, not external database or LLM provisioning. The
`UnifiedPipeline` API remains opt-in alongside earlier runtimes.

## Register an independent provider instance

Implement the operations in `rag_factory.core.interfaces.services` and
register a descriptor and a fresh-instance constructor with
`ServiceRegistry`. Example for a keyword store:

```python
from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
from rag_factory.services.keyword.memory import MemoryKeywordStore
from rag_factory.testing.provider_contracts import check_provider_contract

check_provider_contract("keyword_store", MemoryKeywordStore)

registry = ServiceRegistry()
registry.register(
    ProviderDescriptor(
        "keyword_store", "my-offline-keywords",
        frozenset({"upsert", "search"})
    ),
    MemoryKeywordStore,
)

descriptor, instance = registry.resolve(
    ServiceConfig("keyword_store", "my-offline-keywords")
)
assert "search" in descriptor.capabilities
```

This is a **registry declaration**, not authorization, schema inspection, or
endpoint connectivity verification. Constructors receive
`ServiceConfig.parameters` as keyword arguments. The unified factory resolves
each *named* service once and owns its lifecycle: it closes providers in
reverse creation order, including after failed construction. If the same
underlying external resource must be shared between separate indexing and
retrieval processes, configure its identity explicitly.

The `default_registry()` includes memory stores for keyword/vector/document/
graph interfaces and a regex tokenizer. Real providers should be opt-in and
tested separately from the Python 3.12 offline CI. New adapters can run the
reusable conformance suite:

```python
from rag_factory.testing.provider_contracts import check_provider_contract

check_provider_contract("keyword_store", YourStoreConstructor)
```

That harness checks a fresh instance and closes it when possible. It checks
the operations' observable behavior but cannot prove physical durability,
network reliability, authorization, or performance.

## Bind a provider to one or more strategies

For an existing strategy, no changes to the strategy implementation are
needed. Supply a matching `ServiceConfig` and the appropriate stage
bindings, using `StrategySpec`:

```python
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified

config = UnifiedConfiguration(
    services={
        "writer": ServiceConfig("keyword_store", "my-offline-keywords"),
        "reader": ServiceConfig("keyword_store", "my-offline-keywords"),
        "tokens": ServiceConfig("tokenizer", "regex"),
    },
    strategies={
        "lexical": StrategySpec(
            kind="keyword",
            indexing={"keyword_store": "writer"},
            retrieval={"keyword_store": "reader", "tokenizer": "tokens"},
        ),
    },
)
```

For this example, register the regex tokenizer as well or start from
`default_registry()` and add the custom provider. **Two named service
instances are independent** unless the provider constructor connects them to
the same persistent index. The memory providers are not shared across names or
processes. For a single-process memory example, bind the *same* store name to
both stages.

`validate_unified_configuration(config, registry)` checks interface
capabilities and strategy dependencies **without constructing any provider**.
`load_validated_unified_config(path, registry)` also checks YAML schema
fields and reports the source path.

## Add a genuinely new strategy kind

There is no automatic strategy plug-in registry yet. Adding a new kind is a
deliberate code change to the unified implementation. Review these
integration points together:

1. Implement a strategy's indexing and/or retrieval algorithms behind service
   interfaces; retain independent, deterministic offline baselines.
2. Add its stage-specific `ServiceRequirement` declarations in
   `factory/unified.py:REQUIRES`. Decide whether it belongs to `INDEXED`,
   `REFERENCED`, or a composed-source family.
3. Extend `UnifiedPipeline.index()` and/or `retrieve()` to invoke it, and
   `core/index_payloads.py` to validate any new indexing payload format.
4. Define manifest capabilities and compatibility rules in
   `UnifiedPipeline.attach_artifacts()`, including any needed relationship
   metadata. Never confuse metadata-only bundles with physical indexes.
5. Validate strategy-specific parameters and references before provider
   construction; preserve typed `RetrievalHit` output and positive integer
   retrieval limits.
6. Add offline acceptance tests for indexing, retrieval, malformed config,
   provider failure cleanup, partial writes, artifact handoff, and P1 metrics
   reproducibility.

An algorithm improvement to an existing kind belongs to **P3**, after
retaining a baseline experiment report. A new provider implementation should
be tested by both conformance and a manually opted-in integration suite before
production use.

## Test boundaries

Core Python 3.12 CI exercises deterministic in-memory and mock services.
Live-provider tests must be opt-in, credential-managed, and marked
`@pytest.mark.integration` or `@pytest.mark.external`. Do not put real
provider network requests in `tests/unit/core`. Benchmark results and
retrieval quality are informational; they do not silently become mandatory CI
thresholds.
