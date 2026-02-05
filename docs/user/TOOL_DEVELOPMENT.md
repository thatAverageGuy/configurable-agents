# Custom Tool Development

This guide shows you how to create, register, and integrate custom tools in Configurable Agents.

## Table of Contents
- [Overview](#overview)
- [Tool Interface](#tool-interface)
- [Creating a Custom Tool](#creating-a-custom-tool)
- [Tool Examples](#tool-examples)
- [Tool Configuration](#tool-configuration)
- [Security Considerations](#security-considerations)
- [Testing Tools](#testing-tools)
- [Tool Best Practices](#tool-best-practices)
- [Advanced Tool Patterns](#advanced-tool-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

Tools in Configurable Agents extend the capabilities of LLM-powered nodes by enabling them to perform actions beyond text generation. Tools can:
- Make API calls to external services
- Query databases
- Execute system commands
- Process files
- Perform computations

All tools extend LangChain's `BaseTool` class and are registered in the tool registry for discovery and use in workflows.

## Tool Interface

### BaseTool from LangChain

All tools extend LangChain's `BaseTool` class:

```python
from langchain_core.tools import Tool

def my_tool_function(input_data: str) -> str:
    """Process input and return output."""
    # Your tool logic here
    return result

tool = Tool(
    name="my_tool",
    description="Description of what the tool does",
    func=my_tool_function,
)
```

### Tool Registry

The tool registry uses a factory pattern for lazy loading and validation:

```python
from configurable_agents.tools import register_tool

def create_my_tool() -> Tool:
    """Create and configure custom tool."""
    return Tool(
        name="my_tool",
        description="Tool description",
        func=my_tool_function,
    )

register_tool("my_tool", create_my_tool)
```

## Creating a Custom Tool

### Step 1: Define Tool Function

Create a function that takes a string input and returns a string output:

```python
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"
```

### Step 2: Create Tool Factory

Create a factory function that returns a configured Tool instance:

```python
from langchain_core.tools import Tool

def create_calculator_tool() -> Tool:
    """Create a calculator tool."""
    return Tool(
        name="calculator",
        description="Evaluate mathematical expressions. Input: expression like '2+2' or '5*10'",
        func=calculate,
    )
```

### Step 3: Register Tool

Register the tool in the registry:

```python
# In src/configurable_agents/tools/registry.py or your custom tools file
from configurable_agents.tools import register_tool

register_tool("calculator", create_calculator_tool)
```

### Step 4: Use in Workflow

Use the tool in a workflow configuration:

```yaml
nodes:
  - name: calculate
    llm:
      provider: google
      model: gemini-1.5-flash
    tools:
      - calculator
    prompt: |
      Calculate the result of: {expression}
      Use the calculator tool to evaluate the expression.
```

## Tool Examples

### Example 1: HTTP API Tool

```python
import requests
from langchain_core.tools import Tool
from configurable_agents.tools import register_tool

def call_api(input_data: str) -> str:
    """Make HTTP GET request to endpoint."""
    try:
        response = requests.get(input_data, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def create_api_tool() -> Tool:
    """Create an HTTP API tool."""
    return Tool(
        name="api_caller",
        description="Make HTTP GET requests to REST APIs. Input: URL",
        func=call_api,
    )

register_tool("api_caller", create_api_tool)
```

### Example 2: Database Query Tool

```python
import sqlite3
import json
from langchain_core.tools import Tool
from configurable_agents.tools import register_tool

def query_database(input_data: str) -> str:
    """Execute SQL query and return results."""
    try:
        # Parse input as JSON for flexibility
        params = json.loads(input_data)
        query = params.get("query", "")
        db_path = params.get("db_path", "database.db")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()

        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

def create_db_tool() -> Tool:
    """Create a database query tool."""
    return Tool(
        name="database_query",
        description="Execute SQL queries on SQLite database. Input: JSON with 'query' and optional 'db_path'",
        func=query_database,
    )

register_tool("database_query", create_db_tool)
```

### Example 3: File Processing Tool

```python
from pathlib import Path
from langchain_core.tools import Tool
from configurable_agents.tools import register_tool

def process_file(input_data: str) -> str:
    """Read and process file contents."""
    try:
        file_path = Path(input_data)
        content = file_path.read_text()

        # Example processing: count words
        word_count = len(content.split())
        return f"File: {file_path.name}\nWords: {word_count}\nPreview: {content[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_file_tool() -> Tool:
    """Create a file processing tool."""
    return Tool(
        name="file_processor",
        description="Read and analyze text files. Input: file path",
        func=process_file,
    )

register_tool("file_processor", create_file_tool)
```

## Tool Configuration

### Environment Variables

Access environment variables for configuration:

```python
import os
from langchain_core.tools import Tool

def create_configured_tool() -> Tool:
    """Create tool with environment configuration."""
    api_key = os.getenv("MY_TOOL_API_KEY")
    if not api_key:
        raise ValueError(
            "MY_TOOL_API_KEY environment variable not set. "
            "Please set it before using this tool."
        )

    return Tool(
        name="my_tool",
        description="Tool with API key configuration",
        func=lambda x: call_with_api(x, api_key),
    )
```

### Tool Parameters

Tools receive string input from LLM. Use JSON for complex data:

```python
import json

def complex_tool(input_json: str) -> str:
    """Process complex input with parameters."""
    try:
        params = json.loads(input_json)

        # Access fields
        field1 = params.get('field1', 'default')
        field2 = params.get('field2', 0)

        # Process data
        result = process(field1, field2)
        return json.dumps(result)
    except json.JSONDecodeError:
        return "Error: Invalid JSON input"

def create_complex_tool() -> Tool:
    return Tool(
        name="complex_tool",
        description="Process complex data. Input: JSON with 'field1' and 'field2'",
        func=complex_tool,
    )
```

## Security Considerations

### Command Execution

If your tool executes system commands, implement whitelisting:

```python
import os
from configurable_agents.tools import ToolConfigError

def safe_command_tool(cmd: str) -> str:
    """Execute only whitelisted commands."""
    allowed = os.getenv("ALLOWED_COMMANDS", "").split(",")
    cmd_name = cmd.split()[0]

    if allowed and cmd_name not in allowed:
        return f"Error: Command '{cmd_name}' not in allowed list: {allowed}"

    try:
        result = os.system(cmd)
        return f"Executed: {cmd}\nResult: {result}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Input Validation

Always validate and sanitize inputs:

```python
import re

def validated_tool(input_data: str) -> str:
    """Validate input before processing."""
    # Check format
    if not re.match(r'^[a-zA-Z0-9_-]+$', input_data):
        return "Error: Invalid input format. Only alphanumeric characters, hyphens, and underscores allowed."

    # Check length
    if len(input_data) > 1000:
        return "Error: Input too long. Maximum 1000 characters."

    # Process validated input
    return process(input_data)
```

### Error Handling

Handle errors gracefully:

```python
def robust_tool(input_data: str) -> str:
    """Tool with comprehensive error handling."""
    try:
        # Validate input
        if not input_data:
            return "Error: Empty input"

        # Process
        result = process(input_data)

        # Validate output
        if not result:
            return "Error: Processing produced no output"

        return result

    except ValueError as e:
        return f"Validation Error: {str(e)}"
    except RuntimeError as e:
        return f"Runtime Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"
```

## Testing Tools

### Unit Tests

Write unit tests for your tools:

```python
import pytest
from configurable_agents.tools.my_tool import create_my_tool

def test_my_tool_basic():
    """Test basic tool functionality."""
    tool = create_my_tool()
    result = tool.func("test input")
    assert "expected" in result

def test_my_tool_error_handling():
    """Test error handling."""
    tool = create_my_tool()
    result = tool.func("")
    assert "Error" in result

def test_my_tool_edge_cases():
    """Test edge cases."""
    tool = create_my_tool()
    # Test with special characters
    result = tool.func("!@#$%^&*()")
    # Test with very long input
    result = tool.func("a" * 10000)
```

### Integration Tests

Test tools in workflow context:

```python
from configurable_agents.config import parse_config_file
from configurable_agents.runtime import run_workflow

def test_tool_in_workflow():
    """Test tool integration in workflow."""
    config = parse_config_file("workflows_with_tool.yaml")
    result = run_workflow(config)
    assert result["final_output"] is not None
    # Verify tool was used
```

## Tool Best Practices

1. **Keep tools focused** - Single responsibility principle
2. **Handle errors gracefully** - Return error messages, don't raise
3. **Use type hints** - For better IDE support and documentation
4. **Document parameters** - Clear docstrings and descriptions
5. **Validate inputs** - Sanitize all inputs before processing
6. **Consider rate limits** - For API tools, implement throttling
7. **Log operations** - Add logging for debugging
8. **Cache results** - When appropriate, cache expensive operations
9. **Timeout operations** - Don't let tools hang indefinitely
10. **Test thoroughly** - Unit tests, integration tests, edge cases

## Advanced Tool Patterns

### Async Tools

```python
import asyncio
from langchain_core.tools import Tool

async def async_tool(input_data: str) -> str:
    """Asynchronous tool implementation."""
    await asyncio.sleep(1)  # Simulate async operation
    return f"Processed: {input_data}"

def create_async_tool() -> Tool:
    """Create tool with async function."""
    return Tool(
        name="async_tool",
        func=lambda x: asyncio.run(async_tool(x)),
        description="Asynchronous processing tool",
    )
```

### Stateful Tools

```python
class StatefulTool:
    """Stateful tool with caching."""

    def __init__(self):
        self.cache = {}

    def __call__(self, input_data: str) -> str:
        """Process with caching."""
        if input_data in self.cache:
            return f"Cached: {self.cache[input_data]}"

        result = process(input_data)
        self.cache[input_data] = result
        return f"Processed: {result}"

def create_stateful_tool() -> Tool:
    """Create stateful tool instance."""
    tool_instance = StatefulTool()
    return Tool(
        name="stateful_tool",
        func=tool_instance,
        description="Stateful tool with caching",
    )
```

### Multi-Step Tools

```python
def multi_step_tool(input_data: str) -> str:
    """Tool with multiple processing steps."""
    # Step 1: Parse input
    parsed = parse(input_data)
    if not parsed:
        return "Error: Failed to parse input"

    # Step 2: Validate
    validated = validate(parsed)
    if not validated:
        return "Error: Validation failed"

    # Step 3: Process
    result = process(validated)

    # Step 4: Format output
    return format_output(result)
```

## Troubleshooting

### Tool Not Found

**Error**: `Tool 'my_tool' not found in registry`

**Solutions**:
- Check tool is registered in registry.py
- Verify tool factory function exists
- Check for import errors
- Ensure registration code runs before tool usage

**Debugging**:
```python
from configurable_agents.tools import list_tools
print("Available tools:", list_tools())
```

### Tool Execution Fails

**Error**: `Tool execution failed: ...`

**Solutions**:
- Check tool function signature (must accept str, return str)
- Verify input format matches expectations
- Check environment variables are set
- Review error messages in tool output
- Test tool function directly outside workflow

**Debugging**:
```python
tool = create_my_tool()
result = tool.func("test input")
print(f"Tool result: {result}")
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'my_tool'`

**Solutions**:
- Ensure tool file is in correct location
- Check `__init__.py` exports
- Verify Python path includes tool directory
- Install required dependencies

## Related Documentation

- [Configuration Reference](CONFIG_REFERENCE.md) - Tool configuration in workflows
- [Security Guide](SECURITY_GUIDE.md) - Tool security considerations
- [Architecture Decision Records](adr/) - Design decisions for tool system
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/tools/) - LangChain tool concepts

## Next Steps

1. **Experiment**: Create a simple tool and test it
2. **Extend**: Add more complex functionality
3. **Integrate**: Use tool in real workflow
4. **Share**: Consider contributing useful tools back to the project

---

**Level**: Advanced (⭐⭐⭐⭐)
**Prerequisites**: Python programming, basic LangChain knowledge
**Time Investment**: 2-4 hours to build and test a custom tool
