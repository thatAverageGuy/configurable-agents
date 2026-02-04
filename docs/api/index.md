# API Reference

Welcome to the Configurable Agents API documentation. This reference provides detailed documentation for all public modules, classes, and functions.

## Quick Start

### Running a Workflow

```python
from configurable_agents.runtime import run_workflow

result = run_workflow("path/to/config.yaml")
print(result["final_output"])
```

### Loading Configuration

```python
from configurable_agents.config import parse_config_file

config = parse_config_file("path/to/config.yaml")
print(config.name)
```

### Validating Configuration

```python
from configurable_agents.runtime import validate_workflow

is_valid = validate_workflow("path/to/config.yaml")
if is_valid:
    print("Configuration is valid!")
```

## Core Modules

### Runtime
- [`run_workflow()`](runtime.md#run_workflow) - Execute workflow from file
- [`run_workflow_from_config()`](runtime.md#run_workflow_from_config) - Execute from config object
- [`validate_workflow()`](runtime.md#validate_workflow) - Validate without execution
- [Full Runtime API](runtime.md) - Complete runtime module documentation

### Configuration
- [`WorkflowConfig`](config.md#configurable_agents.config.schema.WorkflowConfig) - Main config model
- [`StateSchema`](config.md#configurable_agents.config.schema.StateSchema) - State structure
- [`NodeConfig`](config.md#configurable_agents.config.schema.NodeConfig) - Node configuration
- [Full Configuration API](config.md) - Complete configuration module documentation

### Core
- [`build_graph()`](core.md#build_graph) - Construct execution graph
- [`build_state_model()`](core.md#build_state_model) - Generate state models
- [`build_output_model()`](core.md#build_output_model) - Generate output models
- [Full Core API](core.md) - Complete core module documentation

## Integration Modules

### LLM Providers
- [Google Provider](llm.md) - Google Gemini implementation
- [LiteLLM Provider](llm.md) - Multi-provider support
- [Provider Interface](llm.md) - Base provider interface

### Tools
- [Tool Registry](tools.md) - Tool registration and discovery
- [Available Tools](tools.md) - Built-in tools
- [Custom Tools](tools.md) - Creating custom tools

### Observability
- [MLFlow Tracker](observability.md) - MLFlow integration
- [Cost Reporter](observability.md) - Cost tracking
- [Profiler](observability.md) - Performance profiling

## Exception Reference

### Configuration Errors
- [`ConfigLoadError`](runtime.md#configurable_agents.runtime.ConfigLoadError) - Config file parsing failed
- [`ConfigValidationError`](runtime.md#configurable_agents.runtime.ConfigValidationError) - Config validation failed

### Runtime Errors
- [`WorkflowExecutionError`](runtime.md#configurable_agents.runtime.WorkflowExecutionError) - Workflow execution failed
- [`NodeExecutionError`](runtime.md#configurable_agents.runtime.NodeExecutionError) - Node execution failed

### Tool Errors
- [`ToolNotFoundError`](tools.md#configurable_agents.tools.ToolNotFoundError) - Tool not in registry
- [`ToolExecutionError`](tools.md#configurable_agents.tools.ToolExecutionError) - Tool execution failed

## Module Index

```{toctree}
:maxdepth: 2

runtime
config
core
llm
tools
observability
```

## Additional Resources

- [User Documentation](../)
- [Configuration Reference](../CONFIG_REFERENCE.md)
- [Architecture](../ARCHITECTURE.md)
- [Examples](../../examples/)
- [Contributing](../../CONTRIBUTING.md)
