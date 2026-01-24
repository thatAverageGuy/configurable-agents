# Discussion Summary

**Date**: 2026-01-24
**Session**: Project Discovery & Schema Design
**Status**: Awaiting Review & Approval

---

## Executive Summary

We conducted a comprehensive discovery session for the **configurable-agents** project, resulting in:
- Complete project vision and philosophy
- Finalized config schema (v1.0) with "Full Schema Day One" approach
- 9 Architecture Decision Records (ADRs)
- Updated technical specification
- Detailed work breakdown (20 tasks, 6-8 weeks for v0.1)

**Current State**: All documentation complete, ready for your review before implementation begins.

---

## What We Discussed

### 1. Project Vision & Goals

**Reference**: `docs/PROJECT_VISION.md`

**Key Points**:
- **Purpose**: Config-first agent runtime enabling "idea to production in minutes"
- **Core Philosophy**:
  - Local-first (data stays local)
  - Strict typing (Pydantic schemas everywhere)
  - Fail fast, fail loud
  - Boring technology (prefer standard tools)
  - Production-grade from day one
- **Success Metrics**:
  - 12 months: Config → running agent in < 5 minutes
  - 3 years: Standard tool for agent development
- **Phases**:
  - v0.1: Core engine (linear flows)
  - v0.2: Enhanced runtime (conditionals, loops, multi-provider)
  - v0.3: Optimization (DSPy integration)
  - v1.0+: Advanced features (multi-modal, cloud deployment)

---

### 2. Config Schema Design (FINALIZED)

**Reference**: `docs/SPEC.md`

**Major Design Session**: We iteratively designed the complete config schema.

**Your Requirements**:
1. ✅ Full schema from day one (support future features in structure)
2. ✅ Strict typing on all outputs (Pydantic enforcement)
3. ✅ Explicit input mapping (`inputs: {query: "{state.topic}"}`)
4. ✅ Nested state support (`object` with `schema`)
5. ✅ Top-level `optimization` (not under `config`)
6. ✅ Use `flow` (not `metadata`)
7. ✅ Prompt syntax: `{state.field}` or `{variable}` (from inputs)
8. ✅ JSON + YAML support (1:1 via Pydantic)

**Final Schema Structure**:
```yaml
schema_version: "1.0"
flow: {name, description, version}
state: {fields with types, nested objects}
nodes: [id, inputs, prompt, output_schema, outputs, tools, llm, optimize]
edges: [from, to, routes (v0.2+)]
optimization: {enabled, strategy, metric, max_demos} (v0.3+)
config: {llm, execution, observability}
```

**Killer Feature**: Type enforcement via `output_schema` - LLM outputs validated against Pydantic models.

---

### 3. Architecture Decisions (9 ADRs)

**Reference**: `docs/adr/`

| ADR | Title | Key Decision |
|-----|-------|--------------|
| ADR-001 | LangGraph as Execution Engine | Use LangGraph (no prompt manipulation → DSPy compatible) |
| ADR-002 | Strict Typing with Pydantic | All outputs must conform to schemas (fail fast, save money) |
| ADR-003 | Config-Driven Architecture | YAML config is single source of truth |
| ADR-004 | Parse-Time Validation | Validate everything before execution (save LLM costs) |
| ADR-005 | Single LLM Provider (v0.1) | Google Gemini only, multi-provider in v0.2 |
| ADR-006 | Linear Flows Only (v0.1) | No conditionals/loops in v0.1, add in v0.2 |
| ADR-007 | Tools as Named Registry | Pre-registered tools, reference by name |
| ADR-008 | In-Memory State (v0.1) | Ephemeral state, persistence in v0.2 |
| ADR-009 | Full Schema Day One | Complete schema from start, runtime evolves incrementally |

**Critical ADR**: ADR-001 addresses your CrewAI concern - LangGraph won't interfere with DSPy because it doesn't wrap prompts.

**Verification Plan**: T-019 and T-020 will test DSPy integration to confirm ADR-001.

---

### 4. Implementation Strategy

**Reference**: `docs/TASKS.md`, `docs/ARCHITECTURE.md`

**Key Principles**:
- **Full Schema Day One** (ADR-009): Schema supports all features, runtime implements incrementally
- **Runtime Feature Gating**: v0.1 accepts conditionals/optimization in config but rejects at runtime with helpful errors
- **Type Enforcement**: Pydantic models generated from config, LLM outputs validated
- **Testing Non-Negotiable**: Every task requires comprehensive tests

**Task Breakdown**: 20 tasks (T-001 through T-020)

**Timeline**:
- Foundation (T-001 to T-007): 3-4 weeks
- Core execution (T-008 to T-013): 3-4 weeks
- Polish (T-014 to T-018): 1.5 weeks
- DSPy verification (T-019, T-020): 1.5 weeks
- **Total**: 6-8 weeks for v0.1

---

## Open Questions

### Q1: Output Schema - Simple Type Shorthand

**Context**: For nodes with single outputs, should we allow shorthand?

**Current Spec**:
```yaml
# Full format (always required)
output_schema:
  type: object
  fields:
    - name: article
      type: str

# Or allow shorthand for simple types?
output_schema:
  type: str
  description: "Article text"
```

**Your Answer in Session**: Full format is in SPEC.md, shorthand mentioned as alternative.

**Question**: Should we support both, or always require full format?

**Impact**: Affects T-003 (Schema), T-007 (Output Builder)

**DECISION**: Always require full format. No shorthand. Simpler parser/validator, clearer for users.

---

### Q2: Expression Language for Conditionals (v0.2+)

**Context**: When we implement conditionals in v0.2, what expression parser?

**Options**:
1. Python `eval()` - Powerful but dangerous
2. Simple comparisons only - Safe but limited (`{state.field} >= 7`)
3. Library like `simpleeval` - Balance of safety and power

**Current Approach**: Store as string in v0.1, decide in v0.2.

**Question**: Any preference now, or defer to v0.2?

**Impact**: Affects v0.2 implementation, not v0.1.

**DECISION**: Defer to v0.2 (as currently planned).

---

### Q3: Default Values for Nested Objects

**Context**: How to handle nested object defaults?

```yaml
state:
  fields:
    metadata:
      type: object
      schema:
        author: str
        timestamp: str
      default: ???  # What goes here?
```

**Options**:
1. Require dict: `default: {author: "", timestamp: ""}`
2. Auto-generate empty object: `default: {}`
3. No defaults for objects (must be provided)

**Question**: Which approach?

**Impact**: Affects T-003 (Schema), T-006 (State Builder)

**DECISION**: Option 1 - Require explicit dict. No magic, clear defaults.

---

### Q4: Tool Configuration Per-Invocation

**Context**: Should tools support per-node configuration?

```yaml
# Current (v0.1)
tools:
  - serper_search  # Uses env var SERPER_API_KEY

# Future possibility
tools:
  - name: serper_search
    config:
      max_results: 10
      region: "US"
```

**Question**: Need this in v0.1, or defer?

**Impact**: Affects T-008 (Tool Registry)

**DECISION**: Defer to v0.2+. Nodes reference tools by name only in v0.1.

---

### Q5: State Field Name Conflicts with Input Mapping

**Context**: What if input mapping creates conflict?

```yaml
state:
  fields:
    query: str  # State has 'query'

nodes:
  - id: research
    inputs:
      query: "{state.topic}"  # Maps topic → query (local variable)
    prompt: "Research {query}"  # Which 'query'?
```

**Options**:
1. Local variables (from `inputs`) take precedence
2. Error if conflict exists
3. Require explicit namespace (`{input.query}` vs `{state.query}`)

**Question**: Which behavior?

**Impact**: Affects T-010 (Template Resolver)

**DECISION**: Option 1 - Local variables take precedence. Note: Revisit in v0.2 for better uniformity to avoid this ambiguity.

---

## Documents Created/Updated

### New Documents

1. **docs/PROJECT_VISION.md** - Complete project vision and philosophy
2. **docs/ARCHITECTURE.md** - v0.1 system architecture
3. **docs/SPEC.md** - Complete Schema v1.0 specification
4. **docs/TASKS.md** - Work breakdown (20 tasks)
5. **docs/adr/ADR-001-langgraph-execution-engine.md** - Critical: Addresses CrewAI concern
6. **docs/adr/ADR-002-strict-typing-pydantic-schemas.md** - Type enforcement rationale
7. **docs/adr/ADR-003-config-driven-architecture.md** - Config-first philosophy
8. **docs/adr/ADR-004-parse-time-validation.md** - Fail fast validation
9. **docs/adr/ADR-005-single-llm-provider-v01.md** - Gemini only for v0.1
10. **docs/adr/ADR-006-linear-flows-only-v01.md** - No conditionals in v0.1
11. **docs/adr/ADR-007-tools-as-named-registry.md** - Tool registry design
12. **docs/adr/ADR-008-in-memory-state-only-v01.md** - Ephemeral state for v0.1
13. **docs/adr/ADR-009-full-schema-day-one.md** - Full schema philosophy
14. **docs/DISCUSSION.md** (this file)

### Existing Files (Unchanged)

- `README.md` - Placeholder, needs updating (T-016)
- `CLAUDE.md` - Your operating instructions (unchanged)
- `sample_config.yaml` - Your PoC config (will be replaced with Schema v1.0 examples)

---

## Corrections Made (2026-01-24)

**After review, the following corrections were applied**:

1. **ADR-003: Validation Flow Correction**
   - **Was**: Validation shown as separate step (#3) before running
   - **Now**: Validation is auto-built-in to `run` and `deploy` commands
   - **Explicit validation**: Optional tool for development/CI feedback

2. **Open Questions Resolved**:
   - Q1: No shorthand syntax - full format always
   - Q2: Expression language deferred to v0.2
   - Q3: Explicit dict required for nested object defaults
   - Q4: Per-node tool config deferred to v0.2+
   - Q5: Local variables take precedence (revisit uniformity in v0.2)

---

## What You Need to Review

### Priority 1: Schema Design (CRITICAL)

**File**: `docs/SPEC.md`

**What to Check**:
- [ ] Is the schema structure exactly what you want?
- [ ] Input mapping format: `inputs: {query: "{state.topic}"}` - correct?
- [ ] Output schema format - always full, or allow shorthand?
- [ ] Nested state support - as designed?
- [ ] Prompt syntax `{state.field}` vs `{variable}` - correct?
- [ ] Top-level structure (schema_version, flow, state, nodes, edges, optimization, config) - correct?

**Why Critical**: This is the user-facing API. Hard to change later.

---

### Priority 2: Full Schema Day One Philosophy

**File**: `docs/adr/ADR-009-full-schema-day-one.md`

**What to Check**:
- [ ] Do you agree with this approach? (Schema v1.0 supports features implemented in v0.1, v0.2, v0.3)
- [ ] Is runtime feature gating acceptable? (v0.1 rejects conditionals with helpful error)
- [ ] Timeline trade-off: 6-8 weeks (full schema) vs 4-6 weeks (incremental schema) - worth it?

**Why Critical**: Affects entire development approach and timeline.

---

### Priority 3: LangGraph Decision

**File**: `docs/adr/ADR-001-langgraph-execution-engine.md`

**What to Check**:
- [ ] Does the analysis of LangGraph vs CrewAI prompt handling make sense?
- [ ] Are you convinced LangGraph won't interfere with DSPy?
- [ ] Is the verification plan (T-019, T-020) sufficient?
- [ ] Is the escape strategy (custom executor if needed) acceptable?

**Why Critical**: Core architecture choice. DSPy integration depends on this.

---

### Priority 4: Timeline & Estimates

**File**: `docs/TASKS.md`

**What to Check**:
- [ ] 6-8 weeks for v0.1 acceptable?
- [ ] Task breakdown makes sense?
- [ ] Priorities correct (P0, P1, P2)?
- [ ] Dependencies look right?

**Why Important**: Sets expectations and planning.

---

### Optional: Other ADRs

**Files**: `docs/adr/ADR-002` through `ADR-008`

**What to Check**:
- [ ] Do you agree with the rationale in each ADR?
- [ ] Any decisions you'd change?
- [ ] Anything missing?

**Why Less Critical**: These are more tactical, easier to adjust later.

---

## Your Answers to Key Questions

During our session, you (with senior engineer input) provided these answers:

### Config Structure
- ✅ `flow:` not `metadata:`
- ✅ `optimization:` top-level (sibling to `config`)
- ✅ `schema_version:` at top-level
- ✅ Nested state via `object` with `schema`

### Input/Output
- ✅ Input mapping: Explicit dict `{query: "{state.topic}"}`
- ✅ Outputs: Simple list `["research", "sources"]`
- ✅ Output schema: Mandatory Pydantic models
- ✅ Descriptions: Required (help LLM + documentation)

### Runtime Strategy
- ✅ Full schema day one, runtime incremental
- ✅ Feature gating with helpful errors
- ✅ Parse-time validation (fail fast)

### Timeline
- ✅ 6-8 weeks acceptable for production-grade v0.1
- ✅ Worth the extra time for stability

### Testing
- ✅ Non-negotiable, comprehensive from day one
- ✅ DSPy verification (T-019, T-020) critical

---

## Next Action Items

### For You (Current Status)

**Completed**:
1. ✅ **Reviewed SPEC.md** - Approved with corrections
2. ✅ **Reviewed ADR-009** - Approved "Full Schema Day One" approach
3. ✅ **Reviewed ADR-001** - Confirmed LangGraph choice
4. ✅ **Answered open questions** (Q1-Q5 resolved)
5. ✅ **Reviewed all ADRs** (001-009)
6. ✅ **Reviewed PROJECT_VISION.md, ARCHITECTURE.md**

**Pending**:
- Final approval to proceed with T-001 (Project Setup)
- Timeline approval (6-8 weeks for v0.1)

---

### For Me (After Your Approval)

**Immediate** (T-001: Project Setup):
1. Clean up PoC files (remove old sample_config.yaml, PoC .py files)
2. Set up Python package structure (`src/configurable_agents/`)
3. Create `pyproject.toml` with dependencies
4. Set up pytest
5. Create `.env.example`
6. Verify imports work

**Then** (T-002: Config Parser):
- Implement YAML/JSON parser
- Write tests

**Ongoing**:
- Each task = one commit
- Tests required for DONE status
- Update TASKS.md status as we progress

---

## Important Notes

### PoC Files

**Current State**: Your PoC files are still in the repo:
- `sample_config.yaml` (old format)
- `crew_builder.py`, `flow_builder.py`, `main.py`, etc. (CrewAI-based)

**Plan**: Delete these once we start T-001, replace with Schema v1.0 examples.

**If you want to keep for reference**: Let me know, I'll move them to `archive/`.

---

### Schema Version Stability

**Critical Commitment**: Schema v1.0 will NOT have breaking changes.

**What this means**:
- Configs written in v0.1 will work in v0.2, v0.3, v1.0
- We can only ADD optional fields, not change/remove existing ones
- Major breaking change → v2.0 (with migration tool)

**Why important**: User trust, ecosystem stability.

---

### DSPy Integration Risk

**Risk**: LangGraph might still interfere with DSPy (despite analysis).

**Mitigation**:
- T-019: Test DSPy integration thoroughly
- T-020: Test structured outputs + DSPy
- Document findings
- Escape hatch: Custom state machine if tests fail (~2 weeks to build)

**Timeline impact if escape needed**: Add 2 weeks to v0.1.

---

### Testing Strategy

**Unit Tests**: Every component, mocked dependencies
**Integration Tests**: Real LLM calls (marked slow, optional in CI)
**Example Configs**: Used as integration test fixtures
**Cost Tracking**: Integration tests report LLM costs

**Coverage Goal**: >80% (aspirational, not required for v0.1 release).

---

## Questions Answered ✅

1. **Schema approval**: SPEC.md approved with minor corrections
2. **Shorthand syntax**: Q1 - No shorthand, full format always
3. **Nested object defaults**: Q3 - Explicit dict required
4. **Input mapping conflicts**: Q5 - Local takes precedence (revisit v0.2)
5. **Validation flow**: Auto-built-in to run/deploy, explicit validation optional
6. **Timeline approval**: Pending final approval
7. **Ready to code**: Pending final approval for T-001

---

## How to Provide Feedback

**Option 1: Approve as-is**
> "Approved. Start T-001 (Project Setup)."

**Option 2: Specific changes**
> "SPEC.md: Change X to Y. ADR-009: Concerns about Z. Timeline: Can we do X weeks?"

**Option 3: Major iteration**
> "Let's discuss [topic] further before implementation."

---

## Session Statistics

**Duration**: ~4 hours of collaborative design
**Messages Exchanged**: ~30 messages
**Documents Created**: 14 files
**Total Documentation**: ~15,000 lines
**ADRs Written**: 9
**Tasks Defined**: 20
**Decisions Made**: 50+

**Quality**: Production-grade documentation, ready for implementation.

---

## References

### Core Documents
- Vision: `docs/PROJECT_VISION.md`
- Architecture: `docs/ARCHITECTURE.md`
- Specification: `docs/SPEC.md`
- Tasks: `docs/TASKS.md`

### Architecture Decisions
- `docs/adr/ADR-001-langgraph-execution-engine.md`
- `docs/adr/ADR-002-strict-typing-pydantic-schemas.md`
- `docs/adr/ADR-003-config-driven-architecture.md`
- `docs/adr/ADR-004-parse-time-validation.md`
- `docs/adr/ADR-005-single-llm-provider-v01.md`
- `docs/adr/ADR-006-linear-flows-only-v01.md`
- `docs/adr/ADR-007-tools-as-named-registry.md`
- `docs/adr/ADR-008-in-memory-state-only-v01.md`
- `docs/adr/ADR-009-full-schema-day-one.md`

### Current Files
- `README.md` - Needs updating
- `CLAUDE.md` - Operating instructions
- `sample_config.yaml` - Old format, will be replaced

---

## Final Notes

**What went well**:
- Comprehensive discovery without jumping to code
- Clear decision-making with rationale
- Senior engineer input on schema design
- All decisions documented

**What's next**:
- Your review and approval
- Start implementation (T-001)
- Iterative development with regular commits

**Commitment**: Production-grade system from day one, not a prototype.

---

**Status**: Awaiting your review.
**Next Session**: After your approval, start T-001 (Project Setup).
