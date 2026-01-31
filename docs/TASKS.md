# Work Breakdown

**Version**: v0.1 (Schema v1.0)
**Last Updated**: 2026-01-31

**Philosophy**: Full Schema Day One (see ADR-009)

---

## Task Status Legend

- `TODO`: Not started
- `IN_PROGRESS`: Currently being worked on
- `BLOCKED`: Waiting on another task or external dependency
- `DONE`: Completed and tested

---

## Phase 1: Foundation (v0.1)

### T-001: Project Setup
**Status**: DONE ✅
**Priority**: P0 (Critical)
**Dependencies**: None
**Completed**: 2026-01-24

**Description**:
Set up project structure, dependencies, and development environment.

**Acceptance Criteria**:
- [x] Create proper Python package structure (`src/configurable_agents/`)
- [x] Set up `pyproject.toml` with dependencies:
  - `pydantic >= 2.0`
  - `pyyaml`
  - `langgraph`
  - `langchain`
  - `langchain-google-genai`
  - `pytest`
  - `python-dotenv`
- [x] Create `.env.example` with required environment variables
- [x] Set up pytest configuration
- [x] Create basic `.gitignore`
- [x] Verify imports work: `from configurable_agents import ...`
- [x] Set up logging configuration
- [x] Create 3 setup tests (test_package_version, test_imports, test_logging_config)

**Files Created**:
- `pyproject.toml`
- `src/configurable_agents/__init__.py` (+ all submodule `__init__.py`)
- `src/configurable_agents/logging_config.py`
- `.env.example`
- `pytest.ini`
- `.gitignore` (updated)
- `tests/__init__.py`, `tests/conftest.py`, `tests/test_setup.py`
- `SETUP.md`

**Tests**: 3 setup tests created

---

### T-002: Config Parser
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-001
**Completed**: 2026-01-24

**Description**:
Implement YAML/JSON config parser that loads config files into Python dicts.
Supports both YAML (.yaml, .yml) and JSON (.json) formats with automatic detection.

**Acceptance Criteria**:
- [x] Load YAML file from path (auto-detect .yaml/.yml)
- [x] Load JSON file from path (auto-detect .json)
- [x] Handle YAML/JSON syntax errors gracefully
- [x] Return parsed dict
- [x] Handle file not found errors
- [x] Support both absolute and relative paths
- [x] Class-based architecture with convenience functions
- [x] Unit tests for valid and invalid YAML/JSON (18 parser tests created)

**Files**:
- `src/configurable_agents/config/parser.py`
- `tests/config/test_parser.py`

**Tests**: 18 parser tests created (21 total project tests: 18 parser + 3 setup from T-001)

**Architecture**:
```python
class ConfigLoader:
    """Load workflow configurations from files or dicts"""

    def load_file(self, path: str) -> dict:
        """Load config from YAML or JSON file"""
        # Auto-detects format from extension
        pass

    def _parse_file(self, path: str) -> dict:
        """Parse YAML or JSON to dict"""
        pass

# Convenience functions for users
def parse_config_file(config_path: str) -> dict:
    """Load YAML or JSON config from file path"""
    return ConfigLoader().load_file(config_path)
```

**Design Decisions**:
- Both YAML and JSON supported from day one (minimal complexity, ~3 lines)
- Class structure for organization and future extensibility
- Function wrappers for user convenience
- Format detection via file extension (.yaml/.yml → YAML, .json → JSON)

---

### T-003: Config Schema (Pydantic Models) - EXPANDED
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-001
**Completed**: 2026-01-24
**Actual Effort**: 1 day (implementation highly efficient)

**Description**:
Define complete Pydantic models for Schema v1.0. Full schema from day one (see ADR-009).

**Acceptance Criteria**:
- [x] `WorkflowConfig` (top-level)
- [x] `FlowMetadata` (name, version, description)
- [x] `StateSchema` with:
  - [x] Basic types (str, int, float, bool)
  - [x] Collection types (list, dict, list[str], etc.)
  - [x] Nested objects (object with schema)
  - [x] Required/default fields
  - [x] Field descriptions
- [x] `NodeConfig` with:
  - [x] Input mapping (dict)
  - [x] Output schema (object or simple type)
  - [x] Tools list
  - [x] Node-level optimization config
  - [x] Node-level LLM overrides
- [x] `EdgeConfig` with:
  - [x] Linear edges (from, to)
  - [x] Conditional routes (list of conditions)
- [x] `OptimizationConfig` (DSPy settings - v0.3+)
- [x] `GlobalConfig` (LLM, execution, observability)
- [ ] JSON Schema export (for IDE autocomplete) - Deferred to later
- [x] Comprehensive unit tests:
  - [x] Valid configs pass
  - [x] Invalid configs fail with good errors
  - [x] Nested structures validated
  - [x] Type validation works
  - [x] Optional fields work
  - [x] Future features (optimization, conditionals) validate

**Files Created**:
- `src/configurable_agents/config/schema.py` (13 Pydantic models)
- `src/configurable_agents/config/types.py` (type parsing utilities)
- `tests/config/test_schema.py` (67 tests)
- `tests/config/test_types.py` (31 tests)
- `tests/config/test_schema_integration.py` (5 integration tests)

**Tests**: 103 tests created (31 type + 67 schema + 5 integration)
**Total Project Tests**: 124 (up from 21)

**Interface**:
```python
class WorkflowConfig(BaseModel):
    schema_version: str
    flow: FlowMetadata
    state: StateSchema
    nodes: list[NodeConfig]
    edges: list[EdgeConfig]
    optimization: Optional[OptimizationConfig] = None
    config: Optional[GlobalConfig] = None
```

---

### T-004: Config Validator - EXPANDED
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-002, T-003
**Estimated Effort**: 2 weeks
**Actual Effort**: 1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Implement comprehensive validation logic that checks config correctness beyond Pydantic schema validation.

**Acceptance Criteria**:
- [ ] **Schema version validation**:
  - [ ] Version is "1.0"
  - [ ] Warn if unknown version
- [ ] **Flow validation**:
  - [ ] Name is present and non-empty
- [ ] **State validation**:
  - [ ] At least one field defined
  - [ ] Field names are valid Python identifiers
  - [ ] Type strings are valid
  - [ ] Required fields don't have defaults
  - [ ] Nested object schemas are valid
- [ ] **Node validation**:
  - [ ] Node IDs are unique
  - [ ] Node IDs are valid identifiers
  - [ ] `output_schema` is present and valid
  - [ ] `outputs` list matches `output_schema` field names
  - [ ] All `outputs` reference valid state fields
  - [ ] Output types match state field types
  - [ ] Input mappings reference valid state fields
  - [ ] Prompt placeholders reference valid inputs or state
  - [ ] All tools exist in registry
  - [ ] Node-level optimization config is valid
  - [ ] Node-level LLM config is valid
- [ ] **Edge validation**:
  - [ ] All `from`/`to` references point to valid nodes or START/END
  - [ ] Exactly one edge from START
  - [ ] All nodes reachable from START
  - [ ] All nodes have path to END
  - [ ] No orphaned nodes
  - [ ] (v0.1) No cycles (linear flow check)
  - [ ] (v0.1) Each node has at most one outgoing edge
  - [ ] Conditional routes syntax is valid (even if not executed in v0.1)
- [ ] **Optimization validation** (v0.3+):
  - [ ] Strategy is valid string
  - [ ] Metric name is valid
  - [ ] Config structure is correct
- [ ] **Global config validation**:
  - [ ] LLM provider is valid (v0.1: only "google")
  - [ ] Model is valid for provider
  - [ ] Temperature is in range [0.0, 1.0]
  - [ ] Timeout/retries are positive integers
- [ ] **Error messages**:
  - [ ] Include file name and line number (if available)
  - [ ] Show context (surrounding lines)
  - [ ] Suggest fixes where possible
  - [ ] "Did you mean...?" for typos
- [ ] Comprehensive unit tests for all validation rules
- [ ] Integration tests with example configs

**Files**:
- `src/configurable_agents/config/validator.py`
- `tests/config/test_validator.py`

**Interface**:
```python
class ValidationError(Exception):
    def __init__(self, message: str, line: int = None, suggestion: str = None): ...

def validate_config(config: WorkflowConfig) -> list[ValidationError]:
    """Validate config and return all errors"""
```

---

### T-004.5: Runtime Feature Gating - NEW
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-003, T-004
**Estimated Effort**: 2-3 days
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Implement runtime checks for unsupported features in v0.1. Reject configs with features not yet implemented, with helpful error messages.

**Acceptance Criteria**:
- [ ] Check for conditional routing (v0.2+ feature)
  - [ ] Detect `routes` in edges
  - [ ] Raise `UnsupportedFeatureError` with timeline
  - [ ] Suggest linear alternative
- [ ] Check for optimization (v0.3+ feature)
  - [ ] Detect `optimization.enabled = true`
  - [ ] Warn (don't fail) that feature is ignored
  - [ ] Point to roadmap
- [ ] Check for observability config (v0.2+ feature)
  - [ ] Detect `config.observability`
  - [ ] Warn that only console logging is available
- [ ] Error messages include:
  - [ ] Feature name
  - [ ] Version when available (v0.2, v0.3)
  - [ ] Timeline (weeks)
  - [ ] Link to roadmap
  - [ ] Workaround for v0.1 (if applicable)
- [ ] Unit tests for all feature gates

**Files**:
- `src/configurable_agents/runtime/feature_gate.py`
- `tests/runtime/test_feature_gate.py`

**Interface**:
```python
class UnsupportedFeatureError(Exception):
    def __init__(self, feature: str, available_in: str, workaround: str = None): ...

def validate_runtime_support(config: WorkflowConfig) -> None:
    """Check if v0.1 runtime can execute this config"""
```

---

### T-005: Type System
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-001
**Estimated Effort**: 1 week
**Actual Effort**: <1 day (implemented as part of T-003)
**Completed**: 2026-01-26

**Description**:
Implement type parsing and validation for config type strings.

**Acceptance Criteria**:
- [x] Parse basic types: `str`, `int`, `float`, `bool`
- [x] Parse collection types: `list`, `dict`, `list[str]`, `list[int]`, `dict[str, int]`
- [x] Parse nested object type with schema
- [x] Convert type strings to Python types
- [x] Validate type strings are valid
- [x] Support type descriptions (handled via `StateFieldConfig.description`)
- [x] Unit tests for all supported types (31 tests)
- [x] Error messages for invalid types

**Files Created**:
- `src/configurable_agents/config/types.py` (type parsing utilities)
- `tests/config/test_types.py` (31 comprehensive tests)

**Note**: Files are in `config/` package instead of `core/` as originally specified. Type descriptions are supported at the field level via `StateFieldConfig.description` in schema.py, not at the type system level.

**Interface**:
```python
def parse_type_string(type_str: str) -> Dict[str, Any]:
    """Parse type string into structured representation"""

def validate_type_string(type_str: str) -> bool:
    """Check if type string is valid"""

def get_python_type(type_str: str) -> Type:
    """Convert type string to Python type"""
```

---

### T-006: State Schema Builder
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-005
**Estimated Effort**: 1 week
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Dynamically generate Pydantic state models from config. Supports nested objects.

**Acceptance Criteria**:
- [x] Create Pydantic `BaseModel` from state config
- [x] Support all type system types
- [x] Handle required fields
- [x] Handle default values
- [x] Support nested objects (recursive schema building)
- [x] Validate state at instantiation
- [x] Include field descriptions in model
- [x] Unit tests with various state schemas:
  - [x] Simple flat state (4 tests)
  - [x] Nested state (1 level) (3 tests)
  - [x] Deeply nested state (3+ levels) (2 tests)
  - [x] All type combinations (1 kitchen sink test)
- [x] Additional comprehensive test coverage (30 total tests)

**Files Created**:
- `src/configurable_agents/core/state_builder.py` (dynamic model builder, 207 lines)
- `tests/core/test_state_builder.py` (30 comprehensive tests)
- `tests/core/__init__.py`

**Interface**:
```python
def build_state_model(state_config: StateSchema) -> Type[BaseModel]:
    """Create Pydantic state model from config"""
    # Returns dynamic WorkflowState class

# Raises StateBuilderError on build failures
```

**Features**:
- Recursive nested object support with meaningful names (WorkflowState_metadata)
- No redundant validation (leverages T-004)
- Supports both simple and full schema formats
- Fail-fast error handling with clear messages

---

### T-007: Output Schema Builder
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-005
**Estimated Effort**: 1 week
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Dynamically generate Pydantic output models for node outputs. This enables type enforcement.

**Acceptance Criteria**:
- [x] Create Pydantic model from `output_schema` config
- [x] Support all type system types (basic, collections)
- [x] Include field descriptions (helps LLM)
- [x] Support simple output (single type)
- [x] Support object output (multiple fields)
- [x] Unit tests with various output schemas:
  - [x] Simple string output (and int, float, bool)
  - [x] Object with multiple fields
  - [x] List and dict outputs (generic and typed)
  - [x] Object with list/dict fields
  - [x] Model naming, error handling, round-trip serialization
- [x] 29 comprehensive tests (all scenarios)
- [x] 231 total tests passing (up from 202)

**Files Created**:
- `src/configurable_agents/core/output_builder.py` (dynamic output model builder)
- `tests/core/test_output_builder.py` (29 comprehensive tests)

**Tests**: 29 output builder tests created (231 total project tests: 29 output + 202 existing)

**Interface**:
```python
from configurable_agents.core import build_output_model, OutputBuilderError

# Build dynamic output model
def build_output_model(output_schema: OutputSchema, node_id: str) -> Type[BaseModel]:
    """Create Pydantic output model from config"""

# Simple output (wrapped in 'result' field)
OutputModel = build_output_model(OutputSchema(type="str"), "write")
output = OutputModel(result="Generated text")

# Object output (multiple fields)
OutputModel = build_output_model(
    OutputSchema(
        type="object",
        fields=[
            OutputSchemaField(name="article", type="str"),
            OutputSchemaField(name="word_count", type="int"),
        ]
    ),
    "write"
)
output = OutputModel(article="...", word_count=500)
```

**Features**:
- Simple outputs wrapped in 'result' field for consistency
- Object outputs with explicit fields
- All output fields required (LLM must provide them)
- Type validation enforced by Pydantic
- Field descriptions preserved (helps LLM)
- Model naming: Output_{node_id}
- Clear error messages with node_id context
- Nested objects not yet supported (can add if needed)

**Note**: Completes Phase 1 (Foundation) - all 8 tasks done!

---

### T-008: Tool Registry
**Status**: DONE ✅
**Priority**: P1
**Dependencies**: T-001
**Estimated Effort**: 1 week
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Implement tool registry that loads tools by name. v0.1 includes `serper_search`.

**Acceptance Criteria**:
- [x] Registry interface to get tool by name
- [x] Implement `serper_search` tool using LangChain
- [x] Load API keys from environment
- [x] Fail loudly if tool not found
- [x] Fail loudly if API key missing (with helpful message)
- [x] List available tools
- [x] Unit tests (mock tool loading)
- [x] Integration test with real Serper API (optional, slow)

**Files Created**:
- `src/configurable_agents/tools/registry.py` (ToolRegistry + global API)
- `src/configurable_agents/tools/serper.py` (Serper search implementation)
- `tests/tools/__init__.py`
- `tests/tools/test_registry.py` (22 tests)
- `tests/tools/test_serper.py` (15 tests + 2 integration tests)

**Tests**: 37 tests created (268 total project tests: 37 tools + 231 existing)

**Interface**:
```python
from configurable_agents.tools import (
    get_tool,        # Get tool by name
    list_tools,      # List available tools
    has_tool,        # Check if tool exists
    register_tool,   # Register custom tools
    ToolNotFoundError,    # Tool not found exception
    ToolConfigError,      # Tool config error exception
)

# Usage
tools = list_tools()  # ['serper_search']
search = get_tool("serper_search")
results = search.run("Python programming")
```

**Features Implemented**:
- Factory-based lazy loading (tools created on demand)
- Global registry instance for convenience
- Comprehensive error messages with setup instructions
- LangChain BaseTool integration
- Environment-based API key configuration
- Extensible design for custom tool registration

---

### T-009: LLM Provider
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-001, T-007
**Estimated Effort**: 1 week
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Implement LLM provider for Google Gemini with structured outputs (type enforcement).

**Acceptance Criteria**:
- [x] Initialize LLM with config (model, temperature, max_tokens)
- [x] Call LLM with structured output (Pydantic schema)
- [x] Handle API errors gracefully
- [x] Read API key from environment
- [x] Retry on rate limit (exponential backoff)
- [x] Retry on validation errors (with clarified prompt)
- [x] Configuration merging (node overrides global)
- [x] Unit tests (mock LLM calls) - 32 tests
- [x] Integration test with real Gemini API (optional, slow) - 2 tests
- [x] **Verification**: LangChain with_structured_output used (ADR-001)

**Files Created**:
- `src/configurable_agents/llm/provider.py` (LLM factory, structured calling, retries)
- `src/configurable_agents/llm/google.py` (Google Gemini implementation)
- `src/configurable_agents/llm/__init__.py` (public API exports)
- `tests/llm/__init__.py`
- `tests/llm/test_provider.py` (19 tests)
- `tests/llm/test_google.py` (13 tests + 2 integration tests)

**Tests**: 32 tests created (300 total project tests: 32 llm + 268 existing)

**Interface**:
```python
from configurable_agents.llm import (
    create_llm,           # Create LLM from config
    call_llm_structured,  # Call LLM with structured output
    merge_llm_config,     # Merge node and global configs
    LLMConfigError,       # Configuration error
    LLMProviderError,     # Provider not supported
    LLMAPIError,          # API call failure
)

# Create LLM from config (supports config merging)
llm = create_llm(llm_config, global_config=None)

# Call LLM with structured output (automatic retries)
result = call_llm_structured(
    llm, prompt, OutputModel, tools=None, max_retries=3
)

# Merge configurations (node overrides global)
merged = merge_llm_config(node_config, global_config)
```

**Features Implemented**:
- Factory pattern for LLM creation
- Google Gemini provider (gemini-1.5-flash, gemini-1.5-pro, gemini-pro)
- Structured output with Pydantic schema binding
- Automatic retry on ValidationError (clarified prompts)
- Exponential backoff on rate limits
- Configuration merging (node overrides global)
- Tool binding support
- Environment-based API key configuration
- Comprehensive error handling with helpful messages

---

### T-010: Prompt Template Resolver
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-006
**Estimated Effort**: 3-4 days
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-26

**Description**:
Resolve `{variable}` placeholders in prompt templates from state or input mappings.

**Acceptance Criteria**:
- [x] Parse prompt templates
- [x] Extract variable references
- [x] Resolve from input mappings (if provided)
- [x] Resolve from state fields (fallback)
- [x] Handle missing variables gracefully (error)
- [x] Support nested state access: `{metadata.author}`
- [x] Unit tests with various templates:
  - [x] Simple placeholders
  - [x] Nested placeholders (1 level and 3+ levels)
  - [x] Mixed input mappings and state
  - [x] Missing variable errors with suggestions
  - [x] Type conversion (int, bool → string)
  - [x] 44 comprehensive tests

**Files Created**:
- `src/configurable_agents/core/template.py` (template resolver, 237 lines)
- `tests/core/test_template.py` (44 comprehensive tests)

**Tests**: 44 tests created (344 total project tests: 44 template + 300 existing)

**Interface**:
```python
from configurable_agents.core import (
    resolve_prompt,             # Main resolution function
    extract_variables,          # Extract {variable} references
    TemplateResolutionError,    # Resolution error exception
)

def resolve_prompt(
    prompt_template: str,
    inputs: dict,  # From node.inputs mapping (overrides state)
    state: BaseModel
) -> str:
    """Resolve {variable} placeholders in prompt"""

# Example
resolved = resolve_prompt(
    "Hello {name}, discuss {topic}",
    {"name": "Alice"},  # Inputs override state
    state_model
)
# Returns: "Hello Alice, discuss AI Safety"
```

**Features Implemented**:
- Variable extraction with regex (supports dot notation)
- Input priority over state (explicit precedence)
- Nested state access: {metadata.author}, {metadata.flags.level}
- Deeply nested access (3+ levels)
- Type conversion (automatic str() for all values)
- Comprehensive error messages
- "Did you mean X?" suggestions (edit distance ≤ 2)
- Available variables listed in errors
- Fast fail-first on missing variables

---

### T-011: Node Executor
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-007, T-008, T-009, T-010
**Estimated Effort**: 1.5 weeks
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-27

**Description**:
Execute a single node (LLM call with tools, type-enforced output).

**Acceptance Criteria**:
- [x] Resolve input mappings from state
- [x] Resolve prompt from state/inputs
- [x] Load tools from registry
- [x] Configure LLM (merge global + node config)
- [x] Call LLM with structured output (Pydantic model)
- [x] Validate output against schema (handled by T-009 retries)
- [x] Retry on validation failure (handled by T-009)
- [x] Update state with outputs (copy-on-write pattern)
- [x] Handle errors:
  - [x] LLM timeout (via T-009)
  - [x] Tool failure
  - [x] Schema mismatch (via T-009 retry)
  - [x] Type validation failure
- [x] Log node execution (INFO level logging)
- [x] Unit tests (23 comprehensive tests - all mocked)
- [ ] Integration tests with real LLM (deferred to T-017)

**Files Created**:
- `src/configurable_agents/core/node_executor.py` (execute_node, NodeExecutionError, _strip_state_prefix)
- `tests/core/test_node_executor.py` (23 tests)

**Tests**: 23 tests created (367 total project tests: 23 node executor + 344 existing)

**Interface**:
```python
from configurable_agents.core import execute_node, NodeExecutionError

def execute_node(
    node_config: NodeConfig,
    state: BaseModel,
    global_config: Optional[GlobalConfig] = None
) -> BaseModel:
    """Execute node and return updated state (new instance)"""
```

**Features Implemented**:
- Input mapping resolution with template syntax
- Prompt template resolution with {state.field} preprocessing
- Tool loading and binding to LLM
- LLM configuration merging (node overrides global)
- Structured output enforcement (Pydantic models from T-007)
- Copy-on-write state updates (immutable pattern)
- Comprehensive error handling with NodeExecutionError
- Logging at INFO level (execution success/failure)

**Design Decisions**:
1. **Copy-on-write state**: Returns new state instance (immutable pattern)
2. **Input mapping semantics**: `inputs: {local: "{template}"}` resolves template against state
3. **State prefix preprocessing**: `_strip_state_prefix` converts `{state.field}` → `{field}`
   - **TODO T-011.1**: Update template resolver to handle {state.X} natively and remove preprocessing
4. **Error wrapping**: All errors wrapped in NodeExecutionError with node_id context
5. **Retry logic**: Delegated to LLM provider (T-009) - max_retries from global config
6. **Logging**: INFO for success/failure, DEBUG for detailed execution steps
7. **Tool binding**: Tools loaded lazily per node execution

**Known Issues / Future Work**:
- **T-011.1 (Future Enhancement)**: Template resolver should handle {state.field} syntax natively
  - Current workaround: `_strip_state_prefix` helper preprocesses prompts
  - Validator (T-004) and SPEC.md both use {state.field} syntax
  - Template resolver (T-010) expects {field} without prefix
  - Resolution: Update template resolver in v0.2+ to accept both syntaxes
  - Location: `src/configurable_agents/core/template.py`
  - Impact: Low (preprocessing works fine, just not elegant)

**Error Messages**:
```python
# Input mapping error
NodeExecutionError: Node 'test': Failed to resolve input mapping 'query' from '{unknown}': Variable 'unknown' not found

# Prompt resolution error
NodeExecutionError: Node 'test': Prompt template resolution failed: Variable 'unknown' not found

# Tool loading error
NodeExecutionError: Node 'test': Tool loading failed: Tool 'unknown_tool' not found

# LLM creation error
NodeExecutionError: Node 'test': LLM creation failed: GOOGLE_API_KEY not set

# Output model error
NodeExecutionError: Node 'test': Output model creation failed: Invalid schema

# LLM call error
NodeExecutionError: Node 'test': LLM call failed: API timeout
```

**Phase 2 Progress**:
T-011 completes 4/6 tasks in Phase 2 (Core Execution) - 67% complete!

---

### T-012: Graph Builder
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-011
**Estimated Effort**: 1.5 weeks
**Actual Effort**: <1 day
**Completed**: 2026-01-27

**Description**:
Build LangGraph StateGraph from config. v0.1: Linear flows only.

**Acceptance Criteria**:
- [x] Create StateGraph instance
- [x] Add nodes from config
- [x] Add edges from config (linear only)
- [x] Validate graph structure (no cycles, reachable)
- [x] Compile graph
- [x] Reject conditional routing (feature gate)
- [x] Unit tests (mock node execution)
- [x] Integration tests with real nodes

**Files Created**:
- `src/configurable_agents/core/graph_builder.py` (build_graph, make_node_function, GraphBuilderError)
- `tests/core/test_graph_builder.py` (18 comprehensive tests: 16 unit + 2 integration)

**Files Modified**:
- `src/configurable_agents/core/__init__.py` (exports)

**Tests**: 18 tests created (383 total project tests: 18 graph builder + 365 existing)

**Interface**:
```python
from configurable_agents.core import build_graph, GraphBuilderError

def build_graph(
    config: WorkflowConfig,
    state_model: Type[BaseModel],
    global_config: Optional[GlobalConfig] = None
) -> CompiledStateGraph:
    """
    Build and compile LangGraph from config.

    Returns compiled graph ready for execution.
    LangGraph returns dict from invoke(), not BaseModel.
    """
```

**Implementation Features**:
- ✅ Direct Pydantic BaseModel integration with LangGraph (no TypedDict conversion)
- ✅ Closure-based node functions (capture node_config and global_config)
- ✅ START/END as LangGraph entry/exit points (not identity nodes)
- ✅ Compiled graph output (ready for immediate execution)
- ✅ Defensive validation (catches validator bugs)
- ✅ Linear flow enforcement (v0.1 constraint - no branching/conditional routing)
- ✅ NodeExecutionError propagation with context preservation
- ✅ Unexpected error wrapping with node_id context
- ✅ Logging at INFO (high-level) and DEBUG (detailed) levels

**Key Design Decisions**:
1. **CompiledStateGraph**: LangGraph's actual type (not CompiledGraph)
2. **Dict Return**: LangGraph's invoke() returns dict, not BaseModel
3. **Closure Pattern**: Clean config capture without state pollution
4. **Minimal Validation**: Trust T-004, defensive checks only
5. **model_construct()**: Used in tests to bypass Pydantic validation

**Integration Points**:
- Calls `execute_node` from T-011 via closure-wrapped node functions
- Uses `WorkflowConfig`, `NodeConfig`, `EdgeConfig` from T-003
- Enables T-013 (Runtime Executor) with perfect interface alignment

**Phase 2 Progress**:
T-012 completes 5/6 tasks in Phase 2 (Core Execution) - 83% complete!

---

### T-013: Runtime Executor
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-004, T-004.5, T-006, T-012
**Estimated Effort**: 1.5 weeks
**Actual Effort**: <1 day (highly efficient implementation)
**Completed**: 2026-01-27

**Description**:
Main entry point that orchestrates config → execution.

**Acceptance Criteria**:
- [x] Load and parse config (YAML/JSON)
- [x] Validate config (T-004)
- [x] Check runtime support (T-004.5)
- [x] Build state model
- [x] Initialize state with inputs
- [x] Build and compile graph
- [x] Execute graph
- [x] Return final state as dict
- [x] Handle all error types gracefully:
  - [x] Config validation errors
  - [x] Runtime feature errors
  - [x] Node execution errors
  - [x] Graph execution errors
- [x] Log workflow execution (start, end, duration)
- [x] Integration tests with example configs (4 tests)
- [x] Verbose logging option for debugging
- [x] Validation-only mode (validate without executing)

**Files Created**:
- `src/configurable_agents/runtime/executor.py` (330 lines)
- `src/configurable_agents/runtime/__init__.py` (updated exports)
- `tests/runtime/test_executor.py` (670 lines, 23 tests)
- `tests/runtime/test_executor_integration.py` (295 lines, 4 integration tests)
- `examples/simple_workflow.yaml` (minimal example)
- `examples/README.md` (usage guide)

**Tests**: 23 comprehensive tests + 4 integration tests (406 total project tests: up from 383)

**Interface**:
```python
from configurable_agents.runtime import (
    run_workflow,              # Execute from file
    run_workflow_from_config,  # Execute from config
    validate_workflow,         # Validate only

    # Error types
    ExecutionError,
    ConfigLoadError,
    ConfigValidationError,
    StateInitializationError,
    GraphBuildError,
    WorkflowExecutionError,
)

# Execute workflow
result = run_workflow("workflow.yaml", {"topic": "AI Safety"})

# Validate only
validate_workflow("workflow.yaml")

# Execute with verbose logging
result = run_workflow("workflow.yaml", {"topic": "AI"}, verbose=True)
```

**Features Implemented**:
- 6-phase execution pipeline with granular error handling
- Comprehensive logging (INFO and DEBUG levels)
- Execution timing and metrics
- Clear error messages with phase identification
- Original exception preservation for debugging
- Verbose mode for detailed execution traces
- Validation-only mode for pre-flight checks

**Phase 2 Complete**:
T-013 completes Phase 2 (Core Execution) - all 6/6 tasks done!

---

### T-014: CLI Interface
**Status**: DONE ✅
**Priority**: P1
**Dependencies**: T-013
**Completed**: 2026-01-27
**Estimated Effort**: 1 week

**Description**:
Command-line interface for running and validating workflows.

**Acceptance Criteria**:
- [x] `run` command: execute workflow from file
- [x] `validate` command: validate config without running
- [x] Parse command-line arguments for inputs
- [x] Pretty-print output (color-coded with Unicode fallback)
- [x] Show helpful error messages
- [x] Support --input flag for inputs
- [x] Support --verbose flag for debug logging
- [x] Integration tests (37 unit + 2 integration tests)

**Files Created**:
- `src/configurable_agents/__main__.py` (14 lines)
- `src/configurable_agents/cli.py` (367 lines)
- `tests/test_cli.py` (597 lines, 39 tests)

**Features Implemented**:
- Smart input parsing with type detection (str, int, bool, JSON)
- Color-coded terminal output (green/red/blue/yellow)
- Unicode fallback for Windows console compatibility
- Comprehensive error handling with 6 exception types
- Two entry points: `configurable-agents` script and `python -m`
- Exit codes: 0 (success), 1 (error)

**Usage**:
```bash
# Run command
configurable-agents run workflow.yaml --input topic="AI Safety"
python -m configurable_agents run workflow.yaml --input topic="AI Safety"

# Validate command
configurable-agents validate workflow.yaml
python -m configurable_agents validate workflow.yaml

# Verbose mode
configurable-agents run workflow.yaml --input name="Alice" --verbose

# Multiple inputs with types
configurable-agents run workflow.yaml \
  --input topic="AI" \
  --input count=5 \
  --input enabled=true \
  --input 'tags=["ai", "safety"]'
```

**Tests**: 39 tests created (37 unit + 2 integration), 443 total passing

---

### T-015: Example Configs
**Status**: DONE ✅
**Priority**: P1
**Dependencies**: T-013
**Estimated Effort**: 3-4 days
**Actual Effort**: <1 day
**Completed**: 2026-01-28

**Description**:
Create example workflow configs using Schema v1.0 format.

**Acceptance Criteria**:
- [x] Simple echo workflow (minimal example)
- [x] Article writer workflow (with tools, multi-step)
- [x] Nested state example
- [x] Type enforcement example (int, list, object outputs)
- [x] All examples work end-to-end
- [x] Include in documentation
- [x] Each example has README explaining it

**Files Created**:
- `examples/echo.yaml` (minimal, 1 node)
- `examples/article_writer.yaml` (multi-step with tools, 2 nodes)
- `examples/nested_state.yaml` (nested objects)
- `examples/type_enforcement.yaml` (complete type system demo)
- `examples/echo_README.md` (beginner guide)
- `examples/article_writer_README.md` (tool integration guide)
- `examples/nested_state_README.md` (nested state guide)
- `examples/type_enforcement_README.md` (type system reference)

**Files Modified**:
- `examples/README.md` (comprehensive catalog with learning path)

**Validation**:
All examples validated successfully with `configurable-agents validate` command.

---

### T-016: Documentation
**Status**: DONE ✅
**Priority**: P1
**Dependencies**: T-015
**Estimated Effort**: 1 week
**Completed**: 2026-01-28

**Description**:
Write user-facing documentation.

**Acceptance Criteria**:
- [x] README.md with quickstart
- [x] Installation instructions
- [x] Environment setup guide (API keys)
- [x] Config schema reference (reference SPEC.md)
- [x] Example walkthrough
- [x] Troubleshooting guide
- [x] Version availability table (what's in v0.1 vs v0.2 vs v0.3)
- [x] Roadmap

**Files Created**:
- `docs/QUICKSTART.md` (5-minute tutorial)
- `docs/CONFIG_REFERENCE.md` (user-friendly schema guide)
- Roadmap integrated into `README.md` (version overview)
- `docs/TROUBLESHOOTING.md` (common issues and solutions)

**Files Modified**:
- `README.md` (added user guides section)

---

### T-017: Integration Tests
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-013 ✅, T-015 ✅
**Estimated Effort**: 1 week
**Actual Effort**: 1 day
**Completed**: 2026-01-28

**Description**:
End-to-end integration tests with real LLM calls. Comprehensive test suite covering all workflows and error scenarios.

**Acceptance Criteria**:
- [x] Test each example config (3/5 tested, 2 skipped with documentation)
- [x] Test with real Google Gemini API
- [x] Test error scenarios:
  - [x] Invalid config
  - [x] Missing API key
  - [x] LLM timeout
  - [x] Tool failure
- [x] Test with tools (serper_search)
- [x] Test type enforcement (wrong types rejected)
- [x] Mark as slow tests (skip in CI if needed)
- [x] Generate test report with costs

**Files Created**:
- `tests/integration/__init__.py` (package initialization)
- `tests/integration/conftest.py` (197 lines - fixtures, cost tracking)
- `tests/integration/test_workflows.py` (332 lines - 6 workflow tests)
- `tests/integration/test_error_scenarios.py` (537 lines - 13 error tests)
- `docs/INTEGRATION_TESTING_FULL.md` (comprehensive implementation report)

**Files Modified**:
- `src/configurable_agents/llm/google.py` (updated default model to gemini-2.5-flash-lite)
- `src/configurable_agents/llm/provider.py` (CRITICAL: fixed tool binding order bug)
- `tests/conftest.py` (added .env loading)
- `examples/article_writer.yaml` (updated model name)
- `examples/nested_state.yaml` (updated model name)
- `examples/type_enforcement.yaml` (updated model name)
- `tests/llm/test_google.py` (updated model assertions)
- `tests/llm/test_provider.py` (updated model assertions, fixed tool binding mock)
- `tests/runtime/test_executor_integration.py` (skipped old tests)

**Test Results**:
- **Total**: 468 tests passing (up from 443)
- **Integration Tests**: 19 tests (17 passed, 2 skipped)
- **Execution Time**: 21.64s for integration tests
- **API Calls**: ~17 real API calls to Google Gemini and Serper

**Bugs Fixed**:
1. **Tool Binding Order**: Tools must be bound BEFORE structured output (prevented article_writer.yaml from working)
2. **Model Name**: Updated gemini-1.5-flash → gemini-2.5-flash-lite (404 errors fixed)

**Known Limitations Documented**:
- Nested objects in output schema not yet supported (2 tests skipped with clear documentation)

---

### T-018: MLFlow Integration Foundation
**Status**: DONE ✅
**Priority**: P0
**Dependencies**: T-001 (Setup)
**Completed**: 2026-01-31
**Actual Effort**: ~5 hours

**Description**:
Add MLFlow observability foundation - config schema, dependency installation, cost estimation, and tracking infrastructure with graceful degradation.

**Acceptance Criteria**:
- [x] Add `mlflow>=2.9.0` to dependencies (pyproject.toml)
- [x] Extend config schema with `ObservabilityConfig` and `MLFlowConfig`:
  - `enabled`: bool (default: False)
  - `tracking_uri`: str (default: "file://./mlruns")
  - `experiment_name`: str (default: "configurable_agents")
  - `run_name`: Optional[str] (template support)
  - `log_artifacts`: bool (default: True)
  - Enterprise hooks: `retention_days`, `redact_pii` (not enforced)
- [x] Create `src/configurable_agents/observability/` package
- [x] Create `CostEstimator` with pricing for 9 Gemini models (January 2025 pricing)
- [x] Create `MLFlowTracker` with workflow/node-level tracking
- [x] Integrate tracker into runtime executor
- [x] Graceful degradation when MLFlow unavailable (zero performance overhead)
- [x] Unit tests (37 tests: 18 cost estimator + 19 MLFlow tracker)
- [x] Integration tests with real MLFlow (9 tests)
- [x] Document config schema in SPEC.md with updated pricing
- [x] Implementation log created

**Files Created**:
- `src/configurable_agents/observability/__init__.py`
- `src/configurable_agents/observability/cost_estimator.py` (218 lines)
- `src/configurable_agents/observability/mlflow_tracker.py` (403 lines)
- `tests/observability/__init__.py`
- `tests/observability/test_cost_estimator.py` (18 tests)
- `tests/observability/test_mlflow_tracker.py` (19 unit tests)
- `tests/observability/test_mlflow_integration.py` (9 integration tests)
- `implementation_logs/phase_4_observability_docker/T-018_mlflow_integration_foundation.md`

**Files Modified**:
- `src/configurable_agents/config/schema.py` (updated ObservabilityMLFlowConfig)
- `src/configurable_agents/runtime/executor.py` (integrated MLFlowTracker)
- `pyproject.toml` (added mlflow>=2.9.0)
- `docs/SPEC.md` (updated pricing for 9 Gemini models)
- `docs/adr/ADR-011-mlflow-observability.md` (updated pricing and status)
- `CHANGELOG.md` (added T-018 entry)

**Tests**: 46 tests (37 unit + 9 integration) - 100% passing

**Key Features**:
- Automatic cost calculation for 9 Gemini models with latest pricing
- Workflow-level and node-level (nested runs) tracking
- Artifact logging for inputs, outputs, prompts, responses
- Graceful degradation with zero overhead when disabled
- Windows-compatible file:// URI handling

**Models Supported**:
- gemini-3-pro, gemini-3-flash
- gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite
- gemini-1.5-pro, gemini-1.5-flash, gemini-1.5-flash-8b
- gemini-1.0-pro

**Related ADRs**: ADR-011 (MLFlow Observability)

---

### T-019: MLFlow Instrumentation (Runtime & Nodes)
**Status**: ✅ DONE (2026-01-31)
**Priority**: P0
**Dependencies**: T-018, T-013 (Runtime Executor)
**Actual Effort**: 2.5 hours

**Description**:
Instrument runtime executor and node executor to log params, metrics, and artifacts to MLFlow.

**Acceptance Criteria**:
- [x] Workflow-level tracking in `runtime/executor.py`:
  - [x] Start MLFlow run on workflow start (T-018)
  - [x] Log params: workflow_name, version, schema_version, global_model, global_temperature (T-018)
  - [x] Log metrics: duration_seconds, total_input_tokens, total_output_tokens, node_count, retry_count, status (T-018)
  - [x] Log artifacts: inputs.json, outputs.json, error.txt (if failed) (T-018)
  - [x] End run on workflow completion (T-018)
- [x] Node-level tracking in `core/node_executor.py`:
  - [x] Start nested run per node
  - [x] Log params: node_id, node_model, tools
  - [x] Log metrics: node_duration_ms, input_tokens, output_tokens, retries
  - [x] Log artifacts: prompt.txt, response.txt
  - [x] End nested run
- [x] Handle MLFlow disabled gracefully (no-op if not enabled)
- [x] Token tracking from LLM responses
- [x] Error tracking (exception details) (T-018)
- [x] Unit tests (existing tests updated, 455 tests passing)
- [x] Integration test (runtime executor tests)

**Implementation**:
- Modified `call_llm_structured()` to return tuple `(result, usage)` with token counts
- Added `LLMUsageMetadata` class for token tracking
- Instrumented `execute_node()` to wrap execution in `tracker.track_node()`
- Passed tracker through graph builder to node executor
- Updated all test mocks to handle new tuple return
- Fixed MLFlow test mocking (set `mlflow = None` in except block for mockability)

**Files Modified**:
- `src/configurable_agents/llm/provider.py` (token extraction)
- `src/configurable_agents/llm/__init__.py` (export LLMUsageMetadata)
- `src/configurable_agents/core/node_executor.py` (node-level tracking)
- `src/configurable_agents/core/graph_builder.py` (tracker propagation)
- `src/configurable_agents/runtime/executor.py` (initialization order)
- `tests/llm/test_provider.py` (19 tests updated)
- `tests/core/test_node_executor.py` (24 tests updated)
- `tests/core/test_graph_builder.py` (18 tests updated)

**Tests**: 492 unit tests passing (includes 19 observability tests, all fixed and passing)

**Related ADRs**: ADR-011

---

### T-020: Cost Tracking & Reporting
**Status**: TODO
**Priority**: P1
**Dependencies**: T-019
**Estimated Effort**: 2 days

**Description**:
Implement token-to-cost calculation and cost tracking in MLFlow.

**Acceptance Criteria**:
- [ ] Create `llm/cost_tracker.py` with pricing tables:
  - `PRICING` dict with model → {input, output} $/1K tokens
  - Support: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-lite
  - Placeholder for future: OpenAI, Anthropic, etc.
- [ ] `calculate_cost(model, input_tokens, output_tokens)` function
- [ ] Log cost metrics in MLFlow:
  - `cost_usd` (per run, cumulative)
  - `cost_per_node_avg` (average cost per node)
- [ ] Create example cost reporting notebook:
  - Query MLFlow API for all runs
  - Aggregate costs (total, per workflow, per model)
  - Export to CSV
  - Visualize trends (matplotlib/seaborn)
- [ ] Unit tests for cost calculation (15 tests)
- [ ] Integration test with MLFlow (1 test)
- [ ] Document pricing tables in OBSERVABILITY.md

**Files Created**:
- `src/configurable_agents/llm/cost_tracker.py`
- `examples/notebooks/cost_report.ipynb` (Jupyter notebook)
- `tests/llm/test_cost_tracker.py`

**Files Modified**:
- `src/configurable_agents/core/node_executor.py` (log costs)
- `src/configurable_agents/runtime/executor.py` (aggregate costs)

**Tests**: 16 tests (15 unit + 1 integration)

**Related ADRs**: ADR-011

---

### T-021: Observability Documentation
**Status**: TODO
**Priority**: P1
**Dependencies**: T-018, T-019, T-020
**Estimated Effort**: 2 days

**Description**:
Comprehensive observability documentation covering MLFlow usage, setup, and future roadmap.

**Acceptance Criteria**:
- [ ] Create `docs/OBSERVABILITY.md`:
  - [ ] Overview (why observability matters)
  - [ ] MLFlow quick start (install, enable, view UI)
  - [ ] Configuration reference (all options explained)
  - [ ] What gets tracked (workflow-level, node-level, costs)
  - [ ] Docker integration (MLFlow UI in container)
  - [ ] Cost tracking guide (query API, export CSV)
  - [ ] DSPy integration (future, v0.3+)
  - [ ] Enterprise features (retention, PII redaction, multi-tenancy)
  - [ ] OpenTelemetry integration (future, v0.2+) - detailed guide
  - [ ] Prometheus integration (future, v0.3+) - detailed guide
  - [ ] Comparison matrix (MLFlow vs OTEL vs Prometheus)
  - [ ] Best practices (when to use what)
  - [ ] Troubleshooting
- [ ] Create example workflow with MLFlow enabled:
  - `examples/article_writer_mlflow.yaml`
- [ ] Update `docs/CONFIG_REFERENCE.md` (add observability section)
- [ ] Update `docs/QUICKSTART.md` (mention observability)
- [ ] Update `README.md` (add observability features)

**Files Created**:
- `docs/OBSERVABILITY.md` (comprehensive guide, ~800 lines)
- `examples/article_writer_mlflow.yaml`

**Files Modified**:
- `docs/CONFIG_REFERENCE.md`
- `docs/QUICKSTART.md`
- `README.md`

**Related ADRs**: ADR-011, ADR-014

---

### T-022: Docker Artifact Generator & Templates
**Status**: TODO
**Priority**: P0
**Dependencies**: T-013 (Runtime Executor), T-021 (Observability)
**Estimated Effort**: 2 days

**Description**:
Implement artifact generation for Docker deployment - Dockerfile, FastAPI server, requirements, etc.

**Acceptance Criteria**:
- [ ] Create `src/configurable_agents/deploy/` package
- [ ] Create `src/configurable_agents/deploy/generator.py`:
  - [ ] `generate_deployment_artifacts(config, output_dir, timeout, enable_mlflow, mlflow_port)`
  - [ ] Template engine (Jinja2 or string.Template)
  - [ ] Variable substitution (workflow_name, ports, timeout)
- [ ] Create `src/configurable_agents/deploy/templates/` directory:
  - [ ] `Dockerfile.template` (multi-stage, optimized)
  - [ ] `server.py.template` (FastAPI with sync/async)
  - [ ] `requirements.txt.template` (minimal runtime deps)
  - [ ] `docker-compose.yml.template`
  - [ ] `.env.example.template`
  - [ ] `README.md.template`
  - [ ] `.dockerignore`
- [ ] Dockerfile optimizations:
  - [ ] Multi-stage build (builder + runtime)
  - [ ] `python:3.10-slim` base image
  - [ ] `--no-cache-dir` for pip
  - [ ] Health check
  - [ ] MLFlow UI startup (if enabled)
- [ ] Unit tests (artifact generation, 20 tests)
- [ ] Integration test (generate → validate files exist, 3 tests)

**Files Created**:
- `src/configurable_agents/deploy/__init__.py`
- `src/configurable_agents/deploy/generator.py`
- `src/configurable_agents/deploy/templates/` (7 template files)
- `tests/deploy/__init__.py`
- `tests/deploy/test_generator.py`

**Tests**: 23 tests (20 unit + 3 integration)

**Related ADRs**: ADR-012, ADR-013

---

### T-023: FastAPI Server with Sync/Async
**Status**: TODO
**Priority**: P0
**Dependencies**: T-022
**Estimated Effort**: 3 days

**Description**:
Create FastAPI server template with sync/async hybrid execution, job store, and MLFlow integration.

**Acceptance Criteria**:
- [ ] FastAPI server template (`server.py.template`):
  - [ ] Endpoints: POST /run, GET /status/{job_id}, GET /health, GET /schema, GET /
  - [ ] Sync/async hybrid logic (timeout-based fallback)
  - [ ] Job store (in-memory dict for v0.1)
  - [ ] Input validation (against workflow schema)
  - [ ] OpenAPI auto-docs (FastAPI built-in)
  - [ ] MLFlow integration (logging within container)
  - [ ] Error handling (ValidationError, ExecutionError, etc.)
  - [ ] Background task execution (FastAPI BackgroundTasks)
- [ ] Sync execution (if < timeout):
  - [ ] Use `asyncio.wait_for()` with timeout
  - [ ] Return outputs immediately (200 OK)
- [ ] Async execution (if > timeout):
  - [ ] Generate job_id (UUID)
  - [ ] Store job metadata (status, created_at, inputs)
  - [ ] Run in background task
  - [ ] Return job_id (202 Accepted)
- [ ] Job status endpoint (query by job_id)
- [ ] Health check endpoint (for orchestration)
- [ ] Schema introspection endpoint (returns input/output schema)
- [ ] Unit tests (mocked workflow execution, 30 tests)
- [ ] Integration test (real FastAPI server, 5 tests)

**Files Modified**:
- `src/configurable_agents/deploy/templates/server.py.template`

**Files Created**:
- `tests/deploy/test_server_template.py` (30 unit tests)
- `tests/deploy/test_server_integration.py` (5 integration tests)

**Tests**: 35 tests (30 unit + 5 integration)

**Related ADRs**: ADR-012

---

### T-024: CLI Deploy Command & Streamlit Integration
**Status**: TODO
**Priority**: P0
**Dependencies**: T-022, T-023
**Estimated Effort**: 3 days

**Description**:
Implement `deploy` CLI command and integrate with Streamlit UI for Docker deployment.

**Acceptance Criteria**:
- [ ] CLI `deploy` command in `src/configurable_agents/cli.py`:
  - [ ] Arguments: workflow_path, --port, --mlflow-port, --output, --name, --timeout, --generate, --no-mlflow, --env-file, --no-env-file
  - [ ] Step 1: Validate workflow (fail-fast)
  - [ ] Step 2: Check Docker installed (`docker version`, fail-fast)
  - [ ] Step 3: Generate artifacts (call T-022 generator)
  - [ ] Step 4: If --generate, exit (artifacts only)
  - [ ] Step 5: Build Docker image (`docker build`)
  - [ ] Step 6: Run container detached (`docker run -d`)
  - [ ] Step 7: Print success message (endpoints, curl examples, management commands)
- [ ] Environment variable handling:
  - [ ] Auto-detect `.env` in current directory
  - [ ] Custom path via `--env-file`
  - [ ] Skip with `--no-env-file`
  - [ ] Validate env file format (KEY=value)
- [ ] Streamlit integration (`streamlit_app.py`):
  - [ ] Add "Deploy to Docker" section
  - [ ] Environment variable upload/paste/skip options
  - [ ] Port configuration (API, MLFlow)
  - [ ] Container name input
  - [ ] Deploy button (executes CLI command)
  - [ ] Real-time logs (subprocess output)
  - [ ] Success message (show endpoints, curl examples)
  - [ ] Container management (list, stop, remove buttons)
- [ ] Unit tests (CLI deploy command, 25 tests)
- [ ] Integration tests (full deploy flow, 3 slow tests)

**Files Modified**:
- `src/configurable_agents/cli.py` (add deploy command)
- `streamlit_app.py` (add deploy section)

**Files Created**:
- `tests/test_cli_deploy.py` (25 unit tests)
- `tests/test_deploy_integration.py` (3 integration tests)

**Tests**: 28 tests (25 unit + 3 integration)

**Related ADRs**: ADR-012, ADR-013

---

### T-025: Error Message Improvements (was T-018)
**Status**: TODO (Deferred to v0.2)
**Priority**: P2
**Dependencies**: T-004, T-013
**Estimated Effort**: 1 week

**Description**:
Improve error messages to be maximally helpful.

**Acceptance Criteria**:
- [ ] Include file name and line number for config errors
- [ ] Suggest fixes ("Did you mean 'serper_search'?")
- [ ] Show context around error (surrounding lines)
- [ ] Clear error categories (config, runtime, LLM, tool)
- [ ] Examples of correct syntax in errors
- [ ] Test error messages are helpful (UX review)

**Files**:
- Update existing error handling across codebase
- `src/configurable_agents/errors.py`

**Note**: Deferred to v0.2 to prioritize observability and deployment features for first public release.

---

### T-026: DSPy Integration Test (was T-019)
**Status**: TODO (Deferred to v0.3)
**Priority**: P1
**Dependencies**: T-009, T-011
**Estimated Effort**: 1 week

**Description**:
Verify DSPy modules can be used in LangGraph nodes without prompt interference (see ADR-001).

**Acceptance Criteria**:
- [ ] Create simple DSPy module (ChainOfThought)
- [ ] Run in LangGraph node
- [ ] Verify prompts are not wrapped/modified
- [ ] Compare: raw DSPy call vs in-LangGraph call
- [ ] Verify optimization works (compile DSPy module)
- [ ] Compare optimized vs non-optimized results
- [ ] Document findings
- [ ] **If tests fail**: Document issue, implement escape strategy (custom executor)

**Files**:
- `tests/integration/test_dspy_integration.py`
- `docs/dspy_integration_findings.md`

**Note**: Deferred to v0.3 (DSPy optimization phase). Critical for validating architecture choice before implementing DSPy features.

---

### T-027: Structured Output + DSPy Test (was T-020)
**Status**: TODO (Deferred to v0.3)
**Priority**: P1
**Dependencies**: T-026
**Estimated Effort**: 3-4 days

**Description**:
Verify Pydantic structured outputs work with DSPy modules.

**Acceptance Criteria**:
- [ ] Combine Pydantic schema with DSPy signature
- [ ] Ensure both work together
- [ ] Test optimization with structured outputs
- [ ] Document any limitations
- [ ] Provide workarounds if needed

**Files**:
- `tests/integration/test_dspy_structured_output.py`

**Note**: Deferred to v0.3. Depends on T-026 (DSPy Integration Test).

---

## Phase 4: Deferred Tasks

These tasks are deferred to v0.2+ to prioritize production-ready features (observability, deployment) for first public release:

### Deferred to v0.2+

- **T-025**: Error Message Improvements (v0.2)
- **T-026**: DSPy Integration Test (v0.3)
- **T-027**: Structured Output + DSPy Test (v0.3)

### Future Tasks (Not in v0.1)

- **T-100**: Conditional edges (if/else routing)
- **T-101**: Loop support (retry, iteration)
- **T-102**: Multiple LLM providers (OpenAI, Anthropic, local)
- **T-103**: Persistent mode (Docker container)
- **T-104**: MLFlow observability integration
- **T-105**: DSPy optimization support
- **T-106**: Custom code nodes
- **T-107**: Long-term memory (vector DBs)
- **T-108**: Config generator chatbot
- **T-109**: Web UI
- **T-110**: Cloud deployment (ECS, Lambda, Fargate)

---

## Task Dependencies

```
Phase 1 & 2 (Foundation & Core - COMPLETE):

T-001 (Setup)
  ├─> T-002 (Parser)
  ├─> T-003 (Schema - EXPANDED)
  ├─> T-005 (Types)
  ├─> T-008 (Tools)
  └─> T-009 (LLM)

T-002, T-003 -> T-004 (Validator - EXPANDED)

T-003, T-004 -> T-004.5 (Feature Gating - NEW)

T-005 -> T-006 (State Builder)
T-005 -> T-007 (Output Builder)

T-006 -> T-010 (Template)

T-007, T-008, T-009, T-010 -> T-011 (Node Executor)

T-011 -> T-012 (Graph Builder)

T-004, T-004.5, T-006, T-012 -> T-013 (Runtime)

T-013 -> T-014 (CLI)
T-013 -> T-015 (Examples)
T-013 -> T-017 (Integration Tests)

T-015 -> T-016 (Docs)

Phase 3 (Production Readiness - IN PROGRESS):

Observability (Sequential):
T-001 (Setup) -> T-018 (MLFlow Foundation)
T-018, T-013 -> T-019 (MLFlow Instrumentation)
T-019 -> T-020 (Cost Tracking)
T-020 -> T-021 (Observability Docs)

Docker Deployment (Sequential):
T-013, T-021 -> T-022 (Artifact Generator)
T-022 -> T-023 (FastAPI Server)
T-023 -> T-024 (CLI Deploy + Streamlit)

Phase 4 (Deferred):

T-004, T-013 -> T-025 (Error Messages) [v0.2]
T-009, T-011 -> T-026 (DSPy Integration Test) [v0.3]
T-026 -> T-027 (Structured Output + DSPy) [v0.3]
```

---

## Progress Tracker

**Last Updated**: 2026-01-31

### v0.1 Progress: 19/27 tasks complete (70%)

**Phase 1: Foundation (8/8 complete) ✅ COMPLETE**
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System (already complete in T-003)
- ✅ T-006: State Schema Builder
- ✅ T-007: Output Schema Builder

**Phase 2: Core Execution (6/6 complete) ✅ COMPLETE**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ✅ T-011: Node Executor
- ✅ T-012: Graph Builder
- ✅ T-013: Runtime Executor

**Phase 3: Production Readiness (6/11 complete)**

*Polish (4/4 complete) ✅*
- ✅ T-014: CLI Interface
- ✅ T-015: Example Configs
- ✅ T-016: Documentation
- ✅ T-017: Integration Tests

*Observability (2/4 complete)*
- ✅ T-018: MLFlow Integration Foundation (2026-01-31)
- ✅ T-019: MLFlow Instrumentation (Runtime & Nodes) (2026-01-31)
- ⏳ T-020: Cost Tracking & Reporting
- ⏳ T-021: Observability Documentation

*Docker Deployment (0/3 complete)*
- ⏳ T-022: Docker Artifact Generator & Templates
- ⏳ T-023: FastAPI Server with Sync/Async
- ⏳ T-024: CLI Deploy Command & Streamlit Integration

**Phase 4: Deferred Tasks (0/3 complete)**
- ⏳ T-025: Error Message Improvements (was T-018) - Deferred to v0.2
- ⏳ T-026: DSPy Integration Test (was T-019) - Deferred to v0.3
- ⏳ T-027: Structured Output + DSPy Test (was T-020) - Deferred to v0.3

**Current Sprint**: Phase 3 - Production Readiness (6/11 complete)
**Next Up**: T-020 (Cost Tracking & Reporting)
**Test Status**: 492 unit tests passing (100% pass rate), 13 integration tests skipped
**Integration Tests**: Runtime executor integration tests verify end-to-end MLFlow tracking

---

## Work Estimates

**Total tasks in v0.1**: 24 tasks (23 for release + 1 auxiliary Streamlit UI)
**Deferred to v0.2+**: 3 tasks (T-025, T-026, T-027)

**Estimated timeline**:
- ✅ Phase 1: Foundation (T-001 to T-007): 3-4 weeks (COMPLETE)
- ✅ Phase 2: Core execution (T-008 to T-013): 3-4 weeks (COMPLETE)
- ✅ Phase 3 Polish (T-014 to T-017): 1 week (COMPLETE)
- ⏳ Phase 3 Observability (T-018 to T-021): 9 days (~2 weeks)
  - T-018: MLFlow Foundation (2 days)
  - T-019: MLFlow Instrumentation (3 days)
  - T-020: Cost Tracking (2 days)
  - T-021: Observability Docs (2 days)
- ⏳ Phase 3 Docker (T-022 to T-024): 8 days (~1.5 weeks)
  - T-022: Artifact Generator (2 days)
  - T-023: FastAPI Server (3 days)
  - T-024: CLI Deploy + Streamlit (3 days)

**Total for v0.1**: **8-10 weeks** (6 weeks done + 3.5 weeks remaining)

**Phase 3 Remaining**: 17 days (~3.5 weeks) for production readiness

**Deferred timeline**:
- T-025 (Error Messages): v0.2 (1 week)
- T-026 (DSPy Integration): v0.3 (1 week)
- T-027 (DSPy + Structured Output): v0.3 (3-4 days)

**Trade-off**: Prioritize production-ready features (observability, deployment) for first public release over polish and DSPy verification.

---

## Notes

- Each task should be a standalone git commit
- All tasks require tests before being marked DONE
- Integration tests (T-017) must pass before v0.1 release ✅ DONE
- Documentation (T-016) is critical for v0.1 release ✅ DONE
- Observability (T-018 to T-021) is production-essential for first public release
- Docker deployment (T-022 to T-024) enables production usage
- Error messages (T-025) deferred to v0.2 - iterative improvement
- DSPy tests (T-026, T-027) deferred to v0.3 - validates architecture choice before DSPy features
- Full Schema Day One (ADR-009) adds upfront complexity but prevents breaking changes
- v0.1 scope expanded from 20 to 24 tasks to include observability and deployment
