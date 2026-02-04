# Runtime Module

The runtime module provides the main workflow execution interface.

## Main Functions

### run_workflow

```{py:function} run_workflow(config_path: str | Path, **kwargs) -> dict
```

Execute a workflow from a configuration file.

**Parameters:**
- `config_path` (str | Path) - Path to YAML or JSON configuration file
- `**kwargs` - Additional execution options:
  - `mlflow_run_id` (str, optional) - MLFlow run ID for tracking
  - `timeout` (int, optional) - Maximum execution time in seconds
  - `debug` (bool, optional) - Enable debug logging

**Returns:**
- dict - Dictionary containing workflow results:
  - `final_output` - Final workflow output
  - `node_results` - Results from each node
  - `metrics` - Execution metrics (cost, duration)

**Raises:**
- `ConfigLoadError` - If configuration file cannot be parsed
- `ConfigValidationError` - If configuration fails validation
- `WorkflowExecutionError` - If workflow execution fails

**Examples:**

```python
from configurable_agents.runtime import run_workflow

# Execute a simple workflow
result = run_workflow("examples/simple_workflow.yaml")
print(result['final_output'])

# Execute with MLFlow tracking
result = run_workflow(
    "config.yaml",
    mlflow_run_id="existing-run"
)

# Execute with timeout
result = run_workflow(
    "config.yaml",
    timeout=300
)
```

### run_workflow_from_config

```{py:function} run_workflow_from_config(config: WorkflowConfig, **kwargs) -> dict
```

Execute a workflow from a WorkflowConfig object.

**Parameters:**
- `config` (WorkflowConfig) - Workflow configuration object
- `**kwargs` - Additional execution options

**Returns:**
- dict - Dictionary containing workflow results

**Examples:**

```python
from configurable_agents.config import parse_config_file
from configurable_agents.runtime import run_workflow_from_config

config = parse_config_file("examples/simple_workflow.yaml")
result = run_workflow_from_config(config)
```

### validate_workflow

```{py:function} validate_workflow(config_path: str | Path) -> bool
```

Validate a workflow configuration without execution.

**Parameters:**
- `config_path` (str | Path) - Path to configuration file

**Returns:**
- bool - True if configuration is valid, False otherwise

**Raises:**
- `ConfigLoadError` - If configuration file cannot be parsed
- `ConfigValidationError` - If configuration fails validation

**Examples:**

```python
from configurable_agents.runtime import validate_workflow

is_valid = validate_workflow("examples/simple_workflow.yaml")
if is_valid:
    print("Configuration is valid!")
```

## Exceptions

### ConfigLoadError

```{py:exception} ConfigLoadError
```

Raised when configuration file cannot be parsed.

### ConfigValidationError

```{py:exception} ConfigValidationError
```

Raised when configuration fails validation.

### WorkflowExecutionError

```{py:exception} WorkflowExecutionError
```

Raised when workflow execution fails.

### NodeExecutionError

```{py:exception} NodeExecutionError
```

Raised when a node execution fails.

## Full API

```{py:module} configurable_agents.runtime
```

## See Also

- [Configuration Module](config.md) - Configuration parsing and validation
- [Core Module](core.md) - Graph building and execution
- [Observability Module](observability.md) - MLFlow tracking
