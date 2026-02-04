# Echo Workflow

**File**: `echo.yaml`
**Complexity**: ⭐ Minimal (simplest possible example)

## What It Does

The absolute simplest workflow possible - takes a message and echoes it back. Perfect for:
- Testing your installation
- Understanding the basic structure
- First-time users learning the system

## Structure

- **1 input field**: `message` (required)
- **1 output field**: `result`
- **1 node**: Simply repeats the input message
- **0 tools**: No external tools needed

## Usage

### CLI

```bash
configurable-agents run echo.yaml --input message="Hello, World!"
```

### Python

```python
from configurable_agents.runtime import run_workflow

result = run_workflow("examples/echo.yaml", {"message": "Hello, World!"})
print(result["result"])
```

## Expected Output

```
Result:
  message: Hello, World!
  result: Hello, World!
```

## What You'll Learn

- Basic YAML config structure
- Required fields: `schema_version`, `flow`, `state`, `nodes`, `edges`
- State field definitions with `type`, `required`, `default`
- Node structure with `prompt`, `outputs`, `output_schema`
- Linear flow with START → node → END

## Next Steps

Once this works, try:
1. `simple_workflow.yaml` - Slightly more complex with personalization
2. `article_writer.yaml` - Multi-node workflow with tools
