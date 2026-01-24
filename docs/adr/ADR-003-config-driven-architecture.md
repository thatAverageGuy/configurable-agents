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

## Superseded By

None (current)
