# **PROJECT STRUCTURE - rag-factory**

**Project Type:** process-centric  
**Description:** RAG Factory - Modular RAG strategy system with entity-repository pattern and dynamic model generation

---

## **Overview**

This document describes the complete folder structure of this project, including the purpose and usage of each directory.

---

## **Source Code Structure**

### **src/rag_factory/core/**

The core business logic organized by architectural pattern.

#### **core/strategies/**
- **Description:** Self-contained RAG strategy implementations
- **Purpose:** Each strategy owns entities, schema, migrations, and business logic

#### **core/core/**
- **Description:** Core interfaces and base classes (strategy-independent)
- **Purpose:** Define contracts that strategies must implement

#### **core/shared/**
- **Description:** Shared infrastructure (services, repositories, utilities)
- **Purpose:** Implementations used across multiple strategies

#### **core/pipelines/**
- **Description:** Pipeline orchestration
- **Purpose:** Execute multiple strategies in sequence

#### **core/factory/**
- **Description:** Factory pattern and service registry
- **Purpose:** Create strategies, manage services, validate configurations

#### **core/cli/**
- **Description:** Command-line interface
- **Purpose:** Developer tools for testing and deployment

#### **core/server/**
- **Description:** Development HTTP server (NOT production)
- **Purpose:** Testing and POC demonstrations

### **src/rag_factory/cli/**
- **Description:** Terminal interface (adapter layer)
- **Files:** main.py (CLI entry point using Typer/Click)

### **src/rag_factory/gui/**
- **Description:** Graphical interface (adapter layer)
- **Files:** app.py (GUI entry point using PyQt/Tkinter)

### **src/rag_factory/utils/**
- **Description:** Infrastructure utilities
- **Files:**
  - `config.py`: # Configuration loading utilities

  - `logger.py`: # Logging configuration


---

## **Test Structure**

### **tests/unit/**

Unit tests organized by component type.

#### **tests/unit/strategies/**
- **Purpose:** {'test_semantic_search': {'description': 'Semantic search strategy tests', 'files': {'test_entities.py': '# Test SemanticChunk, SemanticVector entities\n', 'test_indexer.py': '# Test VectorEmbeddingIndexer\n', 'test_retriever.py': '# Test SemanticRetriever\n'}}, 'test_keyword_search': {'files': {'test_entities.py': '', 'test_indexer.py': '', 'test_retriever.py': ''}}, 'test_agentic_rag': {'files': {'test_retriever.py': '', 'test_tools.py': '# Test agent tools\n', 'test_agent.py': '# Test agent logic\n'}}}

#### **tests/unit/shared/**
- **Purpose:** {'test_services': {'files': {'test_embedding_onnx.py': '# Test ONNX embedding service\n', 'test_llm_lmstudio.py': '# Test LM Studio service\n', 'test_database_postgres.py': '# Test PostgreSQL service\n', 'test_reranking_cosine.py': '# Test cosine similarity reranking\n'}}, 'test_repositories': {'files': {'test_entity_repository.py': '# Test generic repository\n', 'test_read_only_repository.py': '# Test read-only repository\n'}}, 'test_database': {'files': {'test_model_factory.py': '# Test dynamic model generation\n', 'test_schema_loader.py': '# Test schema loading\n', 'test_connection.py': '# Test connection pooling\n'}}, 'test_validation': {'files': {'test_embedding_validator.py': '# Test dimension validation\n', 'test_service_validator.py': '# Test service validation\n'}}, 'test_utils': {'files': {'test_chunking.py': '', 'test_tokenization.py': ''}}}

#### **tests/unit/core/**
- **Purpose:** {'files': {'test_interfaces.py': '# Test interface contracts\n', 'test_capabilities.py': '# Test capability enums\n', 'test_base_strategy.py': '# Test base strategy validation\n'}}

#### **tests/unit/pipelines/**
- **Purpose:** {'files': {'test_indexing_pipeline.py': '# Test indexing pipeline\n', 'test_retrieval_pipeline.py': '# Test retrieval pipeline\n'}}

#### **tests/unit/factory/**
- **Purpose:** {'files': {'test_rag_factory.py': '# Test factory\n', 'test_service_registry.py': '# Test service registry\n', 'test_strategy_manager.py': '# Test strategy pair manager\n'}}

#### **tests/unit/cli/**
- **Purpose:** {'files': {'test_validate_command.py': '# Test validation commands\n', 'test_generate_migration.py': '# Test migration generation\n'}}

### **tests/integration/**
- **Purpose:** {'strategies': {'files': {'test_semantic_search_e2e.py': '# End-to-end semantic search\n', 'test_keyword_search_e2e.py': '# End-to-end keyword search\n', 'test_agentic_rag_e2e.py': '# End-to-end agentic RAG\n'}}, 'pipelines': {'files': {'test_pipeline_integration.py': '# Test pipeline integration\n', 'test_multi_strategy.py': '# Test multiple strategies together\n'}}, 'database': {'files': {'test_postgres_integration.py': '# Test PostgreSQL integration\n', 'test_neo4j_integration.py': '# Test Neo4j integration\n'}}}

### **tests/e2e/**
- **Purpose:** {'description': 'End-to-end workflow tests', 'files': {'test_cli_workflow.py': '# Test complete CLI workflow\n', 'test_external_database.py': '# Test read-only external DB access\n'}}

### **tests/performance/**
- **Purpose:** {'description': 'Performance benchmarks and profiling', 'files': {'__init__.py': ''}, 'folders': {'benchmarks': {'description': 'Performance benchmark tests', 'files': {'__init__.py': '', 'test_indexing_throughput.py': '# Benchmark indexing speed (chunks/sec)\n', 'test_retrieval_latency.py': '# Benchmark query latency (ms)\n', 'test_embedding_speed.py': '# Benchmark embedding generation\n', 'test_strategy_comparison.py': '# Compare strategy performance\n', 'test_memory_usage.py': '# Benchmark memory consumption\n'}}, 'profiling': {'description': 'Code profiling tools', 'files': {'__init__.py': '', 'memory_profiling.py': '# Memory usage profiling with memory_profiler\n', 'cpu_profiling.py': '# CPU usage profiling with cProfile\n', 'query_profiling.py': '# Profile query execution paths\n'}}}}

### **tests/dependency_graph/**
- **Purpose:** {'description': 'Impact analysis - JSON maps linking source files to tests (for Agent)', 'files': {'README.md': '# Dependency Graph\nJSON maps linking source files to tests for intelligent test selection.\n\n## Purpose\nThe agent uses these mappings to determine which tests to run when source files change.\n\n## Structure\n```\ndependency_graph/\n└── rag_factory/\n    ├── strategies/\n    │   └── semantic_search/\n    │       ├── indexer.json\n    │       └── retriever.json\n    ├── shared/\n    │   └── services/\n    │       └── embedding/\n    │           └── onnx_local.json\n    └── core/\n        └── interfaces/\n            └── indexing.json\n```\n\n## Example File Content\n```json\n{\n  "source_file": "src/rag_factory/strategies/semantic_search/indexer.py",\n  "tests": [\n    "tests/unit/strategies/test_semantic_search/test_indexer.py",\n    "tests/integration/strategies/test_semantic_search_e2e.py"\n  ],\n  "dependencies": [\n    "src/rag_factory/strategies/semantic_search/entities/chunk.py",\n    "src/rag_factory/strategies/semantic_search/entities/vector.py",\n    "src/rag_factory/shared/services/embedding/onnx_local.py"\n  ]\n}\n```\n'}, 'folders': {'rag_factory': {'description': 'Dependency mappings organized by package structure', 'folders': {'strategies': {'description': 'Strategy source-to-test mappings', 'files': {}}, 'shared': {'description': 'Shared infrastructure mappings', 'files': {}}, 'core': {'description': 'Core interface mappings', 'files': {}}, 'pipelines': {'description': 'Pipeline mappings', 'files': {}}, 'factory': {'description': 'Factory mappings', 'files': {}}}}}}

### **tests/mocks/**
- **Purpose:** Shared mock objects for tests
- **Usage:** Reusable mocks across different test suites

### **tests/dependency_graph/**
- **Purpose:** Impact analysis - JSON maps linking source files to tests
- **Critical for Agent:** Agent uses these mappings to determine which tests to run when source files change
- **Structure:**
  ```
  dependency_graph/
  └── {package_name}/
      ├── core/
      └── cli/
  ```

### **tests/cli/**
- **Purpose:** CLI interface tests

### **tests/gui/**
- **Purpose:** GUI interface tests

---

## **Agent Development Tools**

### **agent_tools/**
- **Description:** Agent development tooling (IMMUTABLE)
- **Status:** IMMUTABLE - Do not modify
- **Files:**
  - `definitions.py`: Tool schemas for the Agent
  - `handlers.py`: Python functions the Agent calls
  - `runner.py`: Script to launch the Agent loop
- **Prompts:**
  - `prompts/system_architect.md`: System prompt for Architecture tasks
- **Templates:**
  - `templates/ARCHITECTURE_PROCESS_CENTRIC.md`: Architecture template for agent to fill

### **resources/**
- **Description:** Agent context and templates
- **Templates:**
  - `templates/test_case.j2`: Jinja2 template for generating tests

### **workspace/**
- **Description:** Agent sandbox (ignored by git)
- **Usage:** Temporary sandbox for agent experimentation
- **Status:** Ignored by git

---

## **Documentation Structure**

### **docs/epics/**
- **Description:** High-level business requirements

### **docs/stories/**
- **Description:** Specific, implementable tasks

### **docs/architecture/**
- **Description:** System design and decisions
  - `decisions/`: Subfolder
  - `diagrams/`: Subfolder

### **docs/standards/**
- **Description:** Coding style and technical restrictions

### **docs/reference/**
- **Description:** API documentation and guides

---

## **Root Files**

- **`.env`**: Environment variables (ignored by git)
- **`.env.example`**: Example environment configuration
- **`.gitignore`**: Git ignore rules
- **`requirements.txt`**: Python dependencies
- **`pyproject.toml`**: Project configuration and metadata

---

## **Key Principles**

### **Process-Centric Architecture**
- **Processors** are small, focused operations
- **Pipelines** orchestrate workflows
- **Strategies** provide algorithm choices
- **Handlers** manage cross-cutting concerns
- **Interfaces** define contracts
- Components are composable and stateless

---

## **For More Information**

- **Architecture Details:** See `docs/architecture/ARCHITECTURE_*.md`
- **Architectural Principles:** See `docs/architecture/ARCHITECTURAL_PRINCIPLES_*.md`
- **Coding Standards:** See `docs/standards/style_and_restrictions.md`
