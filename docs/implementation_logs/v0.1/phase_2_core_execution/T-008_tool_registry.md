# T-008: Tool Registry

**Status**: ✅ Complete
**Completed**: 2026-01-25
**Commit**: T-008: Tool registry - Web search tool integration
**Phase**: Phase 2 (Core Execution)
**Progress After**: 9/20 tasks (45%)

---

## 🎯 What Was Done

- Implemented centralized tool registry for loading tools by name
- Created registry-based architecture with factory functions for lazy loading
- Implemented `serper_search` web search tool using Google Serper API
- Comprehensive error handling with helpful messages
- Added langchain-community dependency for tool integrations
- 37 comprehensive tests covering all scenarios
- Total: 268 tests passing (up from 231)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/tools/
├── registry.py (tool registry with global instance)
└── serper.py (Serper web search implementation)
```

### Tests

```
tests/tools/
├── __init__.py
├── test_registry.py (22 registry tests)
└── test_serper.py (15 serper tests + 2 integration tests)
```

---

## 🔧 How to Verify

### 1. Test tool registry

```bash
pytest tests/tools/test_registry.py -v
# Expected: 22 passed
```

### 2. Test serper tool

```bash
pytest tests/tools/test_serper.py -v -m "not integration"
# Expected: 15 passed
```

### 3. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 268 passed (37 new + 231 existing)
```

### 4. Use tool registry

```python
import os
os.environ["SERPER_API_KEY"] = "your-key-here"

from configurable_agents.tools import get_tool, list_tools

# List tools
print(list_tools())  # ['serper_search']

# Get and use tool
search = get_tool("serper_search")
results = search.run("artificial intelligence news")
print(results)
```

---

## ✅ What to Expect

**Working**:
- ✅ Tool registry loads tools by name from config
- ✅ Serper search tool works with valid API key
- ✅ Helpful error messages for missing tools or API keys
- ✅ Tools are LangChain BaseTool instances
- ✅ Registry is extensible for custom tools
- ✅ Lazy loading - tools created only when requested
- ⚠️ Only `serper_search` available in v0.1 (more tools in v0.2+)

**Not Yet Working**:
- ❌ Only web search tool available (v0.1 constraint)
- ❌ Custom tool registration not yet exposed (internal only)

---

## 💻 Public API

### Main Tool Functions

```python
from configurable_agents.tools import (
    get_tool,      # Get tool by name: get_tool(name) -> BaseTool
    list_tools,    # List available tools: list_tools() -> list[str]
    has_tool,      # Check tool exists: has_tool(name) -> bool
)

# List available tools
tools = list_tools()  # ['serper_search']

# Check if tool exists
if has_tool("serper_search"):
    # Get tool instance
    search = get_tool("serper_search")
    results = search.run("Python programming")
```

### Error Handling

```python
from configurable_agents.tools import ToolNotFoundError, ToolConfigError

# Tool not found
try:
    tool = get_tool("unknown_tool")
except ToolNotFoundError as e:
    # Tool 'unknown_tool' not found in registry.
    # Available tools: serper_search
    # Suggestion: Check the tool name for typos. Tools are case-sensitive.
    print(e)

# Missing API key
try:
    tool = get_tool("serper_search")
except ToolConfigError as e:
    # Tool 'serper_search' configuration failed:
    # SERPER_API_KEY environment variable not set
    # Set the environment variable: SERPER_API_KEY
    # Example: export SERPER_API_KEY=your-api-key-here
    print(e)
```

### Complete Public API

```python
# From configurable_agents.tools

# Registry functions
from configurable_agents.tools import (
    get_tool,          # Get tool by name
    list_tools,        # List available tools
    has_tool,          # Check if tool exists
    register_tool,     # Register custom tool (advanced)
)

# Exceptions
from configurable_agents.tools import (
    ToolNotFoundError,    # Tool not found in registry
    ToolConfigError,      # Tool configuration failed
)

# Usage
search = get_tool("serper_search")
results = search.run("AI research")
```

---

## 📚 Dependencies Added

### New Dependencies

- `langchain-community >= 0.0.20` - For GoogleSerperAPIWrapper

**Status**: Declared in `pyproject.toml`, used in serper tool implementation

---

## 💡 Design Decisions

### Why Factory Pattern?

- Tools created via factory functions for lazy loading
- Only instantiate tools when actually needed
- Avoids loading API keys at import time
- Enables better error messages (fail when used, not imported)

### Why Global Registry?

- Single global instance for convenience
- Simplifies tool lookup from configs
- Matches LangChain pattern
- Easy to extend with custom tools

### Why Fail Loudly?

- Clear errors with actionable messages
- Fail at runtime (when tool requested) not import time
- Include setup instructions in error messages
- List available tools to help users

### Why LangChain Integration?

- Tools use LangChain BaseTool interface
- Compatible with LangChain agent frameworks
- Standard tool calling protocol
- Enables future tool ecosystem

### Why Environment-Based Config?

- API keys from environment variables (secure)
- Follows 12-factor app principles
- Easy to configure in different environments
- No secrets in code or configs

### Why Case-Sensitive Names?

- Tool names match config exactly
- Simpler implementation (no normalization)
- Clear error messages for typos
- Predictable behavior

---

## 🧪 Tests Created

**Files**:
- `tests/tools/test_registry.py` (22 tests)
- `tests/tools/test_serper.py` (15 unit + 2 integration tests)

### Test Categories (37 tests total)

#### Registry Tests (22 tests)

1. **Tool Registration** (5 tests)
   - Register tool with factory function
   - Register multiple tools
   - Overwrite existing tool
   - Invalid factory function
   - Factory function returns non-Tool

2. **Tool Retrieval** (6 tests)
   - Get tool by name
   - Get tool creates new instance each time
   - Get non-existent tool raises error
   - Error message includes available tools
   - Error message includes suggestion for typos

3. **Tool Listing** (4 tests)
   - List all tools
   - List tools after registration
   - Empty registry
   - List sorted alphabetically

4. **Tool Existence** (3 tests)
   - has_tool returns True for existing tool
   - has_tool returns False for non-existent tool
   - Case sensitivity check

5. **Global Registry** (4 tests)
   - Global instance accessible
   - get_tool uses global instance
   - list_tools uses global instance
   - Built-in tools pre-registered

#### Serper Tool Tests (15 unit + 2 integration)

1. **Tool Creation** (4 tests)
   - Create tool with valid API key
   - Tool name is "serper_search"
   - Tool description is helpful
   - Tool is LangChain BaseTool instance

2. **API Key Validation** (5 tests)
   - Missing API key raises error
   - Error message includes setup instructions
   - Empty API key raises error
   - API key from environment variable
   - Error message helpful for new users

3. **Tool Behavior** (4 tests)
   - Tool run method exists
   - Tool accepts query string
   - Tool returns string result
   - Tool description helps LLM selection

4. **Error Handling** (2 tests)
   - ToolConfigError on missing key
   - Error includes environment variable name

5. **Integration Tests** (2 tests - marked)
   - Real API call with valid key
   - Search results contain relevant content

---

## 🎨 Tool Registry Features

### Get Tool by Name

```python
search = get_tool("serper_search")
```

- ✅ Returns LangChain BaseTool instance
- ✅ Creates fresh instance each call (lazy loading)
- ✅ Raises ToolNotFoundError if not found
- ✅ Error includes available tools list

### List Available Tools

```python
tools = list_tools()  # ['serper_search']
```

- ✅ Returns list of tool names
- ✅ Sorted alphabetically
- ✅ Reflects registered tools

### Check Tool Exists

```python
if has_tool("serper_search"):
    tool = get_tool("serper_search")
```

- ✅ Returns boolean
- ✅ Case-sensitive matching
- ✅ No exceptions raised

### Register Custom Tools

```python
def my_tool_factory():
    return MyCustomTool()

register_tool("my_tool", my_tool_factory)
```

- ✅ Register custom tool with factory function
- ✅ Factory called on each get_tool
- ✅ Overwrites existing tools
- ✅ Validates factory returns BaseTool

---

## 🔍 Serper Search Tool

### Features

- ✅ Web search using Google Search via Serper API
- ✅ Reads SERPER_API_KEY from environment
- ✅ Clear error messages with setup instructions
- ✅ LangChain Tool wrapper for compatibility
- ✅ Helpful description for LLM tool selection

### Usage

```python
import os
os.environ["SERPER_API_KEY"] = "your-key-here"

search = get_tool("serper_search")
results = search.run("Python programming tutorials")
print(results)
```

### Error Messages

```
# Missing API key
ToolConfigError: Tool 'serper_search' configuration failed:
SERPER_API_KEY environment variable not set

Set the environment variable: SERPER_API_KEY
Example: export SERPER_API_KEY=your-api-key-here

Get your API key from: https://serper.dev/
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-008 marked DONE, progress updated to 9/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)
- ✅ .env.example (added SERPER_API_KEY template)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-008: Tool registry - Web search tool integration

- Implemented tool registry with factory-based lazy loading
  - get_tool(name) - Get tool by name
  - list_tools() - List available tools
  - has_tool(name) - Check if tool exists
  - register_tool(name, factory) - Register custom tools
  - Fail loudly if tool not found or API key missing

- Implemented serper_search web search tool
  - Google Search via Serper API
  - Reads SERPER_API_KEY from environment
  - Clear error messages with setup instructions
  - LangChain Tool wrapper for compatibility

- Added langchain-community dependency
- Created 37 comprehensive tests
  - 22 registry tests (registration, retrieval, errors)
  - 15 serper tests (creation, validation, behavior)
  - 2 integration tests (marked with @pytest.mark.integration)

Verification:
  pytest -v -m 'not integration'
  Expected: 268 passed (37 tools + 231 existing)

Progress: 9/20 tasks (45%) - Phase 2 (Core Execution) 1/6 complete
Next: T-009 (LLM Provider - Google Gemini)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-008 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Tool integration requirements
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Tools component architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Tool ecosystem roadmap

---

## 🚀 Next Steps for Users

### Setup Serper API Key

```bash
# Get API key from https://serper.dev/
export SERPER_API_KEY="your-api-key-here"

# Or add to .env file
echo "SERPER_API_KEY=your-api-key-here" >> .env
```

### Use in Workflow Config

```yaml
nodes:
  - id: search
    prompt: "Search the web for: {query}"
    tools:
      - serper_search  # Tool name from registry
    outputs:
      - results
```

### Test Tool Integration

```python
from configurable_agents.tools import get_tool

search = get_tool("serper_search")
results = search.run("latest AI research")
print(results)
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 1/6 complete (17%)**
- ✅ T-008: Tool Registry
- ⏳ T-009: LLM Provider (Google Gemini)
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

---

*Implementation completed: 2026-01-25*
*Next task: T-009 (LLM Provider)*
