# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added - T-011: Node Executor ✅

**Commit**: T-011: Node executor - Execute nodes with LLM + tools

**What Was Done**:
- Implemented node executor that integrates all Phase 2 components
- Input mapping resolution from state
- Prompt template resolution with {state.field} preprocessing helper
- Tool loading and binding to LLM
- LLM configuration merging (node-level overrides global)
- Structured output enforcement using Pydantic models
- Copy-on-write state updates (immutable pattern)
- Comprehensive error handling with NodeExecutionError
- 23 comprehensive tests covering all scenarios
- Total: 367 tests passing (up from 344)

**Node Executor Features**:
- ✅ Execute workflow nodes with LLM + tools
- ✅ Resolve input mappings: `{local: "{template}"}` from state
- ✅ Resolve prompts with variable substitution
- ✅ Handle {state.field} syntax via preprocessing (_strip_state_prefix)
- ✅ Load and bind tools to LLM (serper_search, etc.)
- ✅ Merge node-level and global LLM configurations
- ✅ Enforce output schema with Pydantic validation
- ✅ Update state immutably (copy-on-write pattern)
- ✅ Retry logic via LLM provider (max_retries from config)
- ✅ Logging at INFO level (execution success/failure)
- ✅ Wrap all errors in NodeExecutionError with node_id context

**Files Created**:
```
src/configurable_agents/core/
└── node_executor.py (execute_node, NodeExecutionError, _strip_state_prefix)

tests/core/
└── test_node_executor.py (23 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.core import (
    execute_node,              # Main execution function
    NodeExecutionError,        # Error type for node failures
)

# Execute a node
updated_state = execute_node(
    node_config,      # NodeConfig
    state,            # Current workflow state (Pydantic model)
    global_config,    # Optional[GlobalConfig]
)
# Returns: Updated state (new Pydantic instance)
```

**Design Decisions**:
- Copy-on-write state updates: Returns new state instance (immutable pattern)
- Input mapping semantics: Template strings resolved against state
- State prefix preprocessing: `_strip_state_prefix` converts {state.X} → {X}
  - TODO T-011.1: Update template resolver to handle {state.X} natively
- Error wrapping: All failures wrapped in NodeExecutionError with context
- Retry delegation: LLM provider handles retries (max_retries from global config)
- Logging strategy: INFO for success/failure, DEBUG for detailed steps

**Known Technical Debt**:
- **T-011.1** (Future): Template resolver should handle {state.field} syntax natively
  - Current: Validator (T-004) and SPEC.md use {state.field} syntax
  - Current: Template resolver (T-010) expects {field} without prefix
  - Workaround: `_strip_state_prefix` helper preprocesses prompts/inputs
  - Impact: Low (preprocessing works fine, just not elegant)
  - Resolution: Update template resolver in v0.2+ to accept both syntaxes

**Progress**:
- Phase 2 (Core Execution): 4/6 tasks complete (67%)
- Overall v0.1 progress: 12/20 tasks complete (60%)

---

### Added - T-010: Prompt Template Resolver ✅

**Commit**: T-010: Prompt template resolver - Variable substitution

**What Was Done**:
- Implemented prompt template resolution with {variable} placeholder support
- Input mappings override state fields (explicit precedence)
- Support for nested state access ({metadata.author}, {metadata.flags.level})
- Comprehensive error handling with "Did you mean?" suggestions
- Edit distance algorithm for typo detection (max 2 edits)
- Automatic type conversion (int, bool, etc. → string)
- 44 comprehensive tests covering all scenarios
- Total: 344 tests passing (up from 300)

**Template Resolver Features**:
- ✅ Resolve {variable} placeholders from inputs or state
- ✅ Input mappings take priority over state fields
- ✅ Nested state access: {metadata.author}, {flags.enabled}
- ✅ Deeply nested access (3+ levels): {metadata.flags.level}
- ✅ Multiple variables in single template
- ✅ Type conversion (non-string values converted to strings)
- ✅ Empty templates handled gracefully
- ✅ Templates without variables returned unchanged
- ✅ Fail-fast with helpful error messages
- ✅ "Did you mean X?" suggestions for typos (edit distance ≤ 2)

**Files Created**:
```
src/configurable_agents/core/
└── template.py (prompt template resolver)

tests/core/
└── test_template.py (44 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.core import (
    resolve_prompt,             # Main resolution function
    extract_variables,          # Extract {variable} references
    TemplateResolutionError,    # Resolution error exception
)

# Resolve prompt template
resolved = resolve_prompt(
    prompt_template="Hello {name}, discuss {topic}",
    inputs={"name": "Alice"},  # Node-level inputs (override state)
    state=state_model,         # Workflow state (Pydantic model)
)
# Returns: "Hello Alice, discuss AI Safety"

# Extract variable references
variables = extract_variables("Author: {metadata.author}")
# Returns: {"metadata.author"}
```

**Error Handling**:
```python
# Missing variable
>>> resolve_prompt("Hello {unknown}", {}, state)
TemplateResolutionError: Variable 'unknown' not found in inputs or state
Suggestion: Did you mean 'topic'?
Available inputs: []
Available state fields: ['topic', 'score']

# Nested variable not found
>>> resolve_prompt("{metadata.author}", {}, state)
TemplateResolutionError: Variable 'metadata.author' not found in inputs or state
Available inputs: []
Available state fields: ['topic', 'score']
```

**How to Verify**:

1. **Test template resolver**:
   ```bash
   pytest tests/core/test_template.py -v
   # Expected: 44 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v -m "not integration"
   # Expected: 344 passed (44 template + 300 existing)
   ```

3. **Use template resolver**:
   ```python
   from configurable_agents.core import resolve_prompt
   from pydantic import BaseModel

   class State(BaseModel):
       topic: str
       score: int

   state = State(topic="AI Safety", score=95)
   inputs = {"name": "Alice"}

   # Simple resolution
   result = resolve_prompt("Hello {name}", inputs, state)
   assert result == "Hello Alice"

   # State field
   result = resolve_prompt("Topic: {topic}", {}, state)
   assert result == "Topic: AI Safety"

   # Input overrides state
   inputs = {"topic": "Robotics"}
   result = resolve_prompt("Topic: {topic}", inputs, state)
   assert result == "Topic: Robotics"
   ```

**What to Expect**:

- ✅ Prompt templates resolve variables from inputs and state
- ✅ Input mappings override state fields (explicit precedence)
- ✅ Nested state access works (dot notation)
- ✅ Multiple variables in single template
- ✅ Type conversion automatic (int → "95", bool → "True")
- ✅ Helpful error messages with suggestions
- ✅ "Did you mean X?" for typos (edit distance ≤ 2)
- ✅ Available variables listed in error messages
- ✅ Fast and efficient (regex-based extraction)

**Design Decisions**:

1. **Input priority**: Inputs override state (node-level control)
2. **Dot notation**: Nested access via {a.b.c} syntax
3. **Type conversion**: Automatic str() conversion for all values
4. **Fail-fast**: Error on first missing variable encountered
5. **Edit distance**: Max 2 edits for suggestions (Levenshtein distance)
6. **Simple syntax**: Only {variable} supported (no format strings yet)
7. **No escaping**: Literal braces not supported in v0.1 (can add if needed)

**Phase 2 Progress**:
With T-010 done, **Phase 2 (Core Execution) is 3/6 complete**:
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ⏳ docs/TASKS.md (T-010 marked DONE, progress updated to 11/20)
- ⏳ docs/DISCUSSION.md (status updated)
- ⏳ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-010: Prompt template resolver - Variable substitution

- Implemented prompt template resolution with {variable} placeholders
  - resolve_prompt(template, inputs, state) - Main resolution function
  - extract_variables(template) - Extract variable references
  - Input mappings override state fields (explicit precedence)
  - Fail loudly if variable not found

- Support for nested state access
  - Dot notation: {metadata.author}, {metadata.flags.level}
  - Works with Pydantic models and dicts
  - Deeply nested access (3+ levels)
  - Automatic type conversion (int, bool → string)

- Comprehensive error handling
  - \"Did you mean?\" suggestions for typos (edit distance ≤ 2)
  - Available inputs and state fields listed
  - Clear error messages with context
  - TemplateResolutionError exception

- Created 44 comprehensive tests
  - Simple variable resolution (inputs, state)
  - Input override priority
  - Nested state access (1 level, 3+ levels)
  - Multiple variables, type conversion
  - Error cases with suggestions
  - Helper functions (extract, get_nested_value)
  - Edit distance algorithm
  - Integration scenarios

Verification:
  pytest -v -m 'not integration'
  Expected: 344 passed (44 template + 300 existing)

Progress: 11/20 tasks (55%) - Phase 2 (Core Execution) 3/6 complete
Next: T-011 (Node Executor)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Added - T-009: LLM Provider ✅

**Commit**: T-009: LLM provider - Google Gemini integration

**What Was Done**:
- Implemented LLM provider factory with Google Gemini support
- Created structured output calling with Pydantic schema enforcement
- Comprehensive error handling and retry logic
- Configuration merging (node-level overrides global settings)
- API key validation with helpful setup instructions
- 32 comprehensive tests covering all scenarios
- Total: 300 tests passing (up from 268)

**LLM Provider Features**:
- ✅ Create LLM from config: `create_llm(config) -> BaseChatModel`
- ✅ Structured output calling: `call_llm_structured(llm, prompt, OutputModel)`
- ✅ Configuration merging: `merge_llm_config(node_config, global_config)`
- ✅ Provider validation (v0.1: Google Gemini only)
- ✅ Model defaults (gemini-1.5-flash)
- ✅ Temperature and max_tokens configuration
- ✅ Automatic retry on validation failures
- ✅ Exponential backoff on rate limits
- ✅ Tool binding support
- ✅ Fail loudly with helpful error messages

**Google Gemini Integration**:
- ✅ ChatGoogleGenerativeAI wrapper
- ✅ Reads GOOGLE_API_KEY from environment
- ✅ Supports multiple models (gemini-1.5-flash, gemini-1.5-pro, gemini-pro, gemini-pro-vision)
- ✅ Clear error messages with API key setup instructions
- ✅ Configuration validation
- ✅ Integration tests (marked as slow/integration)

**Files Created**:
```
src/configurable_agents/llm/
├── provider.py (LLM factory and core functionality)
├── google.py (Google Gemini implementation)
└── __init__.py (public API exports)

tests/llm/
├── __init__.py
├── test_provider.py (19 provider tests)
└── test_google.py (13 Google tests + 2 integration tests)
```

**Public API**:
```python
from configurable_agents.llm import (
    create_llm,              # Create LLM from config
    call_llm_structured,     # Call LLM with structured output
    merge_llm_config,        # Merge node and global configs
    LLMConfigError,          # Configuration error exception
    LLMProviderError,        # Provider not supported exception
    LLMAPIError,             # API call failure exception
)

# Create LLM
config = LLMConfig(provider="google", model="gemini-pro", temperature=0.7)
llm = create_llm(config)

# Call with structured output
class Article(BaseModel):
    title: str
    content: str

result = call_llm_structured(llm, "Write an article about AI", Article)
print(result.title)
```

**Error Handling**:
```python
# Missing API key
>>> create_llm(LLMConfig(provider="google"))
LLMConfigError: LLM configuration failed for provider 'google':
GOOGLE_API_KEY environment variable not set

Suggestion: Set the environment variable: GOOGLE_API_KEY
Get your API key from: https://ai.google.dev/
Example: export GOOGLE_API_KEY=your-api-key-here

# Unsupported provider
>>> create_llm(LLMConfig(provider="openai"))
LLMProviderError: LLM provider 'openai' is not supported.
Supported providers: google

Note: v0.1 only supports Google Gemini. Additional providers coming in v0.2+ (8-12 weeks).

# Retry on rate limit
# Automatically retries with exponential backoff (1s, 2s, 4s, etc.)

# Retry on validation error
# Clarifies prompt and retries up to max_retries times
```

**How to Verify**:

1. **Test LLM provider**:
   ```bash
   pytest tests/llm/test_provider.py -v
   # Expected: 19 passed
   ```

2. **Test Google Gemini**:
   ```bash
   pytest tests/llm/test_google.py -v -m "not integration"
   # Expected: 13 passed
   ```

3. **Run full test suite**:
   ```bash
   pytest -v -m "not integration"
   # Expected: 300 passed (32 llm + 268 existing)
   ```

4. **Use LLM provider**:
   ```python
   import os
   os.environ["GOOGLE_API_KEY"] = "your-key-here"

   from configurable_agents.llm import create_llm, call_llm_structured
   from configurable_agents.config import LLMConfig
   from pydantic import BaseModel

   # Create LLM
   config = LLMConfig(model="gemini-1.5-flash", temperature=0.7)
   llm = create_llm(config)

   # Call with structured output
   class Greeting(BaseModel):
       message: str

   result = call_llm_structured(llm, "Say hello", Greeting)
   print(result.message)
   ```

**What to Expect**:

- ✅ LLM instances created from config
- ✅ Structured outputs with Pydantic validation
- ✅ Node config overrides global config
- ✅ Automatic retries on failures
- ✅ Helpful error messages with setup instructions
- ✅ Tool binding for LLM calls
- ✅ Rate limit handling with exponential backoff
- ⚠️ Only Google Gemini supported in v0.1 (more providers in v0.2+)
- ⚠️ Integration tests require GOOGLE_API_KEY

**Design Decisions**:

1. **Factory pattern**: LLMs created via factory functions for flexibility
2. **Config merging**: Node-level settings override global (explicit precedence)
3. **Fail loudly**: Clear errors with actionable messages
4. **Retry logic**: Automatic retry on validation errors and rate limits
5. **Structured outputs**: Pydantic schema binding for type enforcement
6. **Provider abstraction**: Easy to add providers in future versions
7. **Environment-based config**: API keys from environment variables

**Phase 2 Progress**:
With T-009 done, **Phase 2 (Core Execution) is 2/6 complete**:
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ⏳ docs/TASKS.md (T-009 marked DONE, progress updated to 10/20)
- ⏳ docs/DISCUSSION.md (status updated)
- ⏳ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-009: LLM provider - Google Gemini integration

- Implemented LLM provider factory for creating LLM instances
  - create_llm(config) - Create LLM from config
  - call_llm_structured(llm, prompt, OutputModel) - Structured outputs
  - merge_llm_config(node, global) - Config merging
  - Fail loudly if provider not supported or API key missing

- Implemented Google Gemini LLM provider
  - ChatGoogleGenerativeAI integration
  - Reads GOOGLE_API_KEY from environment
  - Supports gemini-1.5-flash, gemini-1.5-pro, gemini-pro models
  - Temperature and max_tokens configuration
  - Clear error messages with setup instructions

- Structured output calling with retry logic
  - Pydantic schema binding for type enforcement
  - Automatic retry on ValidationError (up to max_retries)
  - Exponential backoff on rate limits
  - Clarified prompts on validation failures
  - Tool binding support

- Configuration merging
  - Node-level LLM config overrides global config
  - Explicit precedence rules
  - Handles None configs gracefully

- Created 32 comprehensive tests
  - 19 provider tests (factory, merging, structured calls, retries)
  - 13 Google tests (creation, validation, configuration)
  - 2 integration tests (marked with @pytest.mark.integration)

Verification:
  pytest -v -m 'not integration'
  Expected: 300 passed (32 llm + 268 existing)

Progress: 10/20 tasks (50%) - Phase 2 (Core Execution) 2/6 complete
Next: T-010 (Prompt Template Resolver)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Added - T-008: Tool Registry ✅

**Commit**: T-008: Tool registry - Web search tool integration

**What Was Done**:
- Implemented centralized tool registry for loading tools by name
- Created registry-based architecture with factory functions for lazy loading
- Implemented `serper_search` web search tool using Google Serper API
- Comprehensive error handling with helpful messages
- Added langchain-community dependency for tool integrations
- 37 comprehensive tests covering all scenarios
- Total: 268 tests passing (up from 231)

**Tool Registry Features**:
- ✅ Get tool by name: `get_tool(name) -> BaseTool`
- ✅ List available tools: `list_tools() -> list[str]`
- ✅ Check tool exists: `has_tool(name) -> bool`
- ✅ Register custom tools: `register_tool(name, factory)`
- ✅ Lazy loading - tools created on demand
- ✅ API key validation from environment variables
- ✅ Fail loudly with helpful errors if tool not found
- ✅ Fail loudly with setup instructions if API key missing
- ✅ Factory-based design for extensibility

**Serper Search Tool**:
- ✅ Web search using Google Search via Serper API
- ✅ Reads SERPER_API_KEY from environment
- ✅ Clear error messages with setup instructions
- ✅ LangChain Tool wrapper for compatibility
- ✅ Helpful description for LLM tool selection

**Files Created**:
```
src/configurable_agents/tools/
├── registry.py (tool registry with global instance)
└── serper.py (Serper web search implementation)

tests/tools/
├── __init__.py
├── test_registry.py (22 registry tests)
└── test_serper.py (15 serper tests + 2 integration tests)
```

**Public API**:
```python
from configurable_agents.tools import get_tool, list_tools, has_tool

# List available tools
tools = list_tools()  # ['serper_search']

# Check if tool exists
if has_tool("serper_search"):
    # Get tool instance
    search = get_tool("serper_search")
    results = search.run("Python programming")
```

**Error Handling**:
```python
# Tool not found
>>> get_tool("unknown_tool")
ToolNotFoundError: Tool 'unknown_tool' not found in registry.
Available tools: serper_search
Suggestion: Check the tool name for typos. Tools are case-sensitive.

# Missing API key
>>> get_tool("serper_search")
ToolConfigError: Tool 'serper_search' configuration failed:
SERPER_API_KEY environment variable not set

Set the environment variable: SERPER_API_KEY
Example: export SERPER_API_KEY=your-api-key-here
```

**How to Verify**:

1. **Test tool registry**:
   ```bash
   pytest tests/tools/test_registry.py -v
   # Expected: 22 passed
   ```

2. **Test serper tool**:
   ```bash
   pytest tests/tools/test_serper.py -v -m "not integration"
   # Expected: 15 passed
   ```

3. **Run full test suite**:
   ```bash
   pytest -v -m "not integration"
   # Expected: 268 passed (37 new + 231 existing)
   ```

4. **Use tool registry**:
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

**What to Expect**:

- ✅ Tool registry loads tools by name from config
- ✅ Serper search tool works with valid API key
- ✅ Helpful error messages for missing tools or API keys
- ✅ Tools are LangChain BaseTool instances
- ✅ Registry is extensible for custom tools
- ✅ Lazy loading - tools created only when requested
- ⚠️ Only `serper_search` available in v0.1 (more tools in v0.2+)

**Design Decisions**:

1. **Factory pattern**: Tools created via factory functions for lazy loading
2. **Global registry**: Single global instance for convenience
3. **Fail loudly**: Clear errors with actionable messages
4. **LangChain integration**: Tools use LangChain BaseTool interface
5. **Environment-based config**: API keys from environment variables
6. **Case-sensitive names**: Tool names match config exactly

**Phase 2 Progress**:
With T-008 done, **Phase 2 (Core Execution) is 1/6 complete**:
- ✅ T-008: Tool Registry
- ⏳ T-009: LLM Provider (Google Gemini)
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-008 marked DONE, progress updated to 9/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Dependencies Added**:
- `langchain-community>=0.0.20` (for GoogleSerperAPIWrapper)

**Git Commit Command**:
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
Next: T-009 (LLM Provider - Google Gemini)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Added - T-007: Output Schema Builder ✅

**Commit**: T-007: Output schema builder - Type-enforced LLM outputs

**What Was Done**:
- Implemented dynamic Pydantic model generation from OutputSchema configs
- Enables type-enforced LLM responses
- Supports simple outputs (single type wrapped in 'result' field)
- Supports object outputs (multiple fields)
- Supports all type system types (basic, collections)
- Includes field descriptions to help LLM understand what to return
- 29 comprehensive tests covering all scenarios
- Total: 231 tests passing (up from 202)

**Output Builder Features**:
- ✅ Build runtime Pydantic BaseModel from output_schema
- ✅ Simple outputs (str, int, float, bool) - wrapped in 'result' field
- ✅ Object outputs (multiple fields)
- ✅ Collection types (list, dict, list[T], dict[K,V])
- ✅ Type validation enforced by Pydantic
- ✅ All output fields required (LLM must provide them)
- ✅ Field descriptions preserved in models
- ✅ Model naming: Output_{node_id}
- ✅ Fail-fast error handling with clear messages
- ✅ Error messages include node_id for context
- ⚠️ Nested objects not yet supported (can add if needed)

**Files Created**:
```
src/configurable_agents/core/
└── output_builder.py (dynamic output model builder)

tests/core/
└── test_output_builder.py (29 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.core import build_output_model, OutputBuilderError

# Build dynamic output model
OutputModel = build_output_model(output_schema, node_id="write")

# Create instance (simple output)
output = OutputModel(result="Generated article")

# Create instance (object output)
output = OutputModel(article="...", word_count=500)
```

**How to Verify**:

1. **Test output builder**:
   ```bash
   pytest tests/core/test_output_builder.py -v
   # Expected: 29 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 231 passed (29 new + 202 existing)
   ```

3. **Use output builder**:
   ```python
   from configurable_agents.config import OutputSchema, OutputSchemaField
   from configurable_agents.core import build_output_model

   # Simple output
   schema = OutputSchema(type="str", description="Article text")
   OutputModel = build_output_model(schema, "write")
   output = OutputModel(result="Hello world")
   assert output.result == "Hello world"

   # Object output
   schema = OutputSchema(
       type="object",
       fields=[
           OutputSchemaField(name="article", type="str", description="Article text"),
           OutputSchemaField(name="word_count", type="int", description="Word count"),
       ]
   )
   OutputModel = build_output_model(schema, "write")
   output = OutputModel(article="Test article", word_count=100)
   assert output.article == "Test article"
   assert output.word_count == 100
   ```

**What to Expect**:

- ✅ Dynamic Pydantic models generated from output schemas
- ✅ Simple outputs wrapped in 'result' field
- ✅ Object outputs with explicit fields
- ✅ All type system types supported (basic, collections)
- ✅ Type validation enforced (ValidationError if wrong type)
- ✅ All fields required (ValidationError if missing)
- ✅ Field descriptions included in model schema (helps LLM)
- ✅ Clear error messages with node_id context
- ⚠️ Nested objects not yet supported (use dicts instead)

**Example Error Messages**:

```python
# Missing output schema
OutputBuilderError: Node 'test': output_schema is required

# Invalid type
OutputBuilderError: Node 'write': Invalid output type 'unknown_type': ...

# Missing required field (Pydantic)
ValidationError: 1 validation error for Output_write
result
  Field required [type=missing, input_value={}, input_type=dict]

# Wrong type (Pydantic)
ValidationError: 1 validation error for Output_write
result
  Input should be a valid string [type=string_type, input_value=123, input_type=int]

# Nested objects not supported
OutputBuilderError: Node 'test': Nested objects in output schema not yet supported.
Field 'metadata' has type 'object'. Use basic types, lists, or dicts instead.
```

**Design Decisions**:

1. **Simple outputs wrapped**: Single-field outputs use 'result' as field name for consistency
2. **All fields required**: LLM must provide all output fields (no optional)
3. **Model naming**: Output_{node_id} for clarity
4. **No nested objects**: Keep v0.1 simple, can add if needed in future
5. **Descriptions preserved**: Help LLM understand what to return
6. **Fail-fast**: Clear OutputBuilderError for builder-specific issues

**Phase 1 Complete**:
With T-007 done, **Phase 1 (Foundation) is now complete** (8/8 tasks):
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System
- ✅ T-006: State Schema Builder
- ✅ T-007: Output Schema Builder

**Next Phase**: Phase 2 - Core Execution (T-008: Tool Registry)

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-007 marked DONE, progress updated to 8/20, Phase 1 complete)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-007: Output schema builder - Type-enforced LLM outputs

- Implemented dynamic Pydantic model generation from OutputSchema
- Simple outputs wrapped in 'result' field (str, int, float, bool)
- Object outputs with multiple fields
- Supports all type system types (basic, collections)
- Type validation enforced by Pydantic
- All output fields required (LLM must provide them)
- Field descriptions preserved to help LLM

- Created 29 comprehensive tests
  - Simple outputs (str, int, float, bool)
  - Object outputs (multiple fields, all types)
  - Collection types (list, dict, typed variants)
  - Object with list/dict fields
  - Model naming and error handling
  - Round-trip serialization
  - Validation enforcement

Verification:
  pytest -v
  Expected: 231 passed (29 output builder + 202 existing)

Progress: 8/20 tasks (40%) - Phase 1 (Foundation) COMPLETE!
Next: T-008 (Tool Registry) - Phase 2 start

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Added - T-006: State Schema Builder ✅

**Commit**: T-006: State schema builder - Dynamic Pydantic models

**What Was Done**:
- Implemented dynamic Pydantic model generation from StateSchema configs
- Supports all type system types (basic, collections, nested objects)
- Recursive nested object handling with meaningful model names
- Required/optional fields with proper validation
- Default values preserved and enforced
- Field descriptions included in generated models
- 30 comprehensive tests covering all scenarios
- Total: 202 tests passing (up from 172)

**State Builder Features**:
- ✅ Build runtime Pydantic BaseModel from config
- ✅ Basic types (str, int, float, bool)
- ✅ Collection types (list, dict, list[T], dict[K,V])
- ✅ Nested objects (1 level deep)
- ✅ Deeply nested objects (3+ levels)
- ✅ Required field validation
- ✅ Optional fields (default to None)
- ✅ Default values
- ✅ Field descriptions preserved
- ✅ Fail-fast error handling with clear messages
- ✅ No redundant validation (leverages T-004 validator)

**Files Created**:
```
src/configurable_agents/core/
└── state_builder.py (dynamic Pydantic model builder)

tests/core/
├── __init__.py
└── test_state_builder.py (30 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.core import build_state_model, StateBuilderError

# Build dynamic state model
StateModel = build_state_model(state_config)

# Create state instance
state = StateModel(topic="AI Safety", score=95)
```

**How to Verify**:

1. **Test state builder**:
   ```bash
   pytest tests/core/test_state_builder.py -v
   # Expected: 30 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 202 passed (30 new + 172 existing)
   ```

3. **Use state builder**:
   ```python
   from configurable_agents.config import StateSchema, StateFieldConfig
   from configurable_agents.core import build_state_model

   # Define state config
   state_config = StateSchema(
       fields={
           "topic": StateFieldConfig(type="str", required=True),
           "score": StateFieldConfig(type="int", default=0),
           "tags": StateFieldConfig(type="list[str]", default=[]),
           "metadata": StateFieldConfig(
               type="object",
               required=False,
               schema={"author": "str", "timestamp": "int"},
           ),
       }
   )

   # Build model
   StateModel = build_state_model(state_config)

   # Create instance (minimal)
   state1 = StateModel(topic="AI Safety")
   assert state1.topic == "AI Safety"
   assert state1.score == 0
   assert state1.tags == []
   assert state1.metadata is None

   # Create instance (full)
   state2 = StateModel(
       topic="AI Safety",
       score=95,
       tags=["ai", "safety"],
       metadata={"author": "Alice", "timestamp": 1234567890},
   )
   assert state2.metadata.author == "Alice"
   assert state2.metadata.timestamp == 1234567890
   ```

**What to Expect**:

- ✅ Dynamic Pydantic models generated from configs
- ✅ All type system types supported (basic, collections, nested objects)
- ✅ Required fields enforced (ValidationError if missing)
- ✅ Optional fields default to None
- ✅ Default values work correctly
- ✅ Field descriptions included in model schema
- ✅ Nested objects have meaningful names (WorkflowState_metadata, etc.)
- ✅ Type validation enforced by Pydantic
- ✅ Clear error messages for invalid configs

**Example Error Messages**:

```python
# Missing required field
ValidationError: 1 validation error for WorkflowState
topic
  Field required [type=missing, input_value={}, input_type=dict]

# Wrong type
ValidationError: 1 validation error for WorkflowState
score
  Input should be a valid integer [type=int_type, input_value='not_a_number', input_type=str]

# Object without schema
StateBuilderError: Field 'metadata' has type 'object' but no 'schema' defined

# Empty nested schema
StateBuilderError: Field 'data' has type 'object' with empty schema
```

**Design Decisions**:

1. **Model naming**: All models named `WorkflowState` for readability (not hashes)
2. **Nested model naming**: Uses descriptive names like `WorkflowState_metadata_flags`
3. **No redundant validation**: Assumes config already validated by T-004
4. **Fail-fast**: Clear StateBuilderError for builder-specific issues
5. **Supports both schema formats**:
   - Simple: `{"name": "str", "age": "int"}`
   - Full: `{"name": {"type": "str", "required": true}}`

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-006 marked DONE, progress updated to 7/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-006: State schema builder - Dynamic Pydantic models

- Implemented dynamic Pydantic model generation from StateSchema
- Supports all type system types (basic, collections, nested objects)
- Recursive nested object handling with meaningful names
- Required/optional fields, defaults, descriptions
- No redundant validation (leverages T-004)
- Fail-fast error handling

- Created 30 comprehensive tests
  - Basic types (str, int, float, bool)
  - Collection types (list, dict, list[T], dict[K,V])
  - Nested objects (1 level and 3+ levels deep)
  - Required/optional/default fields
  - Field descriptions
  - Error handling
  - Model reuse

Verification:
  pytest -v
  Expected: 202 passed (30 core + 172 existing)

Progress: 7/20 tasks (35%) - Foundation phase 7/7 complete!
Next: T-007 (Output Schema Builder)"
```

---

### Added - T-004.5: Runtime Feature Gating ✅

**Commit**: T-004.5: Runtime feature gating - Version checks

**What Was Done**:
- Implemented runtime feature gating to reject unsupported v0.2+ and v0.3+ features
- Hard blocks for incompatible features (conditional routing)
- Soft blocks with warnings for future features (optimization, MLFlow)
- Helpful error messages with version timelines and workarounds
- Feature support query API
- 19 comprehensive tests for all feature gates
- Total: 172 tests passing (up from 153)

**Files Created**:
```
src/configurable_agents/runtime/
└── feature_gate.py (runtime version checks and feature gating)

tests/runtime/
├── __init__.py
└── test_feature_gate.py (19 comprehensive tests)
```

**Feature Gating System**:

**Hard Blocks (UnsupportedFeatureError)**:
- ✅ Conditional routing (edge routes) - v0.2+ feature
  - Raises error with timeline and workaround
  - Suggests using linear edges instead
  - Points to roadmap

**Soft Blocks (UserWarning)**:
- ✅ Global DSPy optimization (optimization.enabled) - v0.3+ feature
  - Warns that feature will be IGNORED
  - Workflow runs without optimization
- ✅ Node-level optimization (node.optimize.enabled) - v0.3+ feature
  - Warns per-node that optimization ignored
- ✅ MLFlow observability (config.observability.mlflow) - v0.2+ feature
  - Warns that only console logging available
  - MLFlow tracking ignored

**Supported in v0.1**:
- ✅ Basic logging (config.observability.logging)
- ✅ Linear workflows
- ✅ All core features (state, nodes, LLM, tools)

**How to Verify**:

1. **Test feature gates**:
   ```bash
   pytest tests/runtime/test_feature_gate.py -v
   # Expected: 19 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 172 passed (19 runtime + 153 existing)
   ```

3. **Use feature gating**:
   ```python
   from configurable_agents.config import parse_config_file, WorkflowConfig
   from configurable_agents.runtime import validate_runtime_support, UnsupportedFeatureError

   # Load config
   config_dict = parse_config_file("workflow.yaml")
   config = WorkflowConfig(**config_dict)

   # Check runtime support (raises if unsupported features)
   try:
       validate_runtime_support(config)
       print("✅ Config is compatible with v0.1 runtime")
   except UnsupportedFeatureError as e:
       print(f"❌ {e}")
       print(f"   Available in: {e.available_in}")
       print(f"   Timeline: {e.timeline}")
       print(f"   Workaround: {e.workaround}")
   ```

4. **Query feature support**:
   ```python
   from configurable_agents.runtime import check_feature_support

   # Check if a feature is supported
   result = check_feature_support("Conditional routing (if/else)")
   print(f"Supported: {result['supported']}")
   print(f"Available in: {result['version']}")
   print(f"Timeline: {result['timeline']}")
   ```

**What to Expect**:

- ✅ Configs with v0.2+ features are rejected at runtime with clear errors
- ✅ Configs with v0.3+ features trigger warnings but still run (degraded mode)
- ✅ Error messages include version info, timeline, and workarounds
- ✅ Valid v0.1 configs pass without errors or warnings
- ✅ Feature support can be queried programmatically

**Example Error Messages**:

```python
# Hard block - conditional routing
UnsupportedFeatureError: Feature 'Conditional routing (edge routes)' is not supported in v0.1
Available in: v0.2
Estimated timeline: 8-12 weeks from initial release

Workaround: Use linear edges (from/to) instead. For decision logic, create multiple separate workflows and chain them externally.

See roadmap: docs/PROJECT_VISION.md

# Soft block - optimization
UserWarning: DSPy optimization (optimization.enabled=true) is not supported in v0.1.
This setting will be IGNORED. Available in: v0.3 (12-16 weeks from initial release).
Your workflow will run without optimization. See docs/PROJECT_VISION.md for roadmap.
```

**Public API**:
```python
# From configurable_agents.runtime

from configurable_agents.runtime import (
    UnsupportedFeatureError,      # Exception for hard blocks
    validate_runtime_support,      # Main validation function
    get_supported_features,        # Get feature list
    check_feature_support,         # Check specific feature
)
```

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-004.5 marked DONE, progress updated to 5/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-004.5: Runtime feature gating - Version checks

- Implemented feature gating for v0.2+ and v0.3+ features
  - Hard blocks: Conditional routing (UnsupportedFeatureError)
  - Soft blocks: Optimization, MLFlow (UserWarning)
  - Clear error messages with timelines and workarounds

- Feature support query API
  - get_supported_features() - list all features
  - check_feature_support(name) - check specific feature
  - Returns version, timeline, support status

- Comprehensive error messages
  - Feature name and version when available
  - Timeline estimate (8-12 weeks, 12-16 weeks, etc.)
  - Workarounds for v0.1
  - Links to roadmap documentation

- Created 19 comprehensive tests
  - Valid v0.1 configs pass
  - Conditional routing blocked (hard)
  - Optimization warned (soft)
  - MLFlow observability warned (soft)
  - Multiple feature combinations
  - Feature query API

Verification:
  pytest -v
  Expected: 172 passed (19 runtime + 153 existing)

Progress: 5/20 tasks (25%) - Foundation phase
Next: T-005 (Type System - mostly done in T-003)"
```

---

### Added - T-005: Type System ✅

**Commit**: T-005: Type system - Formal closure (implemented in T-003)

**What Was Done**:
- Formally closed T-005 by documenting existing type system implementation
- Type system was already implemented as part of T-003 (Config Schema)
- 31 comprehensive tests already passing
- All acceptance criteria met

**Type System Features**:
- ✅ Parse basic types: `str`, `int`, `float`, `bool`
- ✅ Parse collection types: `list`, `dict`, `list[str]`, `dict[str, int]`
- ✅ Parse nested object types: `object` (with schema in StateFieldConfig)
- ✅ Convert type strings to Python types
- ✅ Validate type strings (with TypeParseError for invalid types)
- ✅ Support type descriptions (via StateFieldConfig.description field)
- ✅ Comprehensive error messages for invalid types

**Files** (created in T-003):
```
src/configurable_agents/config/
└── types.py (type parsing and validation utilities)

tests/config/
└── test_types.py (31 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.config.types import (
    TypeParseError,              # Exception for invalid types
    parse_type_string,           # Parse type string to dict
    validate_type_string,        # Validate type string
    get_python_type,             # Convert to Python type
)
```

**How to Verify**:

1. **Test type system**:
   ```bash
   pytest tests/config/test_types.py -v
   # Expected: 31 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 172 passed (no change from T-004.5)
   ```

3. **Use type parsing**:
   ```python
   from configurable_agents.config.types import parse_type_string, get_python_type

   # Parse type string
   parsed = parse_type_string("list[str]")
   print(parsed)  # {"kind": "list", "item_type": {...}, "name": "list[str]"}

   # Get Python type
   py_type = get_python_type("list[str]")
   print(py_type)  # <class 'list'>

   # Validate
   from configurable_agents.config.types import validate_type_string
   assert validate_type_string("dict[str, int]") is True
   assert validate_type_string("unknown_type") is False
   ```

**What to Expect**:

- ✅ All type strings used in configs are validated
- ✅ Invalid types raise TypeParseError with helpful messages
- ✅ Type descriptions supported at field level (StateFieldConfig)
- ✅ Type system fully integrated with Pydantic schema validation

**Note**: Files are in `config/` package (not `core/` as originally specified in task). Type descriptions are handled via `StateFieldConfig.description` field in schema.py, not in the type system itself.

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-005 marked DONE, progress updated to 6/20)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add docs/
git commit -m "T-005: Type system - Formal closure

- Type system already implemented in T-003
- 31 tests passing (parse_type_string, validate_type_string, get_python_type)
- All acceptance criteria met
- Type descriptions supported via StateFieldConfig.description

Verification:
  pytest tests/config/test_types.py -v
  Expected: 31 passed

Progress: 6/20 tasks (30%) - Foundation phase 6/7 complete
Next: T-006 (State Schema Builder)"
```

---

### Added - T-004: Config Validator ✅

**Commit**: T-004: Config validator - Comprehensive validation

**What Was Done**:
- Implemented comprehensive config validation beyond Pydantic schema checks
- Cross-reference validation (node IDs, state fields, output types)
- Graph structure validation (connectivity, reachability)
- Linear flow enforcement (v0.1 constraints: no cycles, no conditional routing)
- Fail-fast error handling with helpful suggestions
- "Did you mean...?" suggestions for typos using edit distance
- Context-aware error messages with clear guidance
- 29 comprehensive validator tests
- Total: 153 tests passing (up from 124)

**Files Created**:
```
src/configurable_agents/config/
└── validator.py (validation engine with 8 validation stages)

tests/config/
└── test_validator.py (29 comprehensive tests)
```

**Validation Features**:
- ✅ Edge reference validation (from/to point to valid nodes)
- ✅ Node output validation (outputs exist in state fields)
- ✅ Output schema alignment (schema fields match outputs list)
- ✅ Type alignment (output types match state field types)
- ✅ Prompt placeholder validation ({variable} references valid fields)
- ✅ State type validation (all type strings are valid)
- ✅ Graph structure (START/END connectivity, no orphaned nodes)
- ✅ Linear flow constraints (no cycles, no conditional routing, single entry point)

**How to Verify**:

1. **Test validation**:
   ```bash
   pytest tests/config/test_validator.py -v
   # Expected: 29 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 153 passed (18 parser + 67 schema + 31 types + 5 integration + 29 validator + 3 setup)
   ```

3. **Validate a config programmatically**:
   ```python
   from configurable_agents.config import parse_config_file, WorkflowConfig, validate_config

   # Load and parse YAML/JSON
   config_dict = parse_config_file("workflow.yaml")
   config = WorkflowConfig(**config_dict)

   # Validate (raises ValidationError if invalid)
   validate_config(config)
   print("Config is valid!")
   ```

**What to Expect**:
- ✅ Comprehensive validation catches common errors early
- ✅ Helpful error messages with context and suggestions
- ✅ "Did you mean 'process'?" for typos (edit distance ≤ 2)
- ✅ Fail-fast: stops at first error category
- ✅ Clear distinction between v0.1 features vs v0.2+ (with timeline info)
- ✅ Graph validation ensures all nodes reachable and can reach END
- ✅ Type safety: output types must match state field types
- ✅ No hidden surprises: placeholders validated at parse time

**Example Error Messages**:
```python
# Missing state field
ValidationError: Node 'process': output 'missing_field' not found in state fields
Suggestion: Add 'missing_field' to state.fields or check spelling. Available fields: ['input', 'output']

# Typo in node reference
ValidationError: Edge 0: 'to' references unknown node 'proces'
Suggestion: Did you mean 'process'?

# Cycle detected
ValidationError: Cycle detected in workflow: step1 -> step2 -> step1
Suggestion: Remove edges to break the cycle. Linear workflows cannot have loops (loops available in v0.2+)
Context: v0.1 supports linear flows only

# Conditional routing (v0.2+ feature)
ValidationError: Edge 0: Conditional routing not supported in v0.1
Suggestion: Use linear edges (from/to) instead. Conditional routing available in v0.2+ (8-12 weeks)
Context: Edge: START -> routes. See docs/PROJECT_VISION.md for roadmap
```

**Validation Stages** (fail-fast order):
1. Edge references (nodes exist)
2. Node outputs (state fields exist)
3. Output schema alignment (schema ↔ outputs)
4. Type alignment (output types ↔ state types)
5. Prompt placeholders (valid references)
6. State types (valid type strings)
7. Linear flow constraints (v0.1 specific)
8. Graph structure (connectivity)

**Public API Updated**:
```python
# From configurable_agents.config

# Validator (T-004)
from configurable_agents.config import (
    ValidationError,   # Custom exception with helpful messages
    validate_config,   # Main validation function
)

# Usage
try:
    validate_config(config)
except ValidationError as e:
    print(e)  # Includes message, context, and suggestion
```

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-004 marked DONE, progress updated to 4/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-004: Config validator - Comprehensive validation

- Implemented cross-reference validation
  - Node IDs, state fields, output types
  - Prompt placeholders, type alignment
  - 'Did you mean?' suggestions for typos

- Implemented graph validation
  - START/END connectivity
  - All nodes reachable from START
  - All nodes have path to END
  - No orphaned nodes

- Implemented linear flow enforcement (v0.1)
  - No conditional routing (v0.2+ feature)
  - No cycles in graph
  - Each node has at most one outgoing edge
  - Single entry point from START

- Fail-fast error handling
  - Stops at first error category
  - Context-aware messages
  - Helpful suggestions with alternatives

- Created 29 comprehensive tests
  - Valid config tests
  - Edge reference validation
  - Cross-reference validation
  - Type alignment validation
  - Graph structure validation
  - Linear flow constraint tests

Verification:
  pytest -v
  Expected: 153 passed (29 validator + 124 existing)

Progress: 4/20 tasks (20%) - Foundation phase
Next: T-004.5 (Runtime Feature Gating)"
```

---

## [0.1.0-dev] - 2026-01-24

### Added - T-003: Config Schema (Pydantic Models) ✅

**Commit**: T-003: Config schema - Pydantic models for Schema v1.0

**What Was Done**:
- Implemented complete type system for parsing type strings (str, int, float, bool, list, dict, list[T], dict[K,V], object)
- Created comprehensive Pydantic models for entire Schema v1.0
- Full Schema Day One: All models support features through v0.3 (ADR-009)
- 13 Pydantic models covering workflow, state, nodes, edges, optimization, config
- Type validation, field validation, cross-field validation
- Support for YAML/JSON round-trip conversion
- Created 103 new tests (31 type tests + 67 schema tests + 5 integration tests)
- Total: 124 tests passing (up from 21)

**Files Created**:
```
src/configurable_agents/config/
├── types.py (type string parsing system)
└── schema.py (13 Pydantic models for Schema v1.0)

tests/config/
├── test_types.py (31 tests for type system)
├── test_schema.py (67 tests for Pydantic models)
└── test_schema_integration.py (5 integration tests)
```

**Pydantic Models Created**:
```python
# Top-level
WorkflowConfig

# Components
FlowMetadata
StateSchema, StateFieldConfig
NodeConfig
OutputSchema, OutputSchemaField
EdgeConfig, Route, RouteCondition

# Configuration
OptimizationConfig, OptimizeConfig
LLMConfig
ExecutionConfig
GlobalConfig
ObservabilityConfig, ObservabilityMLFlowConfig, ObservabilityLoggingConfig
```

**How to Verify**:

1. **Test type system**:
   ```bash
   pytest tests/config/test_types.py -v
   # Expected: 31 passed
   ```

2. **Test Pydantic models**:
   ```bash
   pytest tests/config/test_schema.py -v
   # Expected: 67 passed
   ```

3. **Test integration (YAML → Pydantic)**:
   ```bash
   pytest tests/config/test_schema_integration.py -v
   # Expected: 5 passed
   ```

4. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 124 passed (18 parser + 3 setup + 31 types + 67 schema + 5 integration)
   ```

5. **Load and validate a config**:
   ```python
   from configurable_agents.config import parse_config_file, WorkflowConfig

   # Load YAML to dict
   config_dict = parse_config_file("workflow.yaml")

   # Parse into Pydantic model (validates structure)
   config = WorkflowConfig(**config_dict)

   # Access validated data
   print(f"Flow: {config.flow.name}")
   print(f"Nodes: {len(config.nodes)}")
   ```

**What to Expect**:
- ✅ Complete type system (str, int, float, bool, list, dict, nested)
- ✅ Full Schema v1.0 Pydantic models
- ✅ YAML/JSON configs parse into type-safe models
- ✅ Validation errors with helpful messages
- ✅ Support for v0.2/v0.3 features in schema (conditional edges, optimization)
- ✅ Round-trip: config → dict → YAML/JSON → dict → config
- ❌ No cross-reference validation yet (T-004: outputs match state, node IDs exist)
- ❌ No runtime feature gating yet (T-004.5: reject unsupported features)

**Type System Examples**:
```python
from configurable_agents.config.types import parse_type_string, get_python_type

# Parse basic types
parse_type_string("str")     # {"kind": "basic", "type": str}
parse_type_string("int")     # {"kind": "basic", "type": int}

# Parse collection types
parse_type_string("list[str]")        # {"kind": "list", "item_type": ...}
parse_type_string("dict[str, int]")   # {"kind": "dict", "key_type": ..., "value_type": ...}

# Parse object types
parse_type_string("object")  # {"kind": "object"}

# Get Python type
get_python_type("str")       # str
get_python_type("list[int]") # list
```

**Pydantic Model Examples**:
```python
from configurable_agents.config import WorkflowConfig, FlowMetadata, StateSchema

# Minimal config
config = WorkflowConfig(
    schema_version="1.0",
    flow=FlowMetadata(name="my_flow"),
    state=StateSchema(fields={"input": {"type": "str"}}),
    nodes=[...],
    edges=[...]
)

# Access validated data
config.flow.name              # "my_flow"
config.state.fields["input"]  # StateFieldConfig(type="str", ...)

# Export to dict/YAML/JSON
config_dict = config.model_dump(by_alias=True, exclude_none=True)
```

**Validation Features**:
- ✅ Schema version must be "1.0"
- ✅ Flow name cannot be empty
- ✅ State must have at least one field
- ✅ Required fields cannot have defaults
- ✅ Node IDs must be unique
- ✅ Node IDs must be valid Python identifiers (no hyphens)
- ✅ Temperature must be 0.0-1.0
- ✅ Timeouts/retries must be positive
- ✅ Output schema for type="object" must have fields
- ✅ Edges must have either 'to' or 'routes' (not both)
- ✅ Log levels validated (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Public API Updated**:
```python
# From configurable_agents.config

# Parser (T-002)
from configurable_agents.config import parse_config_file, ConfigLoader

# Types (T-003)
from configurable_agents.config import (
    parse_type_string,
    validate_type_string,
    get_python_type,
    TypeParseError
)

# Schema models (T-003)
from configurable_agents.config import (
    WorkflowConfig,
    FlowMetadata,
    StateSchema,
    StateFieldConfig,
    NodeConfig,
    OutputSchema,
    EdgeConfig,
    OptimizationConfig,
    LLMConfig,
    GlobalConfig,
    # ... and 8 more models
)
```

**Dependencies Used**:
- `pydantic >= 2.0` - Schema validation and models
- Type hints from `typing` - Python type system

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-003 marked DONE, progress updated)
- ✅ docs/DISCUSSION.md (status updated to 3/20 tasks)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-003: Config schema - Pydantic models for Schema v1.0

- Implemented type system for parsing type strings
  - Basic types: str, int, float, bool
  - Collection types: list, dict, list[T], dict[K,V]
  - Nested object types: object
  - 31 type system tests

- Created 13 Pydantic models for complete Schema v1.0
  - WorkflowConfig (top-level)
  - FlowMetadata, StateSchema, NodeConfig, EdgeConfig
  - OutputSchema with field definitions
  - OptimizationConfig, LLMConfig, ExecutionConfig, GlobalConfig
  - ObservabilityConfig for v0.2+ features
  - 67 schema model tests

- Full Schema Day One (ADR-009)
  - Schema supports all features through v0.3
  - Conditional edges (v0.2+) accepted in schema
  - Optimization config (v0.3+) accepted in schema
  - Runtime will implement features incrementally

- Comprehensive validation
  - Field-level validation (required, defaults, types)
  - Cross-field validation (required + default conflict)
  - Model-level validation (unique node IDs)
  - Type validation (temperature 0-1, positive integers)

- YAML/JSON round-trip support
  - Parse YAML/JSON → dict → Pydantic model
  - Export Pydantic model → dict → YAML/JSON
  - Aliases for reserved keywords (from, schema)
  - 5 integration tests

Verification:
  pytest -v
  Expected: 124 passed (31 types + 67 schema + 5 integration + 21 existing)

Progress: 3/20 tasks (15%) - Foundation phase
Next: T-004 (Config Validator)"
```

---

### Added - T-002: Config Parser ✅

**Commit**: T-002: Config parser - YAML and JSON support

**What Was Done**:
- Implemented `ConfigLoader` class for loading YAML/JSON files
- Auto-detects format from file extension (.yaml, .yml, .json)
- Handles both absolute and relative file paths
- Comprehensive error handling with helpful messages
- Convenience function `parse_config_file()` for simple use cases
- Created 18 comprehensive unit tests for parser (all pass)
- Created 3 setup verification tests
- Total: 21 tests passing
- Test fixtures for valid/invalid YAML and JSON
- **Automated setup scripts** for one-command venv setup (Windows & Unix)
- Setup scripts check if venv exists to avoid redundant installations

**Files Created**:
```
src/configurable_agents/config/
├── parser.py (ConfigLoader class + parse_config_file function)
└── __init__.py (exports public API)

tests/config/
├── __init__.py
├── test_parser.py (18 test functions)
└── fixtures/
    ├── valid_config.yaml
    ├── valid_config.json
    ├── invalid_syntax.yaml
    └── invalid_syntax.json

Development Setup:
├── setup.bat (Windows automated setup)
├── setup.sh (Unix/Linux/macOS automated setup)
└── SETUP.md (updated with Quick Setup section)
```

**How to Verify**:

1. **Test imports work**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file, ConfigLoader; print('Imports OK')"
   # Expected: Imports OK
   ```

2. **Load a YAML file**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.yaml'); print('Flow:', config['flow']['name'])"
   # Expected: Flow: test_workflow
   ```

3. **Load a JSON file**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.json'); print('Flow:', config['flow']['name'])"
   # Expected: Flow: test_workflow
   ```

4. **Test error handling** (file not found):
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('missing.yaml')"
   # Expected: FileNotFoundError: Config file not found: missing.yaml
   ```

5. **Test error handling** (invalid syntax):
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('tests/config/fixtures/invalid_syntax.yaml')"
   # Expected: ConfigParseError: Invalid YAML syntax...
   ```

6. **Run automated setup** (recommended - installs venv & dependencies):
   ```bash
   # Windows
   setup.bat

   # Unix/Linux/macOS
   ./setup.sh
   # Expected: Virtual environment created, dependencies installed
   ```

7. **Run full test suite** (after running setup script):
   ```bash
   .venv/Scripts/pytest tests/config/test_parser.py -v  # Windows
   .venv/bin/pytest tests/config/test_parser.py -v      # Unix
   # Expected: 18 passed in ~0.1s
   ```

**What to Expect**:
- ✅ Load YAML files (.yaml, .yml extensions)
- ✅ Load JSON files (.json extension)
- ✅ Auto-detect format from extension
- ✅ Both absolute and relative paths work
- ✅ Clear error messages for file not found
- ✅ Clear error messages for syntax errors
- ✅ Raises `ConfigParseError` for unsupported extensions
- ❌ No validation yet (returns raw dict, validation is T-004)
- ❌ No programmatic dict loading yet (just files)

**Public API**:
```python
# Recommended usage (convenience function)
from configurable_agents.config import parse_config_file

config = parse_config_file("workflow.yaml")  # or .json
# Returns: dict with config structure

# Advanced usage (class)
from configurable_agents.config import ConfigLoader

loader = ConfigLoader()
config = loader.load_file("workflow.yaml")
# Returns: dict with config structure

# Error handling
from configurable_agents.config import ConfigParseError

try:
    config = parse_config_file("config.yaml")
except FileNotFoundError:
    print("File not found")
except ConfigParseError as e:
    print(f"Parse error: {e}")
```

**Dependencies Used**:
- `pyyaml` - YAML parsing
- `json` (built-in) - JSON parsing
- `pathlib` (built-in) - Path handling

**Documentation Updated**:
- ✅ docs/TASKS.md (T-002 implementation details added)
- ✅ docs/ARCHITECTURE.md (Component 1 updated)
- ✅ docs/DISCUSSION.md (T-002 decisions documented)

**Git Commit Command**:
```bash
git add .
git commit -m "T-002: Config parser - YAML and JSON support

- Implemented ConfigLoader class with YAML/JSON auto-detection
- Added parse_config_file() convenience function
- Support for .yaml, .yml, and .json file extensions
- Comprehensive error handling (FileNotFoundError, ConfigParseError)
- Both absolute and relative path support
- Created 18 unit tests with valid/invalid fixtures
- Exported public API from config module
- Added automated setup scripts (setup.bat, setup.sh)
- Setup scripts check for existing venv to avoid redundant installs
- Updated SETUP.md with Quick Setup section

Verification:
  ./setup.sh  # or setup.bat on Windows
  .venv/Scripts/pytest tests/config/test_parser.py -v
  Expected: 18 passed

Progress: 2/20 tasks (10%) - Foundation phase
Next: T-003 (Config Schema - Pydantic Models)"
```

---

### Added - T-001: Project Setup ✅

**Commit**: T-001: Project setup - Package structure and dependencies

**What Was Done**:
- Created Python package structure (`src/configurable_agents/`)
- Set up all core modules: `config/`, `core/`, `llm/`, `tools/`, `runtime/`
- Configured dependencies in `pyproject.toml`
- Created development environment setup files
- Added logging configuration
- Set up comprehensive test structure
- Created development documentation

**Files Created**:
```
src/configurable_agents/
├── __init__.py (v0.1.0-dev)
├── logging_config.py
├── config/__init__.py
├── core/__init__.py
├── llm/__init__.py
├── tools/__init__.py
└── runtime/__init__.py

tests/
├── __init__.py
├── conftest.py (shared fixtures)
├── test_setup.py (verification tests)
└── {config,core,llm,tools,runtime,integration}/

Configuration:
├── pyproject.toml (dependencies & project metadata)
├── pytest.ini (test configuration)
├── .env.example (API key template)
└── .gitignore (comprehensive Python patterns)

Documentation:
├── README.md (complete user-facing documentation)
├── SETUP.md (development setup guide)
└── CHANGELOG.md (this file)
```

**How to Verify**:

1. **Check package structure exists**:
   ```bash
   ls -la src/configurable_agents/
   # Should see: __init__.py, logging_config.py, and 5 subdirectories
   ```

2. **Verify package imports work**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); import configurable_agents; print(f'Version: {configurable_agents.__version__}')"
   # Expected output: Version: 0.1.0-dev
   ```

3. **Verify all submodules import**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents import config, core, llm, tools, runtime; print('All modules imported successfully')"
   # Expected output: All modules imported successfully
   ```

4. **Check dependencies are defined**:
   ```bash
   grep -A 10 "dependencies = \[" pyproject.toml
   # Should show: pydantic, pyyaml, langgraph, langchain, etc.
   ```

5. **Verify test structure**:
   ```bash
   ls -la tests/
   # Should see: __init__.py, conftest.py, test_setup.py, and subdirectories
   ```

6. **Check environment template exists**:
   ```bash
   cat .env.example
   # Should show: GOOGLE_API_KEY, SERPER_API_KEY placeholders
   ```

**What to Expect**:
- ✅ Clean package structure following Python best practices
- ✅ All imports work (no module errors)
- ✅ Test framework ready (pytest configured)
- ✅ Dependencies declared (not yet installed by user)
- ✅ Development documentation available
- ❌ No actual functionality yet (just structure)
- ❌ Tests will pass but modules are empty placeholders

**Next Steps for User**:
```bash
# Install the package in development mode
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (not needed until T-009)
# GOOGLE_API_KEY=your-key-here

# Verify installation
python -c "import configurable_agents; print(configurable_agents.__version__)"

# Run setup verification tests
pytest tests/test_setup.py -v
```

**Dependencies Status**:
- Core: pydantic, pyyaml, langgraph, langchain, langchain-google-genai, python-dotenv
- Dev: pytest, pytest-cov, pytest-asyncio, black, ruff, mypy
- Status: Declared in pyproject.toml, not yet used in code

**Documentation Updated**:
- ✅ docs/TASKS.md (T-001 marked DONE, progress tracker added)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (complete rewrite with roadmap)
- ✅ SETUP.md (development guide created)
- ✅ CHANGELOG.md (this file created)

**Git Commit Command**:
```bash
git add .
git commit -m "T-001: Project setup - Package structure and dependencies

- Created src/configurable_agents/ package structure
- Set up config, core, llm, tools, runtime modules
- Configured pyproject.toml with all dependencies
- Added pytest configuration and test structure
- Created .env.example for API keys
- Updated .gitignore with comprehensive Python patterns
- Added logging_config.py for application logging
- Created SETUP.md development guide
- Rewrote README.md with roadmap and progress tracker
- Updated docs/TASKS.md and docs/DISCUSSION.md

Verification: python -c 'import sys; sys.path.insert(0, \"src\"); import configurable_agents; print(configurable_agents.__version__)'
Expected: 0.1.0-dev

Progress: 1/20 tasks (5%) - Foundation phase
Next: T-002 (Config Parser)"
```

---

## Template for Future Tasks

```markdown
## [Version] - YYYY-MM-DD

### Added - T-XXX: Task Name ✅

**Commit**: T-XXX: Brief description

**What Was Done**:
- Bullet points of changes

**Files Created/Modified**:
- List of files

**How to Verify**:
1. Command to run
2. Expected output

**What to Expect**:
- ✅ What works
- ❌ What doesn't work yet

**Next Steps for User**:
- Commands to run
- What to test

**Git Commit Command**:
```bash
git add .
git commit -m "..."
```
```

---

## Notes

- Each task gets one commit
- CHANGELOG updated before commit
- Verification steps included for reproducibility
- Progress tracked in both CHANGELOG and docs/TASKS.md
- Version stays at 0.1.0-dev until v0.1 release
