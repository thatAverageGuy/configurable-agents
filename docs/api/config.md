# Configuration Module

The configuration module handles workflow configuration parsing, validation, and schema definitions.

## Main Classes

### WorkflowConfig

```{py:class} configurable_agents.config.schema.WorkflowConfig
```

Main workflow configuration model.

**Attributes:**
- `name` (str) - Workflow name
- `description` (str) - Workflow description
- `version` (str) - Config version (default: "1.0")
- `state` (StateSchema) - State schema definition
- `nodes` (list[NodeConfig]) - List of node configurations
- `edges` (list[EdgeConfig]) - List of edge connections
- `observability` (ObservabilityConfig, optional) - MLFlow and monitoring settings

### StateSchema

```{py:class} configurable_agents.config.schema.StateSchema
```

Defines the state structure for workflow execution.

**Attributes:**
- `type` (str) - State type ("object", "array", "string", etc.)
- `properties` (dict, optional) - Property definitions for object types
- `items` (StateSchema, optional) - Item schema for array types
- `required` (list[str], optional) - Required property names

### NodeConfig

```{py:class} configurable_agents.config.schema.NodeConfig
```

Configuration for individual workflow nodes.

**Attributes:**
- `name` (str) - Node name (unique within workflow)
- `llm` (LLMConfig, optional) - LLM provider configuration
- `tools` (list[str], optional) - List of tool names to use
- `prompt` (str) - Prompt template
- `type` (str, optional) - Node type ("llm", "code", etc.)
- `code` (str, optional) - Code for code execution nodes

## Main Functions

### parse_config_file

```{py:function} parse_config_file(config_path: str | Path) -> WorkflowConfig
```

Parse a workflow configuration from YAML or JSON file.

**Parameters:**
- `config_path` (str | Path) - Path to configuration file

**Returns:**
- WorkflowConfig - Parsed configuration object

**Raises:**
- `ConfigLoadError` - If file cannot be parsed
- `ConfigValidationError` - If configuration is invalid

**Examples:**

```python
from configurable_agents.config import parse_config_file

config = parse_config_file("examples/simple_workflow.yaml")
print(f"Workflow: {config.name}")
print(f"Nodes: {len(config.nodes)}")
```

### validate_config

```{py:function} validate_config(config: WorkflowConfig) -> list[ValidationError]
```

Validate a workflow configuration.

**Parameters:**
- `config` (WorkflowConfig) - Configuration to validate

**Returns:**
- list[ValidationError] - List of validation errors (empty if valid)

## Full API

```{py:module} configurable_agents.config
```

## See Also

- [Runtime Module](runtime.md) - Workflow execution
- [Configuration Reference](../CONFIG_REFERENCE.md) - Complete configuration guide
