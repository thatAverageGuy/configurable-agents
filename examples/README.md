# Workflow Examples

Example workflow configurations for Configurable Agents.

## Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up API key
export GOOGLE_API_KEY="your-key-here"  # Unix/Linux/macOS
# or
set GOOGLE_API_KEY=your-key-here  # Windows
```

## Quick Start

### Using the Runtime Executor (Python)

```python
from configurable_agents.runtime import run_workflow

# Execute workflow from file
result = run_workflow("simple_workflow.yaml", {"name": "Alice"})

print(result["greeting"])
# Output: "Hello Alice! How are you doing today?"
```

### Validating Workflows

```python
from configurable_agents.runtime import validate_workflow

# Validate without executing
try:
    validate_workflow("simple_workflow.yaml")
    print("✅ Config is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")
```

### Using Pre-loaded Configs

```python
from configurable_agents.config import parse_config_file, WorkflowConfig
from configurable_agents.runtime import run_workflow_from_config

# Load and parse config
config_dict = parse_config_file("simple_workflow.yaml")
config = WorkflowConfig(**config_dict)

# Execute from config object
result = run_workflow_from_config(config, {"name": "Bob"})
```

## Available Examples

### simple_workflow.yaml

A minimal greeting workflow demonstrating:
- Basic state management
- Single node execution
- Prompt template with variable substitution
- Structured output

**Usage:**
```python
result = run_workflow("simple_workflow.yaml", {"name": "Alice"})
```

## Error Handling

The executor provides comprehensive error handling:

```python
from configurable_agents.runtime import (
    run_workflow,
    ConfigLoadError,       # Config file not found or invalid syntax
    ConfigValidationError, # Config validation failed
    StateInitializationError, # Invalid input values
    GraphBuildError,       # Graph construction failed
    WorkflowExecutionError, # Node execution failed
)

try:
    result = run_workflow("workflow.yaml", {"name": "Alice"})
except ConfigLoadError as e:
    print(f"Failed to load config: {e}")
except ConfigValidationError as e:
    print(f"Invalid config: {e}")
except StateInitializationError as e:
    print(f"Invalid inputs: {e}")
except WorkflowExecutionError as e:
    print(f"Execution failed: {e}")
```

## Verbose Logging

Enable detailed logging for debugging:

```python
result = run_workflow("workflow.yaml", {"name": "Alice"}, verbose=True)
```

## Notes

- All examples require Google Gemini API key (v0.1 limitation)
- Multi-LLM support coming in v0.2+
- Conditional routing coming in v0.2+
- See [docs/SPEC.md](../docs/SPEC.md) for complete config schema reference

## Next Steps

1. Explore the [full spec](../docs/SPEC.md)
2. Read the [architecture docs](../docs/ARCHITECTURE.md)
3. Check the [roadmap](../docs/PROJECT_VISION.md)

---

**Note**: These examples are minimal demonstrations. Production workflows will have:
- Multiple nodes in sequence
- Tool integration (web search, APIs)
- Complex state management
- Error handling and retries
