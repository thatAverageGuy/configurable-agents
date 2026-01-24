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

**Files Created**:
- `pyproject.toml`
- `src/configurable_agents/__init__.py` (+ all submodule `__init__.py`)
- `src/configurable_agents/logging_config.py`
- `.env.example`
- `pytest.ini`
- `.gitignore` (updated)
- `tests/__init__.py`, `tests/conftest.py`, `tests/test_setup.py`
- `SETUP.md`

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
- [x] Unit tests for valid and invalid YAML/JSON (24 tests created)

**Files**:
- `src/configurable_agents/config/parser.py`
- `tests/config/test_parser.py`

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
**Status**: TODO
**Priority**: P0
**Dependencies**: T-001
**Estimated Effort**: 2 weeks

**Description**:
Define complete Pydantic models for Schema v1.0. Full schema from day one (see ADR-009).

**Acceptance Criteria**:
- [ ] `WorkflowConfig` (top-level)
- [ ] `FlowMetadata` (name, version, description)
- [ ] `StateSchema` with:
  - [ ] Basic types (str, int, float, bool)
  - [ ] Collection types (list, dict, list[str], etc.)
  - [ ] Nested objects (object with schema)
  - [ ] Required/default fields
  - [ ] Field descriptions
- [ ] `NodeConfig` with:
  - [ ] Input mapping (dict)
  - [ ] Output schema (object or simple type)
  - [ ] Tools list
  - [ ] Node-level optimization config
  - [ ] Node-level LLM overrides
- [ ] `EdgeConfig` with:
  - [ ] Linear edges (from, to)
  - [ ] Conditional routes (list of conditions)
- [ ] `OptimizationConfig` (DSPy settings - v0.3+)
- [ ] `GlobalConfig` (LLM, execution, observability)
- [ ] JSON Schema export (for IDE autocomplete)
- [ ] Comprehensive unit tests:
  - [ ] Valid configs pass
  - [ ] Invalid configs fail with good errors
  - [ ] Nested structures validated
  - [ ] Type validation works
  - [ ] Optional fields work
  - [ ] Future features (optimization, conditionals) validate

**Files**:
- `src/configurable_agents/config/schema.py`
- `src/configurable_agents/config/types.py` (type parsing utilities)
- `tests/config/test_schema.py`
- `tests/config/test_types.py`

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
**Status**: TODO
**Priority**: P0
**Dependencies**: T-002, T-003
**Estimated Effort**: 2 weeks

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
**Status**: TODO
**Priority**: P0
**Dependencies**: T-003, T-004
**Estimated Effort**: 2-3 days

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
**Status**: TODO
**Priority**: P0
**Dependencies**: T-001
**Estimated Effort**: 1 week

**Description**:
Implement type parsing and validation for config type strings.

**Acceptance Criteria**:
- [ ] Parse basic types: `str`, `int`, `float`, `bool`
- [ ] Parse collection types: `list`, `dict`, `list[str]`, `list[int]`, `dict[str, int]`
- [ ] Parse nested object type with schema
- [ ] Convert type strings to Python types
- [ ] Validate type strings are valid
- [ ] Support type descriptions
- [ ] Unit tests for all supported types
- [ ] Error messages for invalid types

**Files**:
- `src/configurable_agents/core/types.py`
- `tests/core/test_types.py`

**Interface**:
```python
def parse_type(type_str: str) -> Type:
    """Convert type string to Python type"""

def validate_type_string(type_str: str) -> bool:
    """Check if type string is valid"""
```

---

### T-006: State Schema Builder
**Status**: TODO
**Priority**: P0
**Dependencies**: T-005
**Estimated Effort**: 1 week

**Description**:
Dynamically generate Pydantic state models from config. Supports nested objects.

**Acceptance Criteria**:
- [ ] Create Pydantic `BaseModel` from state config
- [ ] Support all type system types
- [ ] Handle required fields
- [ ] Handle default values
- [ ] Support nested objects (recursive schema building)
- [ ] Validate state at instantiation
- [ ] Include field descriptions in model
- [ ] Unit tests with various state schemas:
  - [ ] Simple flat state
  - [ ] Nested state (1 level)
  - [ ] Deeply nested state (3+ levels)
  - [ ] All type combinations

**Files**:
- `src/configurable_agents/core/state_builder.py`
- `tests/core/test_state_builder.py`

**Interface**:
```python
def build_state_model(state_config: StateSchema) -> Type[BaseModel]:
    """Create Pydantic state model from config"""
```

---

### T-007: Output Schema Builder
**Status**: TODO
**Priority**: P0
**Dependencies**: T-005
**Estimated Effort**: 1 week

**Description**:
Dynamically generate Pydantic output models for node outputs. This enables type enforcement.

**Acceptance Criteria**:
- [ ] Create Pydantic model from `output_schema` config
- [ ] Support all type system types
- [ ] Include field descriptions (helps LLM)
- [ ] Support simple output (single type)
- [ ] Support object output (multiple fields)
- [ ] Unit tests with various output schemas:
  - [ ] Simple string output
  - [ ] Object with multiple fields
  - [ ] Nested object output
  - [ ] List and dict outputs

**Files**:
- `src/configurable_agents/core/output_builder.py`
- `tests/core/test_output_builder.py`

**Interface**:
```python
def build_output_model(output_schema: dict, node_id: str) -> Type[BaseModel]:
    """Create Pydantic output model from config"""
```

---

### T-008: Tool Registry
**Status**: TODO
**Priority**: P1
**Dependencies**: T-001
**Estimated Effort**: 1 week

**Description**:
Implement tool registry that loads tools by name. v0.1 includes `serper_search`.

**Acceptance Criteria**:
- [ ] Registry interface to get tool by name
- [ ] Implement `serper_search` tool using LangChain
- [ ] Load API keys from environment
- [ ] Fail loudly if tool not found
- [ ] Fail loudly if API key missing (with helpful message)
- [ ] List available tools
- [ ] Unit tests (mock tool loading)
- [ ] Integration test with real Serper API (optional, slow)

**Files**:
- `src/configurable_agents/tools/registry.py`
- `src/configurable_agents/tools/serper.py`
- `tests/tools/test_registry.py`
- `tests/tools/test_serper.py`

**Interface**:
```python
def get_tool(tool_name: str) -> BaseTool:
    """Get tool by name from registry"""

def list_tools() -> list[str]:
    """List all available tool names"""
```

---

### T-009: LLM Provider
**Status**: TODO
**Priority**: P0
**Dependencies**: T-001, T-007
**Estimated Effort**: 1 week

**Description**:
Implement LLM provider for Google Gemini with structured outputs (type enforcement).

**Acceptance Criteria**:
- [ ] Initialize LLM with config (model, temperature, max_tokens)
- [ ] Call LLM with structured output (Pydantic schema)
- [ ] Handle API errors gracefully
- [ ] Read API key from environment
- [ ] Retry on rate limit (exponential backoff)
- [ ] Log API calls (prompt, response, cost estimate)
- [ ] Unit tests (mock LLM calls)
- [ ] Integration test with real Gemini API (optional, slow)
- [ ] **Verification**: Compare raw API call vs LangChain - ensure prompts match (ADR-001)

**Files**:
- `src/configurable_agents/llm/provider.py`
- `src/configurable_agents/llm/google.py`
- `tests/llm/test_provider.py`
- `tests/llm/test_google.py`

**Interface**:
```python
def create_llm(llm_config: dict) -> ChatGoogleGenerativeAI:
    """Create LLM instance from config"""

def call_llm_structured(
    llm: ChatGoogleGenerativeAI,
    prompt: str,
    output_model: Type[BaseModel],
    tools: list[BaseTool] = None
) -> BaseModel:
    """Call LLM with structured output"""
```

---

### T-010: Prompt Template Resolver
**Status**: TODO
**Priority**: P0
**Dependencies**: T-006
**Estimated Effort**: 3-4 days

**Description**:
Resolve `{variable}` placeholders in prompt templates from state or input mappings.

**Acceptance Criteria**:
- [ ] Parse prompt templates
- [ ] Extract variable references
- [ ] Resolve from input mappings (if provided)
- [ ] Resolve from state fields (fallback)
- [ ] Handle missing variables gracefully (error)
- [ ] Support nested state access: `{state.metadata.author}`
- [ ] Unit tests with various templates:
  - [ ] Simple placeholders
  - [ ] Nested placeholders
  - [ ] Mixed input mappings and state
  - [ ] Missing variable errors

**Files**:
- `src/configurable_agents/core/template.py`
- `tests/core/test_template.py`

**Interface**:
```python
def resolve_prompt(
    prompt_template: str,
    inputs: dict,  # From node.inputs mapping
    state: BaseModel
) -> str:
    """Resolve {variable} placeholders in prompt"""
```

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

**Last Updated**: 2026-01-24

### v0.1 Progress: 2/20 tasks complete (10%)

**Phase 1: Foundation (2/7 complete)**
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ⏳ T-003: Config Schema (Pydantic Models)
- ⏳ T-004: Config Validator
- ⏳ T-004.5: Runtime Feature Gating
- ⏳ T-005: Type System
- ⏳ T-006: State Schema Builder
- ⏳ T-007: Output Schema Builder

**Phase 2: Core Execution (0/6 complete)**
- ⏳ T-008: Tool Registry
- ⏳ T-009: LLM Provider
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
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

**Current Sprint**: Foundation Phase (T-002 next)

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
