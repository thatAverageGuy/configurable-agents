# ADR-003: Config-Driven Architecture

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

Users want to go from idea to production agent system quickly. The traditional path involves:

1. Write Python code for workflow
2. Hardcode prompts, models, logic
3. Test manually
4. Deploy with custom infrastructure
5. Repeat for every new workflow

**Pain points**:
- High barrier to entry (must know Python, LangChain, etc.)
- Slow iteration (code → test → deploy cycle)
- Hard to share/version workflows
- Each deployment is bespoke

**User request**: "I want to describe a workflow and have it running in minutes, not days."

---

## Decision

**Build a config-driven architecture where YAML configuration is the single source of truth.**

The system will:
1. Read YAML config describing workflow
2. Dynamically generate execution graph
3. Run workflow with given inputs
4. Return outputs

**No code required for users.** The config IS the application.

---

## What This Means

### Before (Code-Based)

```python
# user_workflow.py
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

class State(TypedDict):
    topic: str
    research: str
    article: str

def research_node(state: State) -> State:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
    prompt = f"Research: {state['topic']}"
    result = llm.invoke(prompt)
    state['research'] = result.content
    return state

def write_node(state: State) -> State:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
    prompt = f"Write article about {state['topic']} using {state['research']}"
    result = llm.invoke(prompt)
    state['article'] = result.content
    return state

graph = StateGraph(State)
graph.add_node("research", research_node)
graph.add_node("write", write_node)
graph.add_edge("research", "write")
app = graph.compile()

# Run it
result = app.invoke({"topic": "AI Safety"})
```

**To deploy**: Package code, create Dockerfile, deploy to cloud, expose API, etc.

**To modify**: Edit code, test, redeploy.

**To share**: Share Python code (requires understanding LangGraph).

### After (Config-Based)

```yaml
# article_writer.yaml
flow:
  name: article_writer

state:
  fields:
    topic: {type: str, required: true}
    research: {type: str, default: ""}
    article: {type: str, default: ""}

nodes:
  - id: research
    prompt: "Research: {state.topic}"
    outputs: [research]
    output_schema:
      fields:
        - name: research
          type: str

  - id: write
    prompt: "Write article about {state.topic} using {state.research}"
    outputs: [article]
    output_schema:
      fields:
        - name: article
          type: str

edges:
  - {from: START, to: research}
  - {from: research, to: write}
  - {from: write, to: END}

config:
  llm:
    model: gemini-2.0-flash-exp
```

**To run**:
```bash
python -m configurable_agents run article_writer.yaml --input topic="AI Safety"
```

**To deploy** (v0.2+):
```bash
python -m configurable_agents deploy article_writer.yaml --platform docker
```

**To modify**: Edit YAML, re-run.

**To share**: Share YAML file (no code knowledge needed).

---

## Rationale

### 1. Accessibility

**Non-developers can create workflows**:
- Product managers can prototype agent ideas
- Researchers can experiment with agent architectures
- Consultants can build PoCs for clients

No Python knowledge required.

### 2. Fast Iteration

**Edit-and-run cycle**:
```
Edit YAML → Run → See results
  (~10 seconds)
```

vs

```
Edit code → Save → Restart → Run → See results
  (~30-60 seconds)
```

For experimentation, speed matters.

### 3. Versioning and Collaboration

**YAML configs are git-friendly**:
```bash
git diff article_writer.yaml

- model: gemini-2.0-flash-exp
+ model: gemini-2.0-flash-lite

- temperature: 0.7
+ temperature: 0.9
```

Clear, reviewable changes. Can track evolution over time.

### 4. Portability

**Same config works everywhere**:
- Local machine
- Docker container
- Cloud deployment
- CI/CD pipeline

No environment-specific code.

### 5. Tooling Potential

**Config-as-code enables**:
- Visual editors (drag-and-drop config generation)
- Config validators (linters)
- Config optimizers (DSPy can optimize prompts in config)
- Config templates (starter workflows)
- Config marketplace (share workflows)

### 6. Separation of Concerns

**Clear boundaries**:
- **Config**: What the workflow does (domain logic)
- **Runtime**: How it's executed (infrastructure)

Users focus on domain logic. We handle infrastructure.

---

## Alternatives Considered

### Alternative 1: Code-First (Python Library)

```python
from configurable_agents import Workflow, Node

workflow = Workflow("article_writer")
workflow.add_node(
    Node("research")
    .prompt("Research: {topic}")
    .output_schema({"research": str})
)
workflow.add_edge("research", "write")
```

**Pros**:
- Familiar to developers
- IDE support (autocomplete, type checking)
- More expressive (can use Python logic)

**Cons**:
- **Requires Python knowledge** (excludes non-developers)
- Harder to version (code diffs are noisy)
- Can't easily generate from chatbot
- Deployment requires packaging code

**Why rejected**: Doesn't meet the "anyone can use" goal.

### Alternative 2: JSON Config

```json
{
  "flow": {"name": "article_writer"},
  "nodes": [...]
}
```

**Pros**:
- Machine-readable
- Widespread tooling

**Cons**:
- **Not human-friendly** (no comments, verbose syntax)
- Hard to edit manually
- Poor for multi-line strings (prompts)

**Why rejected**: YAML is more human-readable.

### Alternative 3: Domain-Specific Language (DSL)

```
workflow article_writer:
  state:
    topic: str required
    research: str

  node research:
    prompt "Research: {topic}"
    outputs [research]

  flow:
    research -> write -> end
```

**Pros**:
- Can be more concise
- Tailored to our domain

**Cons**:
- **New syntax to learn**
- Need to build parser
- No existing tooling (editors, linters)
- Harder to extend

**Why rejected**: YAML is familiar and has great tooling.

### Alternative 4: Hybrid (Code + Config)

```yaml
# workflow.yaml
flow:
  name: article_writer
  code: ./custom_logic.py  # External Python file
```

**Pros**:
- Flexibility when needed
- Can use Python for complex logic

**Cons**:
- **Complexity**: Two sources of truth
- Harder to reason about
- Deployment becomes complex again

**Why rejected**: Can add later if needed (v0.2+), but start pure config.

---

## Consequences

### Positive Consequences

1. **Lower Barrier to Entry**
   - Non-developers can create workflows
   - Faster onboarding (understand YAML, not Python/LangChain)

2. **Faster Experimentation**
   - Edit config, re-run instantly
   - No code compilation/restart overhead

3. **Clear Workflows**
   - Config is self-documenting
   - Can visualize from config (future: generate diagrams)

4. **Reproducibility**
   - Same config → same behavior
   - No hidden dependencies

5. **Ecosystem Potential**
   - Share configs on GitHub
   - Config templates for common use cases
   - Chatbot can generate valid configs

6. **DSPy Integration**
   - Configs can be optimized (prompts, model selection)
   - Optimized configs can be shared/versioned

### Negative Consequences

1. **Limited Expressiveness**
   - YAML can't express complex logic (loops with complex conditions, recursion)
   - **Mitigation**: Support 80% of use cases, add custom code option in v0.2+

2. **Runtime Complexity**
   - Dynamic graph generation is more complex than hardcoded
   - **Mitigation**: Thorough testing, clear error messages

3. **Config Verbosity**
   - YAML can be verbose for complex workflows
   - **Mitigation**: Support YAML anchors/aliases, provide templates

4. **Validation Burden**
   - Must validate config thoroughly before execution
   - **Mitigation**: Comprehensive validator (T-004)

5. **Debugging Challenges**
   - Errors happen in generated code, not user's code
   - **Mitigation**: Clear error messages with config context

### Risks

#### Risk 1: Config Schema Becomes Too Complex

**Likelihood**: Medium (as features grow)
**Impact**: High (users can't understand configs)

**Mitigation**:
- Keep v0.1 simple (linear flows only)
- Add complexity incrementally
- Provide config templates and examples
- Build config generator chatbot (v0.3+)

**Example of complexity creep**:
```yaml
# Bad: Too much nesting
nodes:
  - id: research
    conditional:
      if:
        state:
          field: topic_type
          operator: equals
          value: technical
      then:
        llm:
          model: gemini-2.0-flash-exp
          temperature: 0.3
      else:
        llm:
          model: gemini-2.0-flash-lite
          temperature: 0.9
```

**Better approach**: Keep conditionals simple, add advanced features via separate config sections.

#### Risk 2: Config Becomes Turing-Complete

**Likelihood**: Low (we control features)
**Impact**: Medium (defeats simplicity purpose)

**Mitigation**:
- Resist adding loops/recursion to config
- Keep config declarative, not imperative
- For complex logic, require custom code nodes (v0.2+)

**Guard rails**:
- No arbitrary expressions in config
- No eval() of user strings
- Limited set of operators for conditionals

#### Risk 3: Config Validator Bugs

**Likelihood**: Medium (validation is complex)
**Impact**: High (invalid configs pass validation → runtime failures)

**Mitigation**:
- Comprehensive test suite for validator
- Test with adversarial configs (edge cases, malformed)
- Collect real-world configs and test against them

---

## Implementation Strategy

### Phase 1: Core Config Support (v0.1)

**Supported in config**:
- Flow metadata
- State schema
- Nodes (prompts, outputs, schemas)
- Linear edges
- Global config (LLM, execution)

**Explicitly NOT supported**:
- Conditional logic
- Loops
- Custom code
- Dynamic config generation

### Phase 2: Enhanced Config (v0.2)

**Add**:
- Conditional edges (if/else)
- Loop constructs (retry, iterate)
- Config composition (import/extend other configs)

### Phase 3: Advanced Config (v0.3+)

**Add**:
- Custom code nodes (reference Python functions)
- Config generation from chatbot
- Config optimization via DSPy

---

## Config Schema Evolution

As we add features, the config schema will grow. We'll use:

### Versioning

```yaml
flow:
  name: article_writer
  schema_version: "1.0"  # Config schema version
```

### Backwards Compatibility

- Old configs continue to work
- New features are opt-in (default to v1.0 behavior)
- Deprecation warnings for old patterns

### Migration Tools

```bash
# Upgrade config to new schema
python -m configurable_agents upgrade-config article_writer_v1.yaml --to 2.0
```

---

## User Experience

### Creating a Workflow

1. **Start with template**:
   ```bash
   python -m configurable_agents new workflow --template simple
   ```

2. **Edit config**:
   ```yaml
   # Modify prompts, add nodes, configure
   ```

3. **Run** (validation auto-built-in):
   ```bash
   python -m configurable_agents run workflow.yaml --input topic="AI"
   # Config is automatically validated before execution
   ```

4. **Deploy** (v0.2+, validation auto-built-in):
   ```bash
   python -m configurable_agents deploy workflow.yaml --platform docker
   # Config is automatically validated before deployment
   ```

**Optional: Explicit validation** (for development/CI):
```bash
python -m configurable_agents validate workflow.yaml
# Just validates without executing - useful for quick feedback
```

### Sharing a Workflow

```bash
# Export config (with dependencies, example inputs)
python -m configurable_agents export workflow.yaml --output package.zip

# Import someone else's workflow
python -m configurable_agents import package.zip
python -m configurable_agents run imported_workflow.yaml
```

---

## Documentation Strategy

**Must provide**:
1. **Config Reference**: Every field documented
2. **Examples**: 10+ real-world workflows
3. **Templates**: Starter configs for common patterns
4. **Migration Guides**: Upgrading between schema versions
5. **Best Practices**: How to structure complex workflows

---

## References

- YAML spec: https://yaml.org/
- Infrastructure as Code (Terraform): Similar philosophy
- Docker Compose: Config-driven orchestration
- GitHub Actions: Config-driven CI/CD

---

## Notes

This decision is **foundational to the project vision**: "idea to production in minutes."

Config-driven architecture is what enables:
- Chatbot generation (Phase 3)
- Visual editors (Phase 4)
- Config marketplace (Phase 4)
- DSPy optimization (Phase 3)

Without config-as-code, we're just another Python library.

**Key insight**: The config IS the product. The runtime is infrastructure.

---

## Implementation Details

**Status**: ✅ Implemented in v0.1
**Related Tasks**: T-002 (Config Parser), T-003 (Config Schema), T-004 (Config Validator), T-004.5 (Feature Gating), T-010 (Prompt Template)
**Date Implemented**: 2026-01-24 to 2026-01-26

### T-002: Config Parser Implementation

**File**: `src/configurable_agents/config/parser.py` (120 lines)

**Auto-Format Detection**:
```python
def load_config(path: str) -> dict:
    """Load YAML or JSON config (auto-detect from extension)"""
    if path.endswith(('.yaml', '.yml')):
        return _parse_yaml(path)
    elif path.endswith('.json'):
        return _parse_json(path)
    else:
        raise ConfigParserError(f"Unknown format: {path}")
```

**Error Handling**:
- Syntax errors → helpful messages with line numbers
- File not found → clear path reference
- Invalid format → format detection hints

**Test Coverage**: 18 tests (YAML, JSON, errors)

---

### T-003: Config Schema Implementation

**File**: `src/configurable_agents/config/schema.py` (850 lines, 13 Pydantic models)

**Complete Schema Hierarchy**:
```python
class WorkflowConfig(BaseModel):
    schema_version: str = "1.0"
    flow: FlowMetadata
    state: StateSchema
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    optimization: Optional[OptimizationConfig] = None
    config: Optional[GlobalConfig] = None
```

**Full Schema v1.0 (ADR-009)**:
- Supports v0.1 features (linear flows)
- Supports v0.2 features (conditionals, loops) - gated by validator
- Supports v0.3 features (DSPy, parallel execution) - gated by validator
- No breaking changes needed for future versions

**Pydantic Validation Benefits**:
- Type checking at parse time
- Required field enforcement
- Default values
- Custom validators for cross-field checks

**Test Coverage**: 67 schema tests + 5 integration tests

---

### T-004: Config Validator Implementation

**File**: `src/configurable_agents/config/validator.py` (480 lines)

**8-Stage Validation Pipeline**:

```python
def validate_config(config: WorkflowConfig) -> None:
    """Comprehensive validation beyond Pydantic"""

    # Stage 1: Edge references
    _validate_edge_references(config)  # Nodes exist

    # Stage 2: Node outputs
    _validate_node_outputs(config)  # State fields exist

    # Stage 3: Output schema alignment
    _validate_output_schema_alignment(config)  # Schema ↔ outputs match

    # Stage 4: Type alignment
    _validate_type_alignment(config)  # Output types ↔ state types

    # Stage 5: Prompt placeholders
    _validate_prompt_placeholders(config)  # Valid {state.X} refs

    # Stage 6: State types
    _validate_state_types(config)  # Type strings valid

    # Stage 7: Linear flow (v0.1 constraint)
    _validate_linear_flow(config)  # No conditionals/loops

    # Stage 8: Graph structure
    _validate_graph_structure(config)  # Connected, reachable
```

**Helpful Error Messages with Suggestions**:
```python
# Typo detection with "Did you mean?"
ValidationError: Node 'write' references unknown state field 'artcile'
  Available fields: topic, article, research
  Did you mean 'article'?

# Missing connections
ValidationError: Node 'review' is not reachable from START
  Check edges to ensure all nodes are connected
```

**Edit Distance Algorithm**:
- Levenshtein distance ≤ 2 for suggestions
- Helps catch common typos
- Works for node IDs, state fields, placeholders

**Test Coverage**: 29 comprehensive validator tests

---

### T-004.5: Runtime Feature Gating Implementation

**File**: `src/configurable_agents/runtime/feature_gate.py` (180 lines)

**Feature Gating Strategy**:

**Hard Blocks** (v0.2+ features not implemented):
```python
# Conditional routing
if config.edges and any(edge.routes for edge in config.edges):
    raise FeatureNotAvailableError(
        "Conditional routing (routes) requires v0.2+. "
        "Current version: v0.1. Please use simple edges."
    )

# Loops (edge to earlier node)
if _has_backwards_edge(config):
    raise FeatureNotAvailableError(
        "Loops require v0.2+. All edges must flow forward in v0.1."
    )
```

**Soft Warnings** (v0.2+ features partially implemented):
```python
# DSPy optimization
if config.optimization and config.optimization.enabled:
    warnings.warn(
        "DSPy optimization is planned for v0.3. "
        "Config will be accepted but optimization ignored.",
        FutureWarning
    )

# MLFlow observability (v0.1 in progress)
if config.config.observability.mlflow.enabled:
    # Allow in v0.1 (implementation in progress T-018-021)
    pass
```

**Version Support Query**:
```python
from configurable_agents.runtime import is_feature_supported

is_feature_supported("conditional_routing")  # False in v0.1
is_feature_supported("linear_flows")  # True in v0.1
is_feature_supported("mlflow_observability")  # True in v0.1
```

**Test Coverage**: 19 feature gating tests

---

### T-010: Prompt Template Resolver Implementation

**File**: `src/configurable_agents/core/template.py` (250 lines)

**Variable Resolution with Precedence**:
```python
def resolve_prompt(
    prompt_template: str,
    inputs: dict,
    state: BaseModel
) -> str:
    """Resolve {variable} placeholders with input priority"""

    # 1. Extract variables from template
    variables = _extract_variables(prompt_template)
    # Example: "Hello {name}, topic: {topic}" → ["name", "topic"]

    # 2. Build resolution context (inputs override state)
    context = {}
    for var in variables:
        if var in inputs:
            context[var] = inputs[var]  # Input takes priority
        elif hasattr(state, var):
            context[var] = getattr(state, var)  # State fallback
        else:
            # Variable not found - raise with suggestions
            raise TemplateResolutionError(...)

    # 3. Replace variables with string formatting
    return prompt_template.format(**context)
```

**Nested State Access**:
```python
# Supports dot notation: {metadata.author}
def _resolve_nested(var_path: str, state: BaseModel) -> Any:
    """Resolve 'metadata.author' from state.metadata.author"""
    parts = var_path.split('.')
    value = state
    for part in parts:
        value = getattr(value, part)
    return value

# Works with deeply nested: {a.b.c.d}
```

**Type Conversion**:
- int, float, bool → str automatically
- Objects → str representation
- Lists → str representation (for debugging)

**Error Handling with Suggestions**:
```python
TemplateResolutionError:
  Variable 'topik' not found in prompt template.

  Available from inputs: name, task
  Available from state: topic, research, article

  Did you mean 'topic'?
```

**Test Coverage**: 44 template resolution tests (including nested access, typos, type conversion)

---

### Config-Driven Philosophy in Practice

**Single Source of Truth**:
```yaml
# Everything needed to run workflow in one file
schema_version: "1.0"
flow: { name: article_writer }
state: { fields: [...] }
nodes: [...]
edges: [...]
config:
  llm: { model: gemini-2.0-flash-exp }
  observability: { mlflow: { enabled: true } }
```

**No Hidden Behavior**:
- Explicit state fields (no auto-generation)
- Explicit edges (no automatic routing)
- Explicit output schemas (no unstructured outputs)
- Explicit tool references (no auto-discovery)

**Version Control Friendly**:
- YAML diffs show workflow changes clearly
- Comments allowed for documentation
- Anchors/aliases for DRY (future enhancement)

**Shareable**:
- Config + `.env` file = runnable workflow
- No code dependencies
- Platform-independent (YAML is universal)

---

## Implementation Learnings

### What Worked Well

1. **Pydantic Schema Validation**
   - Catches ~70% of errors at parse time
   - Clear error messages with field paths
   - Type coercion helps users (e.g., `"1.0"` → `1.0`)

2. **Two-Stage Validation (Pydantic + Custom)**
   - Pydantic: Structure and types
   - Custom validator: Cross-references and business logic
   - Separation of concerns

3. **YAML as Primary Format**
   - Human-readable
   - Commentable
   - Git-friendly diffs
   - Users prefer it over JSON

4. **Feature Gating**
   - Allows full schema from day one
   - Users can see future features
   - Clear migration path to v0.2+

### Known Limitations (v0.1)

1. **No Config Composition**
   - Can't import/extend other configs
   - Planned for v0.2 (`config.extends`)

2. **Limited Prompt Template Syntax**
   - Only `{variable}` placeholders
   - No filters, functions, or logic
   - Planned: Jinja2-lite in v0.3

3. **Linear Flow Only**
   - No conditionals, loops, parallel branches
   - Enforced by validator in v0.1
   - Planned for v0.2

---

## Superseded By

None (current)
