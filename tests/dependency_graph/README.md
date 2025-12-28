# Dependency Graph
JSON maps linking source files to tests for the Agent

## Purpose
The agent uses these mappings to determine which tests to run when source files change.

## Structure
```
dependency_graph/
└── {package_name}/
    ├── core/
    │   └── entities/
    │       └── customer.json    # Maps customer.py -> its tests
    └── cli/
        └── commands.json        # Maps CLI commands -> their tests
```

## Example File Content
```json
{
  "source_file": "src/{package}/core/entities/customer.py",
  "tests": [
    "tests/unit/entities/test_customer.py",
    "tests/integration/test_customer_workflows.py"
  ],
  "dependencies": [
    "src/{package}/core/models/customer_model.py"
  ]
}
```
