# Hierarchical keyword retrieval

This mock-backed baseline indexes child passages through the provider-neutral keyword store and retains original parent documents in a document store. A separate retriever searches the child passages, maps child hits to their parents, and returns each parent once in ranked first-occurrence order.

Inputs are explicit parent texts, child texts, and child-to-parent identifiers; automatic chunking, hierarchy persistence, graph traversal, and recursive multi-level expansion are not implemented. The hierarchy mapping is held in memory and must accompany the index manifest to use the retriever. Tests run entirely offline with deterministic mocks.

See `tests/unit/core/test_hierarchical_retrieval.py` for examples.
