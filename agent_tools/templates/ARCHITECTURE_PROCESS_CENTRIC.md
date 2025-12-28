# **ARCHITECTURE - PROCESS-CENTRIC**

**Project:** [PROJECT_NAME]  
**Updated:** [YYYY-MM-DD]  
**Architect:** [Name]  
**Status:** [Draft/Active]

---

## **C1: System Context**

**Purpose:**  
[One sentence: What does this library/tool process and for whom?]

**Use Cases:**
- **[Use Case 1]:** [What operation/transformation]
- **[Use Case 2]:** [What operation/transformation]
- **[Use Case 3]:** [What operation/transformation]

**I/O:**
- **Input:** [Data format/type]
- **Output:** [Data format/type]

**External Dependencies:**
- **[Library/Service]:** [Purpose]
- **[Library/Service]:** [Purpose]

---

## **C2: Container Architecture**

```mermaid
C4Container
    title [PROJECT_NAME] - Container View
    
    %% Example structure - customize for your project:
    %% Person(dev, "Developer", "Uses library")
    %% Container(pipeline, "Pipeline", "Python", "Orchestrates processing")
    %% Container(processors, "Processors", "Python", "Individual operations")
    %% Rel(dev, pipeline, "Calls")
    %% Rel(pipeline, processors, "Uses")
```

**Components:**

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| [Name]    | [Tech]     | [What it processes] |
| [Name]    | [Tech]     | [What it processes] |

---

## **Technology Stack**

**Core:**
- Language: [Python 3.x]
- Processing: [Key libraries for operations]

**Interfaces:**
- CLI: [Typer/Click]
- Library API: [Public interface]
- GUI: [Optional]

**Configuration:**
- Settings: [How processing is configured]
- Extensibility: [Plugin system/strategies]

---

## **Processing Model**

**Core Operations:**

| Operation | Input | Output | Purpose |
|-----------|-------|--------|---------|
| [Op1]     | [Type] | [Type] | [What it does] |
| [Op2]     | [Type] | [Type] | [What it does] |

**Workflows:**
```
[Workflow 1]: Input → [Step1] → [Step2] → [Step3] → Output
[Workflow 2]: Input → [StepA] → [StepB] → Output
```

---

## **Project Structure**

**Core Organization:**
```
src/{package}/core/
├── processors/     [Processor1, Processor2, ...]
├── pipelines/      [Pipeline1, Pipeline2, ...]
├── strategies/     [Strategy1, Strategy2, ...]
├── handlers/       [ErrorHandler, LogHandler, ...]
└── interfaces/     [Processor, Strategy, Pipeline]
```

**Test Organization:**
```
tests/
├── unit/processors/
├── unit/strategies/
├── unit/pipelines/
├── integration/[workflow_name]/
└── performance/
```

---

## **Key Strategies**

### **[Strategy Type 1]:** [e.g., Sorting]
- **[Option A]:** [When to use]
- **[Option B]:** [When to use]
- **Selection:** [Criteria]

### **[Strategy Type 2]:** [e.g., Compression]
- **[Option A]:** [When to use]
- **[Option B]:** [When to use]
- **Selection:** [Criteria]

---

## **Critical Decisions (ADRs)**

### **ADR-001: [Title]**
- **Decision:** [What was decided]
- **Rationale:** [Why]
- **Impact:** [Consequences]

### **ADR-002: [Title]**
- **Decision:** [What was decided]
- **Rationale:** [Why]
- **Impact:** [Consequences]

---

## **Constraints**

**Must:**
- [Critical requirement 1]
- [Critical requirement 2]

**Must Not:**
- [Critical restriction 1]
- [Critical restriction 2]

**Performance:**
- [Target: processing speed/memory]
- [Target: scalability requirements]

---

## **Extension Points**

**Custom Processors:** [How users extend]  
**Custom Strategies:** [How users add algorithms]  
**Custom Pipelines:** [How users compose workflows]
