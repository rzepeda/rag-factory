# Implemented adapters and strategy dependencies

Legend: **✓** direct requirement, **◇** indirect requirement through a configured retrieval source, **×** not required. **I** indexing, **R** retrieval.

GitHub Markdown cannot reliably rotate table headers, so the compact strategy codes keep each strategy column narrow. The full strategy names follow the matrix.

| Service | Implemented adapters | Stage | K | S | C | H | G | L | RR | MQ | QE | SR | A | HY | SC | QR | HD | GV |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Keyword store | MemoryKeywordStore | I | ✓ | × | ✓ | ✓ | × | × | × | × | × | × | × | × | × | × | × | × |
| Keyword store | MemoryKeywordStore | R | ✓ | × | ✓ | ✓ | × | × | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | × | ◇ | ◇ | ◇ |
| Tokenizer | RegexTokenizer | I | × | × | × | × | × | × | × | × | × | × | × | × | × | × | × | × |
| Tokenizer | RegexTokenizer | R | ✓ | × | ✓ | ✓ | × | × | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | × | ◇ | ◇ | ◇ |
| Embedding | None registered | I | × | ✓ | × | × | × | × | × | × | × | × | × | × | ✓ | × | × | × |
| Embedding | None registered | R | × | ✓ | × | × | × | ✓ | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | ✓ | ◇ | ◇ | ◇ |
| Vector store | MemoryVectorStore | I | × | ✓ | × | × | × | ✓ | × | × | × | × | × | × | ✓ | × | × | × |
| Vector store | MemoryVectorStore | R | × | ✓ | × | × | × | ✓ | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | ✓ | ◇ | ◇ | ◇ |
| Document store | MemoryDocumentStore | I | × | × | ✓ | ✓ | ✓ | × | × | × | × | × | × | × | × | × | × | × |
| Document store | MemoryDocumentStore | R | × | × | ✓ | ✓ | ✓ | × | ✓ | ◇ | ◇ | ✓ | ◇ | ◇ | × | ◇ | ◇ | ◇ |
| Graph store | MemoryGraphStore | I | × | × | × | × | ✓ | × | × | × | × | × | × | × | × | × | × | × |
| Graph store | MemoryGraphStore | R | × | × | × | × | ✓ | × | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | × | ◇ | ◇ | ◇ |
| LLM | None registered | I | × | × | ✓ | × | × | × | × | × | × | × | × | × | × | × | × | × |
| LLM | None registered | R | × | × | × | × | × | × | ◇ | ✓ | ✓ | ✓ | ✓ | ◇ | × | ✓ | ✓ | ◇ |
| Reranker | None registered | I | × | × | × | × | × | × | × | × | × | × | × | × | × | × | × | × |
| Reranker | None registered | R | × | × | × | × | × | × | ✓ | ◇ | ◇ | ◇ | ◇ | ◇ | × | ◇ | ◇ | ◇ |
| Contextual token encoder | None registered | I | × | × | × | × | × | ✓ | × | × | × | × | × | × | × | × | × | × |
| Contextual token encoder | None registered | R | × | × | × | × | × | × | ◇ | ◇ | ◇ | ◇ | ◇ | ◇ | × | ◇ | ◇ | ◇ |

## Strategy codes

| Code | Strategy | Code | Strategy |
|---|---|---|---|
| K | Keyword | S | Semantic |
| C | Contextual | H | Hierarchical |
| G | Knowledge graph | L | Late chunking |
| RR | Reranking | MQ | Multi-query |
| QE | Query expansion | SR | Self-reflective |
| A | Agentic | HY | Hybrid |
| SC | Semantic chunking | QR | Query refinement |
| HD | HyDE | GV | Graph-vector hybrid |

## Indirect dependencies

The ◇ entries are conditional: a source-based retrieval strategy inherits the retrieval dependencies of its configured sources. Source indexes also require their own indexing services, even if the composite strategy itself has no indexing stage. For example, Hybrid with Keyword and Semantic sources needs both sets of indexing and retrieval services.

The five default adapters are offline/local implementations, not external provider integrations. Test-only mocks are excluded from the implemented-adapters column.

## Related documentation

- [Unified architecture and lifecycle](UNIFIED_FACTORY.md)
- [Creating and registering adapters; extending strategies](EXTENDING_UNIFIED_FRAMEWORK.md)
- [Service configuration and offline CLI](CLI_OFFLINE.md)
- [Evaluation experiments](EVALUATION_EXPERIMENTS.md)

Source of truth: `src/rag_factory/factory/unified.py` and `src/rag_factory/factory/service_registry.py`.
