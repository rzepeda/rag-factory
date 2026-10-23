# Agentic RAG retrieval routing (offline baseline)

The initial implementation uses an injected LLM interface to select an **allowlisted retrieval tool by exact name**. It calls each selected tool at most once, combines document identifiers in first-seen order, and bounds both tool invocations and returned results. Tool arguments are fixed by the application to the original query and a positive limit. Unknown model outputs are rejected.

This is intentionally a small routing agent, not an unrestricted agent runtime: no arbitrary actions, dynamic tool arguments, multi-step planning, generated code, query rewriting, answer generation, or sandbox execution. Offline tests use `MockLLM` and fake retrieval callables. Real providers remain deferred.
