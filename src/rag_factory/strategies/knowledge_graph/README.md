# Knowledge graph retrieval (offline baseline)

This implementation indexes **explicit directed relationships between document IDs** with the graph service and stores originals in a document service. Retrieval performs breadth-first traversal from a supplied document ID for at most `max_hops` edges and returns up to `limit` originals, preserving deterministic neighbor ordering with the existing mock.

It does not extract entities using an LLM, run natural-language-to-graph search, use typed entities, perform graph ranking or provision database schemas. Callers must resolve a natural-language query to a starting graph node separately. The graph edges and document storage must be shared by indexing and retrieval; the index manifest is checked for basic compatibility.
