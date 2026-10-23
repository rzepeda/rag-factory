# Contextual lexical retrieval (mock-backed baseline)

This strategy asks an injected `LLMService` for a short context passage for each chunk, indexes `context + original chunk` through a `KeywordStoreService`, and stores the **unaltered original** through a `DocumentStoreService`. A retriever validates the `IndexManifest`, searches with an injected tokenizer and returns `(chunk_id, original_text)` pairs.

It requires no real model or database: tests exercise `MockLLM`, `MockKeywordStore`, `MockDocumentStore` and `MockTokenizer`. It does not automatically segment documents, persist a manifest, support complex schema mappings, or guarantee an LLM produces accurate context; the context is untrusted generated text. The first implementation is keyword-based, not semantic/contextual embeddings.
