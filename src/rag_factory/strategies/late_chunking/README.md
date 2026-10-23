# Late chunking (offline reference baseline)

The caller supplies document tokens and half-open token spans for chunks. The indexer runs **one full-document contextual token encoding** before pooling the resulting token vectors separately over each span. This is distinct from embedding isolated chunks. The retrieval side accepts a compatible query embedding interface and validates model identity and dimensions using an index manifest.

The contextual encoder and query embedder must represent the **same compatible vector space**; the model identifier alone cannot prove semantic equivalence. This API assumes the entire token sequence fits the encoder context window. It does not implement tokenizer offset alignment, token-window stitching, overlap policies, document chunk segmentation, or a production transformer adapter. The offline tests use an intentionally simplified context-sensitive encoder solely to verify the ordering of operations.
