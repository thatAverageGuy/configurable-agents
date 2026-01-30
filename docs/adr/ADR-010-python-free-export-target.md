# ADR-010: Python-Free Export Target

**Status**: Accepted (Deferred Implementation)
**Date**: 2026-01-29
**Deciders**: User, Claude Code

---

## Context

Current architecture: YAML config → Python runtime (LangGraph + LangChain + Pydantic)

**Deployment footprint**:
- Base image: `python:3.11-slim` (~150MB)
- Dependencies: ~200MB
- **Total: ~350MB**

**User question**: Can we export workflows to Rust/Go for minimal Docker images (~10-15MB)?

**Use case**: Production deployments prioritizing:
- Minimal container size (edge computing, serverless)
- Fast cold starts
- Reduced attack surface
- Lower resource costs

---

## Decision

**DEFER implementation to v0.5+, but design current architecture to enable future export.**

No export in v0.1-v0.3. Python runtime remains primary target.

**Design principles for exportability**:
1. Keep orchestration logic declarative (in config, not code)
2. Separate tool definitions from tool implementations
3. Use serializable config formats (already: YAML/JSON)
4. Avoid Python-specific runtime dependencies in config semantics

---

## Export Architecture (Future)

### Components

**1. Intermediate Representation (IR)**
- Input: YAML workflow config
- Output: Execution-optimized JSON/Protobuf
- Contains:
  - Materialized conditional logic
  - Compiled graph structure
  - Inlined prompts and schemas
  - Type system mappings

**2. Slim Runtime (Rust/Go)**
- Graph executor (topological sort, dependency resolution)
- LLM API client (HTTP, structured output parsing)
- Template resolver (`{field}` substitution)
- State management (typed structs)
- **Size: ~10-15MB static binary**

**3. Tool Execution (Critical Constraint)**

Three approaches:

| Approach | Size | Complexity | Constraints |
|----------|------|------------|-------------|
| **HTTP-only tools** | ~15MB | Low | Limits to HTTP APIs only |
| **Sidecar service** | ~165MB | Medium | Python toolbox as microservice |
| **Tool rewrite** | ~15MB | Very High | Port all LangChain tools |

**Recommended: HTTP-only for v0.5, sidecar for v0.6+**

**4. Type System Mapping**

```
Pydantic → Target Language
--------------------------
str       → String / string
int       → i64 / int64
list[str] → Vec<String> / []string
dict      → HashMap / map
```

Generated at export time from state schema.

---

## Rationale

### Why Defer?

**Cost vs. Benefit (v0.1)**:
- Implementation: 8-12 weeks
- Value: Minimal (no users yet)
- Risk: Distraction from core features

**Cost vs. Benefit (v0.5+)**:
- Implementation: 8-12 weeks
- Value: High (users demanding slim deploys)
- Risk: Low (runtime proven, architecture stable)

### Why Design for Exportability Now?

**Avoiding architectural dead-ends**:
- Don't embed Python-specific semantics in config
- Keep tool registry declarative
- Maintain clear orchestration/execution separation

**Example (Good)**:
```yaml
tools:
  - name: serper_search
    type: http
    endpoint: "https://google.serper.dev/search"
```

**Example (Bad - blocks export)**:
```yaml
tools:
  - name: custom_processor
    type: python
    code: |
      def process(x):
          import pandas as pd
          return pd.DataFrame(x).to_json()
```

### Comparable Systems

**PyTorch → ONNX**:
- Train in Python (flexible)
- Export to ONNX (portable)
- Run via onnxruntime (slim)

**Our approach**:
- Design in YAML (flexible)
- Execute in Python (v0.1-v0.4)
- Export to Rust/Go (v0.5+)

---

## Implementation Roadmap (When Implemented)

**Phase 1: IR Format** (2 weeks)
- Design JSON schema for execution graph
- Include materialized conditionals
- Type system mappings
- Exporter tool: `config-export workflow.yaml → workflow.ir.json`

**Phase 2: Minimal Runtime - HTTP Tools Only** (4 weeks)
- Rust/Go graph executor
- LLM client (OpenAI, Anthropic, Google)
- Template resolver
- State management
- **Limitation: HTTP-based tools only**

**Phase 3: Sidecar Architecture** (3 weeks)
- Python toolbox service
- gRPC/HTTP API for tools
- Runtime calls sidecar for complex tools
- **Size: 15MB + 150MB sidecar**

**Phase 4: Optimization** (2 weeks)
- Static linking
- Binary compression
- Tool bundling

---

## Architectural Constraints for Exportability

To preserve export option, **avoid**:

1. **Python code execution in config**
   ```yaml
   # ❌ Never add this
   nodes:
     - id: processor
       code: |
         def custom_logic(state):
           ...
   ```

2. **Runtime-only tool definitions**
   - All tools must be declaratively defined
   - Tool registry = config, not imports

3. **Implicit state mutations**
   - State changes explicit in config
   - No hidden side effects

**Acceptable (exportable)**:

1. **Declarative tools**
   ```yaml
   tools:
     - name: http_fetch
       type: http
       method: GET
   ```

2. **Expression-based conditionals**
   ```yaml
   condition: "{state.score} >= 8"
   # Parseable, compilable
   ```

3. **Structured schemas**
   ```yaml
   output_schema:
     type: object
     fields:
       - name: result
         type: str
   ```

---

## Consequences

### Positive

1. **Future-proof architecture**
   - Can export when needed
   - No redesign required

2. **Clear separation of concerns**
   - Orchestration (config)
   - Execution (runtime)
   - Tools (registry)

3. **Deployment flexibility**
   - Python (full features)
   - Rust/Go (minimal footprint)
   - Both from same config

### Negative

1. **Design constraints**
   - Can't add Python code execution
   - Must keep tools declarative
   - **Mitigation**: Aligns with config-first philosophy

2. **Deferred value**
   - No immediate benefit
   - Investment without users
   - **Mitigation**: Minimal cost (just design awareness)

### Risks

**Risk 1: Tool limitation blocks use cases**
- HTTP-only tools insufficient
- Users need Python packages
- **Mitigation**: Sidecar architecture (hybrid approach)

**Risk 2: Export never actually needed**
- Users fine with 350MB images
- Wasted design effort
- **Mitigation**: Low cost (just awareness, no code)

**Risk 3: IR format becomes legacy**
- Better export format discovered
- **Mitigation**: IR is internal, can change

---

## Validation Criteria

**Design is successful if**:
1. Config schema has no Python-specific semantics
2. Tool registry is declarative and serializable
3. Export can be implemented in v0.5 without config changes

**Export implementation is successful if** (v0.5+):
1. Docker image <20MB (HTTP-only mode)
2. Docker image <200MB (sidecar mode)
3. Execution semantics identical to Python runtime
4. Same config runs on both runtimes

---

## Alternatives Considered

### Alternative 1: Python Only, Forever

**Approach**: Never support export. Python is fast enough.

**Pros**: Simpler, no design constraints

**Cons**: Blocks edge/serverless use cases, higher costs

**Why rejected**: Want deployment flexibility without committing implementation now.

### Alternative 2: Implement Export in v0.1

**Approach**: Build Rust runtime alongside Python.

**Pros**: Available immediately

**Cons**: 8-12 week delay, premature optimization, no users to validate

**Why rejected**: Too early. Validate Python runtime first.

### Alternative 3: WASM Target

**Approach**: Compile to WebAssembly instead of native.

**Pros**: Portable, sandboxed

**Cons**: Tooling immature for LLM workflows, network access limited

**Why rejected**: Rust/Go native more practical for server deployments.

---

## Examples

### Exportable Config (Good)

```yaml
schema_version: "1.0"
flow:
  name: "research_pipeline"

state:
  fields:
    query: {type: str, required: true}
    results: {type: list[str], default: []}

nodes:
  - id: search
    prompt: "Search for: {query}"
    output_schema:
      type: object
      fields:
        - name: results
          type: list[str]
    outputs: [results]
    tools:
      - serper_search  # HTTP tool, exportable

edges:
  - {from: START, to: search}
  - from: search
    routes:  # Conditional logic, parseable
      - condition: "len({state.results}) > 0"
        to: END
      - condition: "default"
        to: retry
```

**Exportable because**:
- No Python code
- Declarative tools
- Expression-based conditionals
- Type-safe schema

### Non-Exportable Config (Bad - Don't Add This Feature)

```yaml
nodes:
  - id: processor
    type: python_function  # ❌ Python-specific
    code: |
      import pandas as pd
      def process(state):
          df = pd.DataFrame(state.data)
          return df.describe().to_dict()
    outputs: [stats]
```

**Blocks export because**: Requires Python interpreter

---

## References

- PyTorch ONNX Export: https://pytorch.org/docs/stable/onnx.html
- Rust LLM clients: https://github.com/64bit/async-openai
- Protocol Buffers: https://protobuf.dev/

---

## Notes

This ADR establishes **philosophical commitment to exportability** without implementation commitment.

Key principle: **Config is runtime-agnostic.**

If export is never implemented, no harm done (just cleaner architecture). If needed later, path is clear.

---

## Implementation Status

**Status**: ⏸️ Deferred to v0.5+
**Related Tasks**: None (future vision)
**Current State**: Architecture designed to enable future export, but not implemented

**Design Decisions Made** (supporting future export):
- Config-driven architecture (ADR-003) - No Python code in configs
- Pydantic schemas (ADR-002) - Portable type definitions
- LangGraph (ADR-001) - Well-defined state machine model

**No Work Planned for v0.1-v0.4**: Focus on Python runtime first.

---

## Superseded By

None (current)
