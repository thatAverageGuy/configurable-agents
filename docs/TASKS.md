# Work Breakdown

**Version**: v0.1 (Schema v1.0)
**Last Updated**: 2026-01-24

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
**Status**: TODO
**Priority**: P0
**Dependencies**: T-007, T-008, T-009, T-010
**Estimated Effort**: 1.5 weeks

**Description**:
Execute a single node (LLM call with tools, type-enforced output).

**Acceptance Criteria**:
- [ ] Resolve input mappings from state
- [ ] Resolve prompt from state/inputs
- [ ] Load tools from registry
- [ ] Configure LLM (merge global + node config)
- [ ] Call LLM with structured output (Pydantic model)
- [ ] Validate output against schema
- [ ] Retry on validation failure (with clarified prompt)
- [ ] Update state with outputs
- [ ] Handle errors:
  - [ ] LLM timeout
  - [ ] Tool failure
  - [ ] Schema mismatch (retry)
  - [ ] Type validation failure
- [ ] Log node execution (inputs, outputs, time, cost)
- [ ] Unit tests (mock LLM, tools)
- [ ] Integration tests with real LLM

**Files**:
- `src/configurable_agents/core/node_executor.py`
- `tests/core/test_node_executor.py`

**Interface**:
```python
def execute_node(
    node_config: NodeConfig,
    state: BaseModel,
    global_config: GlobalConfig
) -> BaseModel:
    """Execute node and return updated state"""
```

---

### T-012: Graph Builder
**Status**: TODO
**Priority**: P0
**Dependencies**: T-011
**Estimated Effort**: 1.5 weeks

**Description**:
Build LangGraph StateGraph from config. v0.1: Linear flows only.

**Acceptance Criteria**:
- [ ] Create StateGraph instance
- [ ] Add nodes from config
- [ ] Add edges from config (linear only)
- [ ] Validate graph structure (no cycles, reachable)
- [ ] Compile graph
- [ ] Reject conditional routing (feature gate)
- [ ] Unit tests (mock node execution)
- [ ] Integration tests with real nodes

**Files**:
- `src/configurable_agents/core/graph_builder.py`
- `tests/core/test_graph_builder.py`

**Interface**:
```python
def build_graph(
    config: WorkflowConfig,
    state_model: Type[BaseModel]
) -> CompiledGraph:
    """Build LangGraph from config"""
```

---

### T-013: Runtime Executor
**Status**: TODO
**Priority**: P0
**Dependencies**: T-004, T-004.5, T-006, T-012
**Estimated Effort**: 1.5 weeks

**Description**:
Main entry point that orchestrates config → execution.

**Acceptance Criteria**:
- [ ] Load and parse config (YAML/JSON)
- [ ] Validate config (T-004)
- [ ] Check runtime support (T-004.5)
- [ ] Build state model
- [ ] Initialize state with inputs
- [ ] Build and compile graph
- [ ] Execute graph
- [ ] Return final state as dict
- [ ] Handle all error types gracefully:
  - [ ] Config validation errors
  - [ ] Runtime feature errors
  - [ ] Node execution errors
  - [ ] Graph execution errors
- [ ] Log workflow execution (start, end, duration, cost)
- [ ] Integration tests with example configs

**Files**:
- `src/configurable_agents/runtime/executor.py`
- `tests/runtime/test_executor.py`

**Interface**:
```python
def run_workflow(
    config_path: str,
    inputs: dict
) -> dict:
    """Execute workflow from config file and return final state"""

def run_workflow_from_config(
    config: WorkflowConfig,
    inputs: dict
) -> dict:
    """Execute workflow from pre-loaded config"""
```

---

### T-014: CLI Interface
**Status**: TODO
**Priority**: P1
**Dependencies**: T-013
**Estimated Effort**: 1 week

**Description**:
Command-line interface for running and validating workflows.

**Acceptance Criteria**:
- [ ] `run` command: execute workflow from file
- [ ] `validate` command: validate config without running
- [ ] Parse command-line arguments for inputs
- [ ] Pretty-print output (use rich or similar)
- [ ] Show helpful error messages
- [ ] Support --input flag for inputs
- [ ] Support --verbose flag for debug logging
- [ ] Integration tests

**Files**:
- `src/configurable_agents/__main__.py`
- `src/configurable_agents/cli.py`
- `tests/test_cli.py`

**Usage**:
```bash
python -m configurable_agents run workflow.yaml --input topic="AI Safety"
python -m configurable_agents validate workflow.yaml
python -m configurable_agents run workflow.yaml --verbose
```

---

### T-015: Example Configs
**Status**: TODO
**Priority**: P1
**Dependencies**: T-013
**Estimated Effort**: 3-4 days

**Description**:
Create example workflow configs using Schema v1.0 format.

**Acceptance Criteria**:
- [ ] Simple echo workflow (minimal example)
- [ ] Article writer workflow (with tools, multi-step)
- [ ] Nested state example
- [ ] Type enforcement example (int, list, object outputs)
- [ ] All examples work end-to-end
- [ ] Include in documentation
- [ ] Each example has README explaining it

**Files**:
- `examples/echo.yaml`
- `examples/article_writer.yaml`
- `examples/nested_state.yaml`
- `examples/type_enforcement.yaml`
- `examples/README.md`

---

### T-016: Documentation
**Status**: TODO
**Priority**: P1
**Dependencies**: T-015
**Estimated Effort**: 1 week

**Description**:
Write user-facing documentation.

**Acceptance Criteria**:
- [ ] README.md with quickstart
- [ ] Installation instructions
- [ ] Environment setup guide (API keys)
- [ ] Config schema reference (reference SPEC.md)
- [ ] Example walkthrough
- [ ] Troubleshooting guide
- [ ] Version availability table (what's in v0.1 vs v0.2 vs v0.3)
- [ ] Roadmap

**Files**:
- `README.md`
- `docs/QUICKSTART.md`
- `docs/CONFIG_REFERENCE.md`
- `docs/ROADMAP.md`
- `docs/TROUBLESHOOTING.md`

---

### T-017: Integration Tests
**Status**: TODO
**Priority**: P0
**Dependencies**: T-013, T-015
**Estimated Effort**: 1 week

**Description**:
End-to-end integration tests with real LLM calls.

**Acceptance Criteria**:
- [ ] Test each example config
- [ ] Test with real Google Gemini API
- [ ] Test error scenarios:
  - [ ] Invalid config
  - [ ] Missing API key
  - [ ] LLM timeout
  - [ ] Tool failure
- [ ] Test with tools (serper_search)
- [ ] Test type enforcement (wrong types rejected)
- [ ] Mark as slow tests (skip in CI if needed)
- [ ] Generate test report with costs

**Files**:
- `tests/integration/test_workflows.py`
- `tests/integration/test_error_scenarios.py`

---

### T-018: Error Message Improvements
**Status**: TODO
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

---

### T-019: DSPy Integration Test - NEW
**Status**: TODO
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

---

### T-020: Structured Output + DSPy Test - NEW
**Status**: TODO
**Priority**: P1
**Dependencies**: T-019
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

---

## Phase 2: Enhancements (v0.2+)

These are deferred to later versions:

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

T-004, T-013 -> T-018 (Error Messages)

T-009, T-011 -> T-019 (DSPy Integration Test - NEW)
T-019 -> T-020 (Structured Output + DSPy - NEW)
```

---

## Progress Tracker

**Last Updated**: 2026-01-26

### v0.1 Progress: 11/20 tasks complete (55%)

**Phase 1: Foundation (8/8 complete) ✅ COMPLETE**
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System (already complete in T-003)
- ✅ T-006: State Schema Builder
- ✅ T-007: Output Schema Builder

**Phase 2: Core Execution (3/6 complete) - IN PROGRESS**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor (NEXT)
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

**Phase 3: Polish & UX (0/5 complete)**
- ⏳ T-014: CLI Interface
- ⏳ T-015: Example Configs
- ⏳ T-016: Documentation
- ⏳ T-017: Integration Tests
- ⏳ T-018: Error Message Improvements

**Phase 4: DSPy Verification (0/2 complete)**
- ⏳ T-019: DSPy Integration Test
- ⏳ T-020: Structured Output + DSPy Test

**Current Sprint**: Phase 2 - Core Execution (3/6 complete)
**Test Status**: 344 tests passing (44 template + 32 llm + 37 tools + 29 output + 30 state + 29 validator + 19 runtime + 67 schema + 31 types + 18 parser + 5 integration + 3 setup)

---

## Work Estimates

**Total tasks in v0.1**: 20 tasks (was 18, added T-019, T-020)

**Estimated timeline**:
- Foundation (T-001 to T-007): 3-4 weeks (expanded scope)
- Core execution (T-008 to T-013): 3-4 weeks
- Polish (T-014 to T-018): 1.5 weeks
- DSPy verification (T-019, T-020): 1.5 weeks

**Total for v0.1**: **6-8 weeks** with comprehensive testing

**Previous estimate**: 4-6 weeks (before Full Schema Day One)

**Additional time breakdown**:
- Full schema Pydantic models: +1 week (T-003 expanded)
- Extended validation: +1 week (T-004 expanded)
- Feature gating: +2-3 days (T-004.5 new)
- DSPy verification: +1.5 weeks (T-019, T-020 new)

**Trade-off**: Worth it - better foundation, no breaking changes, future-proof.

---

## Notes

- Each task should be a standalone git commit
- All tasks require tests before being marked DONE
- Integration tests (T-017) must pass before v0.1 release
- DSPy tests (T-019, T-020) are critical for validating architecture choice
- Error messages (T-018) can be iterative improvement
- Documentation (T-016) is critical for v0.1 release
- Full Schema Day One (ADR-009) adds upfront complexity but prevents breaking changes
