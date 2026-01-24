# ADR-009: Full Schema Day One

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code, Senior Engineering Team

---

## Context

When building a config-driven system, there's a tension between:

1. **Incremental Schema**: Start minimal, add fields as features are implemented
2. **Full Schema**: Design complete schema upfront, implement features incrementally

### Incremental Schema Approach

```yaml
# v0.1 schema
flow:
  name: "article_writer"
nodes: [...]
edges: [...]

# v0.2 adds optimization
optimization: {...}

# v0.3 adds nested state
state:
  fields:
    metadata:
      type: object  # NEW
```

**Problems**:
- Schema changes between versions → breaking changes
- Parser must handle multiple schema versions
- Users can't prepare configs for future features
- Documentation fragments across versions

### Full Schema Approach

```yaml
# v0.1 schema (complete structure)
schema_version: "1.0"
flow: {...}
state: {...}
optimization: {...}  # Structure exists, runtime in v0.3
nodes: [...]
edges:  # Supports conditionals, runtime rejects in v0.1
  - from: validate
    routes: [...]
```

**Benefits**:
- Single schema version (1.0)
- Users can see full vision
- Configs are forward-compatible
- Runtime evolves without schema changes

---

## Decision

**Implement full schema from day one.**

The schema will support:
- Nested state objects
- Conditional routing structure
- Optimization configuration
- Node-level overrides
- Input/output mappings
- All future features (structure-wise)

**Runtime will implement features incrementally:**
- v0.1: Linear flows, basic types
- v0.2: Conditionals, loops
- v0.3: DSPy optimization

**Runtime feature gating**: When v0.1 encounters unsupported features (conditionals, optimization), it rejects with clear error pointing to roadmap.

---

## Rationale

### 1. Schema Stability = User Confidence

**With incremental schema**:
```yaml
# User's v0.1 config
flow:
  name: "article_writer"
nodes: [...]

# v0.2 breaks it (new required field)
schema_version: "1.0"  # NOW REQUIRED
flow:
  name: "article_writer"
  version: "1.0"  # NOW REQUIRED
```

**User experience**: "My config broke in v0.2, I have to rewrite it."

**With full schema**:
```yaml
# v0.1 config works in v0.2, v0.3, forever
schema_version: "1.0"
flow:
  name: "article_writer"
  version: "1.0"
```

**User experience**: "I can upgrade versions without touching my config."

### 2. Documentation is Complete From Day One

**Users can see the full vision**:

```markdown
# Config Reference (v0.1)

## optimization (v0.3+)
**Status**: Schema supported, runtime coming in v0.3

Enables DSPy prompt optimization.

```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
```

**Current behavior**: Validated but ignored in v0.1.
**Coming**: v0.3 will enable optimization without config changes.
```

**This is powerful**: Users know what's coming, can prepare, can advocate for features.

### 3. Pydantic Models Don't Change

**Code stays stable**:

```python
# v0.1: Define full schema
class WorkflowConfig(BaseModel):
    schema_version: str
    flow: FlowMetadata
    state: StateSchema
    optimization: OptimizationConfig  # Exists but not used
    nodes: list[NodeConfig]
    edges: list[EdgeConfig]
    config: GlobalConfig

# v0.1, v0.2, v0.3: SAME MODEL
# Runtime just checks `optimization.enabled` in v0.3
```

**No schema migrations. No breaking changes.**

### 4. Forward-Compatible Configs

**User writes config in v0.1 with future features**:

```yaml
# Written in v0.1
schema_version: "1.0"
flow:
  name: "article_writer"

# User adds optimization (v0.3 feature)
optimization:
  enabled: false  # Disabled for now

nodes: [...]

# User adds conditional (v0.2 feature)
edges:
  - from: validate
    routes:
      - condition: {logic: "{state.score} >= 7"}
        to: END
```

**v0.1 behavior**:
```
Warning: optimization config found but v0.1 doesn't support it yet.
This will work in v0.3 (12 weeks).

Error: Conditional routing not supported in v0.1.
Found in edge from 'validate'.
This will work in v0.2 (8 weeks).

To run in v0.1, use linear flow:
  - from: validate
    to: END
```

**User can**:
- Keep the config as-is, documented for future
- Comment out unsupported features
- Know exactly when features arrive

### 5. Easier for AI Config Generation (Future)

When we build the chatbot config generator (Phase 3):

**With full schema**:
```python
# Chatbot knows full schema from day one
schema = load_schema_spec("1.0")

# Generate config using complete structure
config = generate_config_from_conversation(
    user_intent="I want retry logic",
    schema_version="1.0"
)

# Generated config uses conditional routing (v0.2 feature)
# User gets helpful message if running v0.1
```

**With incremental schema**:
```python
# Chatbot must know which version user has
version = detect_user_version()

# Generate different config per version
if version == "v0.1":
    # Can't generate retry logic (not in schema)
    suggest_workaround()
elif version == "v0.2":
    # Generate conditional
```

**Complexity nightmare.**

---

## Implementation Strategy

### Schema Design Phase (Before Coding)

1. **Design complete schema** (this ADR)
2. **Document all fields** (even if runtime doesn't use them)
3. **Mark feature availability** ("v0.1", "v0.2", "v0.3")
4. **Validate with Pydantic** (ensure structure is valid)

### Implementation Phases

**Phase 1: Full Pydantic Models (T-003)**
```python
class OptimizationConfig(BaseModel):
    """DSPy optimization config (v0.3+)"""
    enabled: bool = False
    strategy: str = "BootstrapFewShot"
    metric: str = "semantic_match"
    max_demos: int = 4

class WorkflowConfig(BaseModel):
    schema_version: str
    flow: FlowMetadata
    state: StateSchema
    optimization: Optional[OptimizationConfig] = None  # Optional in v0.1
    nodes: list[NodeConfig]
    edges: list[EdgeConfig]
    config: GlobalConfig
```

**All models defined, validated, but not all used.**

**Phase 2: Runtime Feature Gating (T-004.5)**
```python
def validate_runtime_support(config: WorkflowConfig) -> None:
    """Check if v0.1 runtime can execute this config."""

    # Check for conditionals
    for edge in config.edges:
        if edge.routes:  # Conditional routing
            raise UnsupportedFeatureError(
                f"Conditional routing not supported in v0.1.\n"
                f"Found in edge from '{edge.from_node}'.\n\n"
                f"Coming in v0.2 (8 weeks). See docs/ROADMAP.md\n\n"
                f"To run in v0.1, replace with linear edge:\n"
                f"  - from: {edge.from_node}\n"
                f"    to: END"
            )

    # Check for optimization
    if config.optimization and config.optimization.enabled:
        warnings.warn(
            f"Optimization enabled but not supported in v0.1.\n"
            f"Config will be validated but optimization ignored.\n"
            f"Coming in v0.3 (12 weeks)."
        )
```

**Phase 3: Incremental Feature Implementation**

```python
# v0.1: Feature gating rejects conditionals
def execute_workflow(config):
    validate_runtime_support(config)  # Raises on conditionals
    execute_linear_flow(config)

# v0.2: Remove gate, add conditional executor
def execute_workflow(config):
    # validate_runtime_support(config)  # REMOVED
    execute_conditional_flow(config)  # NEW

# v0.3: Add optimization
def execute_workflow(config):
    if config.optimization.enabled:
        optimize_with_dspy(config)  # NEW
    execute_conditional_flow(config)
```

**Schema never changes. Runtime grows.**

---

## Alternatives Considered

### Alternative 1: Incremental Schema (Version Per Feature)

**Approach**: Add schema fields as features are implemented.

```yaml
# v0.1
flow: {...}
nodes: [...]

# v0.2 (adds optimization field)
schema_version: "1.1"
optimization: {...}
nodes: [...]
```

**Pros**:
- Simpler initially (less upfront design)
- Schema matches implementation exactly

**Cons**:
- **Breaking changes** (users must update configs)
- **Multiple schema versions** (parser complexity)
- **Documentation fragments** (v0.1 docs vs v0.2 docs)
- **No forward compatibility**

**Why rejected**: User experience suffers. Upgrading versions becomes painful.

### Alternative 2: Extensibility via "extras" Field

**Approach**: Single stable schema + free-form extras for future features.

```yaml
schema_version: "1.0"
flow: {...}
nodes: [...]

extras:
  optimization: {...}  # Unvalidated, free-form
  custom_routing: {...}
```

**Pros**:
- Schema stays stable
- Users can add anything

**Cons**:
- **No validation** on extras (typos, errors)
- **No autocomplete** in editors
- **Unclear semantics** (what does extras do?)
- **No type safety**

**Why rejected**: Defeats purpose of schema validation. We want type safety.

### Alternative 3: Full Schema with Feature Flags in Runtime

**Approach**: Full schema, runtime checks feature flags at startup.

```bash
# v0.1 with experimental features enabled
ENABLE_CONDITIONALS=true python -m configurable_agents run workflow.yaml
```

**Pros**:
- Users can opt-in to experimental features
- Incremental rollout

**Cons**:
- **Confusing** (is this stable or not?)
- **Testing complexity** (test all flag combinations)
- **Support burden** ("It works with flags but not without")

**Why rejected**: Feature flags should be for A/B testing, not core features. Clean v0.1 → v0.2 → v0.3 is clearer.

---

## Consequences

### Positive Consequences

1. **Schema Stability**
   - Users write configs once
   - Configs work across versions
   - No breaking changes

2. **Complete Documentation**
   - Users see full vision
   - Can plan for future features
   - Clear roadmap

3. **Simpler Parser**
   - Single Pydantic model
   - No version-specific logic
   - Validation is complete

4. **Better Error Messages**
   ```
   Error: Conditional routing not supported yet.
   Coming in v0.2 (8 weeks).
   See: docs/ROADMAP.md
   ```

5. **Future-Proof**
   - AI config generators can use full schema
   - Tooling built once, works forever
   - No migration scripts needed

### Negative Consequences

1. **More Upfront Design**
   - Must design complete schema before coding
   - Harder to change schema later
   - **Mitigation**: Careful design now (this ADR), validation with team

2. **Unused Code Initially**
   - Pydantic models for v0.3 features defined in v0.1
   - More test surface (validate fields even if not used)
   - **Mitigation**: Minimal cost, models are small

3. **User Confusion Possible**
   - "Why is `optimization` in my config if it doesn't work?"
   - **Mitigation**: Clear documentation, warnings in runtime

4. **Temptation to Use Unimplemented Features**
   - Users might expect conditionals to work if schema accepts them
   - **Mitigation**: Loud, clear errors with timeline

### Risks

#### Risk 1: Schema Design is Wrong

**Likelihood**: Medium (hard to predict all future needs)
**Impact**: High (stuck with bad design)

**Example**:
```yaml
# v0.1 schema (bad design)
optimization: {...}  # Top-level

# v0.2: Realize it should be per-node
nodes:
  - id: research
    optimization: {...}  # Oops, can't add this without breaking schema
```

**Mitigation**:
- **Careful design NOW** (get senior engineer input ✅ done)
- **Validate with use cases** (write example configs)
- **Extensibility points** (allow node-level overrides of global config)
- **Reserved fields** (plan for future additions)

#### Risk 2: Users Expect Unimplemented Features to Work

**Likelihood**: Medium (schema accepts it, why doesn't runtime?)
**Impact**: Medium (user frustration)

**Mitigation**:
- **Clear error messages** with timeline
  ```
  Error: Conditional routing not supported in v0.1
  Coming in v0.2 (8 weeks)
  See: docs/ROADMAP.md for details
  ```
- **Documentation** marks each field with version availability
- **Warnings** for ignored features (optimization in v0.1)

#### Risk 3: Schema Becomes Too Complex

**Likelihood**: Low (we control it)
**Impact**: Medium (users overwhelmed)

**Mitigation**:
- **Sensible defaults** (most fields optional)
- **Templates** (starter configs)
- **Progressive disclosure** (simple example → advanced example)

---

## Validation Criteria

**We'll know this decision was right if**:

1. **No breaking changes v0.1 → v0.2 → v0.3**
   - Users upgrade without config changes
   - Configs written in v0.1 work in v0.3

2. **Clear user feedback**
   - Users understand what's supported when
   - Feature requests align with roadmap

3. **Clean codebase**
   - Single Pydantic model
   - No version-specific parsing logic
   - Incremental runtime feature additions

**We'll know it was wrong if**:

1. **Schema redesign needed**
   - Fundamental structure change required
   - Can't add features without breaking changes

2. **User confusion**
   - "Why doesn't this work?" (even with errors)
   - Users angry about unimplemented features

**Escape hatch**: If schema is fundamentally wrong, release v2.0 with new schema, provide migration tool.

---

## Schema Evolution Plan

### v1.0 Schema (Frozen)
- Defined in this ADR
- Covers all planned features through v0.3
- No breaking changes allowed

### Future Extensions (if needed)
```yaml
schema_version: "1.1"  # Minor version bump
# Add new optional fields (backwards compatible)
flow:
  tags: [...]  # NEW, optional
```

### Major Changes (if absolutely needed)
```yaml
schema_version: "2.0"  # Major version bump
# Breaking change, provide migration tool
```

**Goal**: Stay on 1.x schema for as long as possible (years).

---

## Example: Full Schema in Practice

### Config (v0.1)
```yaml
schema_version: "1.0"
flow:
  name: "article_writer"

state:
  fields:
    topic: {type: str, required: true}

nodes:
  - id: research
    inputs: {query: "{state.topic}"}
    prompt: "Research: {query}"
    output_schema:
      type: str
    outputs: [research]

edges:
  - {from: START, to: research}
  - {from: research, to: END}

# Optimization config (v0.3 feature)
optimization:
  enabled: false  # Not yet, but structure exists
```

### Runtime v0.1
```python
config = load_config("workflow.yaml")

# Pydantic validates full schema (including optimization)
validated = WorkflowConfig(**config)  # ✅ Passes

# Runtime checks support
validate_runtime_support(validated)  # ✅ Passes (optimization disabled)

# Execute
result = execute_linear_flow(validated)
```

### Runtime v0.3 (Same Config)
```python
config = load_config("workflow.yaml")
validated = WorkflowConfig(**config)  # ✅ Passes

# Enable optimization
validated.optimization.enabled = True  # User edits config

# Runtime now uses it
optimized_config = optimize_with_dspy(validated)  # NEW in v0.3
result = execute_conditional_flow(optimized_config)
```

**Same config, different runtime behavior. No schema changes.**

---

## References

- Semantic Versioning: https://semver.org/
- Pydantic validation: https://docs.pydantic.dev/
- Backwards compatibility: https://www.hyrumslaw.com/

---

## Notes

This is a **foundational architectural decision** that affects every layer of the system.

The "Full Schema Day One" philosophy prioritizes:
1. **User experience** over implementation simplicity
2. **Stability** over incrementalism
3. **Forward compatibility** over minimal initial design

**Key insight**: Schema is user-facing API. Like REST APIs, it's worth designing carefully upfront to avoid breaking changes.

**Analogy**: We're building the "HTTP spec" (schema) before building the "web server" (runtime). The spec is stable; servers evolve.

---

## Superseded By

None (current)
