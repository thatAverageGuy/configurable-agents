# Core Module

The core module provides graph building, state management, and node execution functionality.

## Main Functions

### build_graph

```{py:function} build_graph(config: WorkflowConfig, repos: StorageRepositories) -> StateGraph
```

Construct a LangGraph StateGraph from workflow configuration.

**Parameters:**
- `config` (WorkflowConfig) - Workflow configuration
- `repos` (StorageRepositories) - Storage repository instances

**Returns:**
- `StateGraph` - Constructed LangGraph ready for execution

**Examples:**

```python
from configurable_agents.config import parse_config_file
from configurable_agents.core import build_graph
from configurable_agents.storage import create_storage_repositories

config = parse_config_file("examples/simple_workflow.yaml")
repos = create_storage_repositories()
graph = build_graph(config, repos)
```

### build_state_model

```{py:function} build_state_model(state_schema: StateSchema) -> type[BaseModel]
```

Generate a Pydantic BaseModel from state schema.

**Parameters:**
- `state_schema` (StateSchema) - State schema definition

**Returns:**
- type[BaseModel] - Generated Pydantic model class

### build_output_model

```{py:function} build_output_model(config: WorkflowConfig) -> type[BaseModel]
```

Generate output model from workflow configuration.

**Parameters:**
- `config` (WorkflowConfig) - Workflow configuration

**Returns:**
- type[BaseModel] - Generated output model class

## Node Execution

### execute_node

```{py:function} execute_node(node_config: NodeConfig, state: dict, **kwargs) -> dict
```

Execute a single node with given state.

**Parameters:**
- `node_config` (NodeConfig) - Node configuration
- `state` (dict) - Current state
- `**kwargs` - Additional execution parameters

**Returns:**
- dict - Updated state after node execution

## Control Flow

### evaluate_condition

```{py:function} evaluate_condition(condition: str, state: dict) -> bool
```

Evaluate a conditional expression against state.

**Parameters:**
- `condition` (str) - Condition expression
- `state` (dict) - Current state

**Returns:**
- bool - True if condition is met, False otherwise

## Full API

```{py:module} configurable_agents.core
```

## See Also

- [Runtime Module](runtime.md) - Workflow execution
- [Configuration Module](config.md) - Configuration models
