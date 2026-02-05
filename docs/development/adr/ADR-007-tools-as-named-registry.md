# ADR-007: Tools as Named Registry

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

Nodes need access to external tools (web search, code execution, database queries, etc.) to augment LLM capabilities.

### Tool Integration Options

**1. Hardcoded in Config**:
```yaml
nodes:
  - id: research
    tools:
      - name: web_search
        api_key: "sk-abc123"  # ← Credentials in config
        url: "https://api.serper.dev"
```

**2. Pre-Registered Names**:
```yaml
nodes:
  - id: research
    tools: [serper_search]  # ← Just reference by name
```

**3. Custom Tool Definitions**:
```yaml
tools:
  - id: my_custom_search
    type: api
    endpoint: "https://my-api.com/search"
    auth: bearer_token

nodes:
  - id: research
    tools: [my_custom_search]
```

**4. Python Functions**:
```yaml
nodes:
  - id: research
    tools:
      - type: python
        code: |
          def search(query):
              import requests
              return requests.get(f"https://...?q={query}")
```

---

## Decision

**v0.1 uses a pre-registered tool registry with name-based lookup.**

Tools are referenced by name in config. Credentials come from environment variables.

---

## Implementation

### Config Usage

```yaml
nodes:
  - id: research
    prompt: "Research {state.topic}"
    tools:
      - serper_search  # Just the name
    outputs: [research]
    output_schema:
      fields:
        - name: research
          type: str
```

### Registry

```python
# tools/registry.py
TOOL_REGISTRY = {
    'serper_search': SerperSearchTool,
    # More tools added here
}

def get_tool(tool_name: str) -> BaseTool:
    """Get tool by name from registry"""
    if tool_name not in TOOL_REGISTRY:
        available = ', '.join(TOOL_REGISTRY.keys())
        raise ValueError(
            f"Unknown tool '{tool_name}'. "
            f"Available tools: {available}"
        )

    tool_class = TOOL_REGISTRY[tool_name]
    return tool_class()  # Instantiate and return
```

### Tool Implementation

```python
# tools/serper.py
import os
from langchain.tools import BaseTool

class SerperSearchTool(BaseTool):
    name = "serper_search"
    description = "Search the web using Serper API"

    def _run(self, query: str) -> str:
        api_key = os.getenv('SERPER_API_KEY')
        if not api_key:
            raise ValueError(
                "SERPER_API_KEY not found in environment. "
                "Get one at https://serper.dev"
            )

        # Make API call
        response = requests.post(
            'https://google.serper.dev/search',
            json={'q': query},
            headers={'X-API-KEY': api_key}
        )

        return response.json()
```

### Environment Variables

```.env
# Required for tools
SERPER_API_KEY=your-api-key-here
GOOGLE_API_KEY=your-gemini-key-here
```

---

## Rationale

### 1. Security (No Credentials in Config)

**Bad** (credentials in config):
```yaml
tools:
  - name: web_search
    api_key: "sk-abc123456789"  # ← Leaks if config shared
```

**Problems**:
- Configs in git → credentials in git history
- Sharing configs → sharing credentials
- Security risk

**Good** (credentials in environment):
```yaml
tools:
  - serper_search  # ← No credentials
```

```.env
SERPER_API_KEY=sk-abc123456789  # ← In .env (gitignored)
```

**Benefits**:
- Configs can be shared safely
- Credentials stay out of version control
- Standard practice (12-factor app)

### 2. Simplicity

**Just reference by name**:
```yaml
tools: [serper_search, calculator]
```

**No need to configure**:
- API endpoints
- Authentication methods
- Request formats
- Response parsing

**Everything is encapsulated in the tool implementation.**

### 3. Validation at Parse Time

```python
# Config validator can check tool exists
def validate_tools(node_config):
    for tool_name in node_config.get('tools', []):
        if tool_name not in TOOL_REGISTRY:
            raise ValidationError(
                f"Unknown tool '{tool_name}'. "
                f"Available: {list(TOOL_REGISTRY.keys())}"
            )
```

**Fail fast**: Know before execution if tool is missing.

### 4. Extensibility

**Adding a new tool is easy**:

1. Implement tool class
2. Register in `TOOL_REGISTRY`
3. Document in README

**Users can reference immediately**:
```yaml
tools: [new_tool]
```

### 5. Leverages LangChain Ecosystem

**Use existing LangChain tools**:
- 100+ pre-built tools
- Well-tested
- Standard interface

**We just need thin wrappers**:
```python
from langchain.tools import DuckDuckGoSearchRun

TOOL_REGISTRY = {
    'duckduckgo_search': DuckDuckGoSearchRun,
    # Wrap and register
}
```

---

## Alternatives Considered

### Alternative 1: Inline Tool Definitions in Config

```yaml
tools:
  - id: my_search
    type: api
    endpoint: "https://api.example.com/search"
    method: POST
    headers:
      Authorization: "Bearer ${SEARCH_API_KEY}"
    body:
      query: "{input}"
    response_path: "results.items"

nodes:
  - id: research
    tools: [my_search]
```

**Pros**:
- Flexible (can define any tool)
- No code changes to add tools
- Power users can customize

**Cons**:
- **Complex config** (verbose, error-prone)
- **Security risk** (credentials in config or complex templating)
- **Hard to validate** (many possible configurations)
- **Reinventing wheel** (most tools already exist in LangChain)

**Why rejected**: Too complex for v0.1. Could add in v0.3+ for advanced users.

### Alternative 2: Python Code in Config

```yaml
nodes:
  - id: research
    tools:
      - type: python
        code: |
          import requests
          def search(query):
              return requests.get(f"https://api.com?q={query}").json()
```

**Pros**:
- Maximum flexibility
- No registry needed

**Cons**:
- **Security risk** (arbitrary code execution)
- **Hard to sandbox** (code can do anything)
- **Not config-first** (configs contain code)
- **Hard to validate** (can't parse Python in YAML validator)

**Why rejected**: Security nightmare. Violates config-first principle.

### Alternative 3: Tool Discovery (Auto-Register)

```yaml
# Config just references tool
tools: [web_search]

# System searches for tool implementations
# 1. Check built-in registry
# 2. Check user's tools/ directory
# 3. Check installed packages (langchain-community, etc.)
```

**Pros**:
- Flexible (users can add tools without modifying registry)
- Discovers community tools

**Cons**:
- **Complex implementation** (search paths, import logic)
- **Surprising behavior** (which tool gets loaded?)
- **Version conflicts** (multiple `web_search` implementations)
- **Slower validation** (need to search filesystem)

**Why rejected**: Too complex for v0.1. Pre-registered registry is explicit and predictable.

### Alternative 4: No Tools (LLM Only)

```yaml
# Don't support tools at all
nodes:
  - id: research
    prompt: "Research {state.topic}"
    # No tools
```

**Pros**:
- Simplest implementation
- No external dependencies

**Cons**:
- **Limited capability** (can't access web, databases, etc.)
- **Not competitive** (other frameworks have tools)
- **Users blocked** (can't build real-world agents)

**Why rejected**: Tools are essential for useful agents.

---

## Consequences

### Positive Consequences

1. **Secure by Default**
   - Credentials in environment, not config
   - Configs can be shared publicly

2. **Simple Config**
   ```yaml
   tools: [serper_search]  # One line
   ```

3. **Easy Validation**
   - Check tool exists at parse time
   - Fail fast if missing

4. **Extensible**
   - Add tools by registering in one place
   - No config changes needed

5. **Leverages Ecosystem**
   - Use LangChain's 100+ tools
   - Community tools can be added

### Negative Consequences

1. **Limited to Pre-Registered Tools**
   - Users can't define custom tools in config (v0.1)
   - **Mitigation**: v0.3+ can add custom tool definitions

2. **Requires Code Changes to Add Tools**
   - New tool → modify registry → redeploy
   - **Mitigation**: Most common tools will be included

3. **Environment Variable Management**
   - Users must set API keys correctly
   - **Mitigation**: Clear error messages, .env.example

### Risks

#### Risk 1: Missing API Key at Runtime

**Scenario**: User references `serper_search` but doesn't set `SERPER_API_KEY`.

**Likelihood**: High (common mistake)
**Impact**: Medium (workflow fails)

**Mitigation**:
```python
# Check at parse time
def validate_tool_dependencies(config):
    required_env_vars = {
        'serper_search': 'SERPER_API_KEY',
        'openai_embedding': 'OPENAI_API_KEY',
    }

    for node in config['nodes']:
        for tool in node.get('tools', []):
            if tool in required_env_vars:
                env_var = required_env_vars[tool]
                if not os.getenv(env_var):
                    warnings.warn(
                        f"Tool '{tool}' requires {env_var} environment variable. "
                        f"Workflow will fail at runtime if not set."
                    )
```

**Better error message**:
```
Warning: Node 'research' uses tool 'serper_search'
  but SERPER_API_KEY is not set.

  Get an API key at: https://serper.dev
  Then set: export SERPER_API_KEY="your-key-here"
```

#### Risk 2: Tool Registry Becomes Bloated

**Likelihood**: Medium (as we add more tools)
**Impact**: Low (performance)

**Mitigation**:
- Lazy load tools (only import when used)
- Group tools by category
- Document which tools are "core" vs "contrib"

```python
# Lazy loading
class ToolRegistry:
    _tools = {
        'serper_search': 'tools.serper.SerperSearchTool',
        'calculator': 'tools.calculator.CalculatorTool',
    }

    def get(self, name: str):
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")

        # Lazy import
        module_path, class_name = self._tools[name].rsplit('.', 1)
        module = importlib.import_module(module_path)
        tool_class = getattr(module, class_name)
        return tool_class()
```

#### Risk 3: Tool Versioning Issues

**Scenario**: LangChain updates tool interface, breaks our wrapper.

**Likelihood**: Medium
**Impact**: High (all workflows using that tool break)

**Mitigation**:
- Pin LangChain version
- Test tools with each LangChain upgrade
- Provide migration guide if tools change

---

## Tool Registry (v0.1)

### Core Tools

| Tool Name | Description | Env Var Required |
|-----------|-------------|------------------|
| `serper_search` | Google search via Serper API | `SERPER_API_KEY` |

**More tools in v0.2+:**
- `duckduckgo_search` (no API key needed)
- `calculator` (math calculations)
- `python_repl` (execute Python code)
- `file_reader` (read local files)

---

## Environment Variable Convention

### Naming

```
<SERVICE>_API_KEY  # For API keys
<SERVICE>_URL      # For endpoints
<SERVICE>_TOKEN    # For tokens
```

**Examples**:
- `SERPER_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DATABASE_URL`

### .env.example

```bash
# LLM Provider
GOOGLE_API_KEY=your-gemini-api-key

# Tools
SERPER_API_KEY=your-serper-api-key

# Optional
# OPENAI_API_KEY=your-openai-key
# ANTHROPIC_API_KEY=your-anthropic-key
```

### Documentation

Every tool must document its requirements:

```markdown
## serper_search

Web search using Serper API.

**Requirements**:
- API Key: Get free key at https://serper.dev
- Environment variable: `SERPER_API_KEY`

**Usage**:
```yaml
nodes:
  - id: research
    tools:
      - serper_search
```

**Example prompt**:
```yaml
prompt: |
  Use the web search tool to research: {state.topic}
  Find at least 3 credible sources.
```
```

---

## Tool Implementation Guidelines

### 1. Inherit from LangChain BaseTool

```python
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "What this tool does"

    def _run(self, input: str) -> str:
        # Implementation
        pass
```

### 2. Check Dependencies Early

```python
def _run(self, input: str) -> str:
    api_key = os.getenv('MY_API_KEY')
    if not api_key:
        raise ValueError(
            "MY_API_KEY not set. "
            "Get one at https://example.com"
        )
    # ...
```

### 3. Provide Good Error Messages

```python
try:
    response = requests.post(url, ...)
except requests.exceptions.RequestException as e:
    raise ValueError(
        f"API call failed: {e}\n"
        f"Check your API key and internet connection."
    )
```

### 4. Return Structured Data When Possible

```python
# Bad: Unstructured string
return "Found 5 results: result1, result2, ..."

# Good: Structured (LLM can parse)
return json.dumps({
    "results": [
        {"title": "...", "url": "..."},
        {"title": "...", "url": "..."},
    ],
    "count": 5
})
```

---

## Future: Custom Tools (v0.3+)

```yaml
# Define custom tool in config
custom_tools:
  - id: my_company_api
    type: rest_api
    endpoint: "https://api.mycompany.com/search"
    method: POST
    auth:
      type: bearer
      token_env: COMPANY_API_TOKEN
    request:
      query: "{input}"
    response:
      path: "data.results"

nodes:
  - id: research
    tools:
      - serper_search      # Built-in
      - my_company_api     # Custom
```

**Use cases**:
- Internal company APIs
- Custom databases
- Proprietary tools

**Implementation**: Parse `custom_tools` section, generate LangChain tools dynamically.

---

## Testing Strategy

### T-008: Tool Registry Tests

**Unit tests**:
- Get tool by name
- Error if tool not found
- List available tools

**Integration tests** (with real APIs):
- Test each tool works
- Test API key missing error
- Test API call failure handling

**Mark as slow/optional**:
```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('SERPER_API_KEY'), reason="API key not set")
def test_serper_search_real_api():
    tool = get_tool('serper_search')
    result = tool.run("test query")
    assert result is not None
```

---

## Documentation

### Tool Catalog (docs/tools/README.md)

```markdown
# Available Tools

## serper_search
**Description**: Google search via Serper API
**Setup**: https://serper.dev
**Env var**: `SERPER_API_KEY`
**Example**:
```yaml
tools: [serper_search]
prompt: "Search for information about {topic}"
```

## calculator
**Description**: Perform math calculations
**Setup**: None (built-in)
**Example**:
```yaml
tools: [calculator]
prompt: "Calculate: {expression}"
```

[More tools...]
```

---

## References

- 12-Factor App (Config): https://12factor.net/config
- LangChain Tools: https://python.langchain.com/docs/modules/agents/tools/
- Serper API: https://serper.dev

---

## Notes

The tool registry is intentionally simple for v0.1. It prioritizes:
1. Security (no credentials in config)
2. Simplicity (just reference by name)
3. Validation (check at parse time)

Advanced features (custom tools, tool composition) can come later once we understand real usage patterns.

**Key insight**: Most users need the same 10-20 tools. Pre-registering them is simpler than building a complex tool definition system.

---

## Implementation Details

**Status**: ✅ Implemented in v0.1
**Related Tasks**: T-008 (Tool Registry)
**Date Implemented**: 2026-01-26

### T-008: Tool Registry Implementation

**File**: `src/configurable_agents/tools/registry.py` (180 lines)

**Factory-Based Lazy Loading**:
```python
class ToolRegistry:
    def __init__(self):
        self._factories = {
            "serper_search": self._create_serper_tool,
            # Future tools added here
        }
        self._instances = {}  # Cache

    def get_tool(self, name: str) -> BaseTool:
        """Get tool by name (lazy instantiation)"""
        if name not in self._factories:
            raise ToolNotFoundError(...)

        if name not in self._instances:
            self._instances[name] = self._factories[name]()

        return self._instances[name]
```

**Global Registry (Convenience)**:
```python
# User-facing API
from configurable_agents.tools import get_tool, list_tools

search = get_tool("serper_search")
results = search.run("Python programming")
```

**Tool Implementation** (Serper):
```python
# tools/serper.py
class SerperSearchTool(BaseTool):
    name = "serper_search"
    description = "Search the web using Google via Serper API"

    def _run(self, query: str) -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ValueError("SERPER_API_KEY not set")

        # Call Serper API
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key},
            json={"q": query}
        )
        return response.json()
```

**Error Handling**:
- Missing API key → clear error message
- Tool not found → suggestions for similar names
- API failures → wrapped with context

**Test Coverage**: 37 tests (22 registry + 15 serper)

**Production Validation** (T-017):
- article_writer.yaml uses serper_search successfully
- Real API integration tested
- Error scenarios validated (missing key, API timeout)

---

## Superseded By

None (current)
