# Tools Module

The tools module provides a registry system for LangChain tool integrations.

## Tool Registry

### register_tool

```{py:function} register_tool(name: str, factory: Callable[[], Tool])
```

Register a tool in the tool registry.

**Parameters:**
- `name` (str) - Unique tool name
- `factory` (Callable) - Factory function that returns a Tool instance

**Examples:**

```python
from langchain_core.tools import Tool
from configurable_agents.tools import register_tool

def create_my_tool() -> Tool:
    return Tool(
        name="my_tool",
        description="Does something useful",
        func=lambda x: f"Processed: {x}"
    )

register_tool("my_tool", create_my_tool)
```

### get_tool

```{py:function} get_tool(name: str) -> Tool
```

Retrieve a tool from the registry.

**Parameters:**
- `name` (str) - Tool name

**Returns:**
- `Tool` - Tool instance

**Raises:**
- `ToolNotFoundError` - If tool is not registered

### list_tools

```{py:function} list_tools() -> list[str]
```

List all registered tool names.

**Returns:**
- list[str] - List of tool names

## Built-in Tools

### Web Search

```{py:class} configurable_agents.tools.serper.SerperSearchTool
```

Web search using Serper API.

**Environment Variables:**
- `SERPER_API_KEY` - Serper API key

### System Tools

```{py:class} configurable_agents.tools.system_tools.ShellTool
```

Execute shell commands (with whitelist).

**Environment Variables:**
- `ALLOWED_COMMANDS` - Comma-separated list of allowed commands

### File Tools

```{py:class} configurable_agents.tools.file_tools.FileReadTool
```

Read file contents.

**Environment Variables:**
- `ALLOWED_PATHS` - Comma-separated list of allowed paths

## Exceptions

### ToolNotFoundError

```{py:exception} configurable_agents.tools.ToolNotFoundError
```

Raised when a requested tool is not in the registry.

### ToolExecutionError

```{py:exception} configurable_agents.tools.ToolExecutionError
```

Raised when tool execution fails.

## Full API

```{py:module} configurable_agents.tools
```

## See Also

- [Tool Development Guide](../TOOL_DEVELOPMENT.md) - Creating custom tools
- [Security Guide](../SECURITY_GUIDE.md) - Tool security considerations
