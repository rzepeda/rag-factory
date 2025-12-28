# **ARCHITECTURAL PRINCIPLES - PROCESS-CENTRIC**

*Quick reference for structure, rules, and decisions in process-centric projects*

---

## **1. Project Structure**

### **Fixed Scaffold (Never Modify)**
```
/
├── .venv/
├── .env
├── .gitignore
├── pyproject.toml
├── agent_tools/        # IMMUTABLE
├── resources/
├── docs/
└── workspace/
```

### **Core Structure (Architect Designs)**
```
src/{package}/core/
├── processors/         # Individual operations (single responsibility)
├── pipelines/          # Workflow orchestration
├── strategies/         # Algorithm choices (swappable)
├── handlers/           # Cross-cutting concerns (errors, logging)
└── interfaces/         # Contracts (Processor, Strategy, Pipeline)

src/{package}/
├── cli/                # Terminal interface
├── gui/                # Visual interface (optional)
└── utils/              # Infrastructure (I/O, config)

tests/
├── unit/processors/    # Isolated processor tests
├── unit/strategies/    # Algorithm tests
├── unit/pipelines/     # Workflow tests
├── integration/        # End-to-end workflows
└── performance/        # Benchmarks
```

---

## **2. Component Rules**

| Component | Location | Purpose | Responsibilities | Boundaries |
|-----------|----------|---------|------------------|------------|
| **Processors** | `core/processors/` | Operations | Single transformation step | Stateless, focused |
| **Pipelines** | `core/pipelines/` | Orchestration | Chain processors, manage flow | Accepts processors as args |
| **Strategies** | `core/strategies/` | Algorithms | Swappable implementations | Common interface |
| **Handlers** | `core/handlers/` | Cross-cutting | Errors, logging, retries | Orthogonal to processing |
| **Interfaces** | `core/interfaces/` | Contracts | Define component APIs | Abstract base classes |
| **CLI/GUI** | `cli/`, `gui/` | User interface | Call pipelines, format I/O | Delegates to pipelines |
| **Utils** | `utils/` | Infrastructure | File I/O, config | Generic utilities only |

**Composition flow:** `CLI/GUI → Pipelines → Processors/Strategies`  
**Core rule:** Components are composable and testable in isolation

---

## **3. Decision Framework**

| Question | Answer |
|----------|--------|
| Single operation/transformation? | → `processors/` |
| Sequence of operations? | → `pipelines/` |
| Alternative algorithms for same task? | → `strategies/` |
| Error handling/logging/retries? | → `handlers/` |
| Component contract/interface? | → `interfaces/` |
| User input/output? | → `cli/` or `gui/` |
| File I/O/configuration? | → `utils/` |

---

## **4. Key Distinctions**

**Processor vs Pipeline vs Strategy:**
- **Processor**: Single step (validate, transform, filter) → `processors/validator.py`
- **Pipeline**: Workflow (step1 → step2 → step3) → `pipelines/data_pipeline.py`
- **Strategy**: Algorithm choice (QuickSort vs MergeSort) → `strategies/sorting/quick_sort.py`

**Files:**
```
processors/validator.py             # What it does
pipelines/standard_pipeline.py      # Workflow name
strategies/sorting/quick_sort.py    # Category/algorithm
handlers/error_handler.py           # What it handles
interfaces/processor.py             # Contract name
```

**Testing:**
- `unit/processors/` - Isolated, no dependencies
- `unit/strategies/` - Algorithm correctness
- `unit/pipelines/` - Mock processors
- `integration/` - Real workflows
- `performance/` - Benchmarks

---

## **5. Core Principles**

✓ Processors are small and focused  
✓ Pipelines compose processors  
✓ Strategies share common interfaces  
✓ Handlers are optional and orthogonal  
✓ Components are stateless when possible  
✓ All components implement interfaces
