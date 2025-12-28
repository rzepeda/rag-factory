"""Capability definitions for indexing and retrieval strategies.

This module defines the capabilities that indexing strategies can produce
and retrieval strategies can require. Capabilities represent what kind of
searchable data or structure is created during indexing.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Set, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from rag_factory.services.dependencies import ServiceDependency


class IndexCapability(Enum):
    """Capabilities that an indexing strategy can produce.
    
    This enum defines all possible capabilities that can be produced by
    indexing strategies. These capabilities are used to:
    1. Declare what an indexing strategy produces
    2. Declare what a retrieval strategy requires
    3. Validate compatibility between indexing and retrieval strategies
    
    Example:
        >>> # Indexing strategy declares what it produces
        >>> def produces(self) -> Set[IndexCapability]:
        ...     return {IndexCapability.VECTORS, IndexCapability.DATABASE}
        
        >>> # Retrieval strategy declares what it requires
        >>> def requires(self) -> Set[IndexCapability]:
        ...     return {IndexCapability.VECTORS}
    """
    
    # Storage types - what kind of searchable data is created
    VECTORS = auto()
    """Vector embeddings stored in database for semantic search."""
    
    KEYWORDS = auto()
    """Keyword/BM25 index created for lexical search."""
    
    GRAPH = auto()
    """Knowledge graph with entities and relationships."""
    
    FULL_DOCUMENT = auto()
    """Complete documents stored as-is without chunking."""
    
    # Structure types - how documents are organized
    CHUNKS = auto()
    """Documents split into chunks for retrieval."""
    
    HIERARCHY = auto()
    """Parent-child relationships between chunks maintained."""
    
    LATE_CHUNKS = auto()
    """Late chunking (embed-then-chunk) applied for better context."""
    
    # Storage backends - where data is persisted
    IN_MEMORY = auto()
    """Data stored in memory only (typically for testing)."""
    
    FILE_BACKED = auto()
    """Data persisted to files on disk."""
    
    DATABASE = auto()
    """Data persisted to database (PostgreSQL, Neo4j, etc.)."""
    
    # Enrichment types - additional processing applied
    CONTEXTUAL = auto()
    """Chunks have contextual descriptions for better retrieval."""
    
    METADATA = auto()
    """Rich metadata extracted and indexed for filtering."""


@dataclass
class IndexingResult:
    """Result of an indexing operation.
    
    This dataclass encapsulates the output of an indexing strategy,
    including what capabilities were produced, metadata about the
    indexing process, and document/chunk counts.
    
    Attributes:
        capabilities: Set of capabilities produced by the indexing strategy
        metadata: Additional metadata from the indexing process (e.g., timing, errors)
        document_count: Number of documents that were indexed
        chunk_count: Number of chunks created during indexing
    
    Example:
        >>> result = IndexingResult(
        ...     capabilities={IndexCapability.VECTORS, IndexCapability.DATABASE},
        ...     metadata={"duration_seconds": 12.5},
        ...     document_count=100,
        ...     chunk_count=450
        ... )
        >>> result.has_capability(IndexCapability.VECTORS)
        True
        >>> result.is_compatible_with({IndexCapability.VECTORS})
        True
    """
    
    capabilities: Set[IndexCapability]
    metadata: Dict
    document_count: int
    chunk_count: int
    
    def has_capability(self, cap: IndexCapability) -> bool:
        """Check if specific capability is present.
        
        Args:
            cap: The capability to check for
        
        Returns:
            True if the capability is present, False otherwise
        
        Example:
            >>> result = IndexingResult(
            ...     capabilities={IndexCapability.VECTORS},
            ...     metadata={},
            ...     document_count=10,
            ...     chunk_count=50
            ... )
            >>> result.has_capability(IndexCapability.VECTORS)
            True
            >>> result.has_capability(IndexCapability.KEYWORDS)
            False
        """
        return cap in self.capabilities
    
    def is_compatible_with(self, requirements: Set[IndexCapability]) -> bool:
        """Check if capabilities satisfy requirements.
        
        Uses subset relationship to determine if all required capabilities
        are present in this result.
        
        Args:
            requirements: Set of capabilities that are required
        
        Returns:
            True if all requirements are satisfied, False otherwise
        
        Example:
            >>> result = IndexingResult(
            ...     capabilities={IndexCapability.VECTORS, IndexCapability.DATABASE},
            ...     metadata={},
            ...     document_count=10,
            ...     chunk_count=50
            ... )
            >>> result.is_compatible_with({IndexCapability.VECTORS})
            True
            >>> result.is_compatible_with({IndexCapability.VECTORS, IndexCapability.KEYWORDS})
            False
        """
        return requirements.issubset(self.capabilities)
    
    def __repr__(self) -> str:
        """Get readable string representation.
        
        Returns:
            String showing capabilities and document/chunk counts
        
        Example:
            >>> result = IndexingResult(
            ...     capabilities={IndexCapability.VECTORS, IndexCapability.DATABASE},
            ...     metadata={},
            ...     document_count=10,
            ...     chunk_count=50
            ... )
            >>> repr(result)
            'IndexingResult(capabilities={VECTORS, DATABASE}, docs=10, chunks=50)'
        """
        caps = sorted([c.name for c in self.capabilities])
        return f"IndexingResult(capabilities={{{', '.join(caps)}}}, docs={self.document_count}, chunks={self.chunk_count})"


@dataclass
class ValidationResult:
    """Result of compatibility validation.
    
    This dataclass encapsulates the result of validating whether an
    indexing result is compatible with a retrieval strategy's requirements.
    It includes information about missing capabilities and services.
    
    Attributes:
        is_valid: Whether the validation passed
        missing_capabilities: Set of capabilities that are required but not present
        missing_services: Set of services that are required but not available
        message: Human-readable validation message
        suggestions: List of suggestions for fixing validation issues
    
    Example:
        >>> from rag_factory.services.dependencies import ServiceDependency
        >>> result = ValidationResult(
        ...     is_valid=False,
        ...     missing_capabilities={IndexCapability.VECTORS},
        ...     missing_services={ServiceDependency.EMBEDDING},
        ...     message="Validation failed",
        ...     suggestions=["Add vector indexing", "Provide embedding service"]
        ... )
        >>> result.is_valid
        False
    """
    
    is_valid: bool
    missing_capabilities: Set[IndexCapability]
    missing_services: Set['ServiceDependency']
    message: str
    suggestions: List[str]
    
    def __repr__(self) -> str:
        """Get readable string representation.
        
        Returns:
            String showing validation status and missing items if invalid
        
        Example:
            >>> result = ValidationResult(
            ...     is_valid=True,
            ...     missing_capabilities=set(),
            ...     missing_services=set(),
            ...     message="Valid",
            ...     suggestions=[]
            ... )
            >>> repr(result)
            'ValidationResult(valid=True)'
            
            >>> from rag_factory.services.dependencies import ServiceDependency
            >>> result = ValidationResult(
            ...     is_valid=False,
            ...     missing_capabilities={IndexCapability.VECTORS},
            ...     missing_services={ServiceDependency.EMBEDDING},
            ...     message="Invalid",
            ...     suggestions=[]
            ... )
            >>> repr(result)
            'ValidationResult(valid=False, missing: capabilities: VECTORS; services: EMBEDDING)'
        """
        if self.is_valid:
            return "ValidationResult(valid=True)"
        
        issues = []
        if self.missing_capabilities:
            caps = sorted([c.name for c in self.missing_capabilities])
            issues.append(f"capabilities: {', '.join(caps)}")
        if self.missing_services:
            svcs = sorted([s.name for s in self.missing_services])
            issues.append(f"services: {', '.join(svcs)}")
        
        if issues:
            return f"ValidationResult(valid=False, missing: {'; '.join(issues)})"
        else:
            return "ValidationResult(valid=False)"
