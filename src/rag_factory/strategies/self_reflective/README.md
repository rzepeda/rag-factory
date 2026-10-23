# Self-reflective retrieval (offline baseline)

The initial implementation searches for candidate IDs and asks a provider-neutral LLM service to grade each retrieved passage YES/NO. It retries the **same query** up to a configured maximum and avoids regrading duplicate IDs. This is bounded retrieval-time evidence filtering, not a complete Self-RAG generator: there is no answer generation, fact verification, query rewriting, or reinforcement learning. The grader requires exactly YES/NO responses and fails closed on malformed responses. Use offline `MockLLM` in tests.
