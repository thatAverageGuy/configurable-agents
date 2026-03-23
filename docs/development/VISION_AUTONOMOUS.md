# Vision: Autonomous Workflow Platform

**Status**: DEFERRED — Phase 2 (start date TBD)
**Last Updated**: 2026-03-23
**Context**: This document captures the long-term architectural vision discussed 2026-03-23. No implementation is in scope until Phase 1.1 is complete and Phase 2 is explicitly started.

---

## The Core Idea

Most agent frameworks make decisions as unstructured text — the LLM emits a reasoning trace, tools are called, and the framework parses the output to determine what to do next. This produces unpredictable, hard-to-audit behavior.

This system inverts that model:

> **Decisions are first-class graph structure. LLMs fill in content within each node. Every execution is a path through a graph — traceable, replayable, and auditable.**

The v1.0 system implements the deterministic layer: fixed graphs defined in YAML, executed with full observability. Phase 2 adds the autonomous layer: graphs that can reason about and extend their own structure — while preserving path traceability at every step.

The result is what we call a **hierarchical deterministic autonomous workflow** (HDAW):
- Deterministic at the macro level (known paths are stable and reproducible)
- Autonomous at the micro level (novel scope triggers controlled, logged expansion)
- Traceable at every level (every decision is a graph transition with a path ID)

---

## Autonomy Levels

The system supports a configurable autonomy dial, not a binary on/off:

| Level | Name | Description | Expansion Source |
|-------|------|-------------|-----------------|
| 0 | **Fixed** | Fully deterministic. No expansion. YAML is final. | None |
| 1 | **Selective** | Can select and invoke pre-defined sub-workflows from a library. No new structure generated. | Sub-workflow library |
| 2 | **Composable** | Can compose new nodes from existing tools + prompt templates. New structure is logged and optionally persisted. | Tool registry + template library |
| 3 | **Generative** | Can generate novel prompt logic and tool compositions. Highest autonomy, most risk. Requires explicit opt-in. | LLM-driven expansion engine |

Level 0 is the current state (v1.0 / v1.1). Phase 2 targets Level 1-2. Level 3 is Phase 3+.

The autonomy level is set per workflow:
```yaml
config:
  autonomy:
    level: 1
    expansion: ephemeral  # or persistent
    max_expansions: 3     # hard cap per run
```

---

## Dynamic Workflow Expansion

When a workflow at Level 1+ encounters a task that its current graph cannot handle, it can expand:

```
WorkflowConfig (YAML, stable)
    ↓ instantiation at runtime
WorkflowInstance
    ↓ expansion trigger (task scope exceeds current graph)
ExpansionEngine (meta-agent)
    ↓ reads: structural memory + task context + autonomy constraints
    ↓ generates: new NodeSpec(s), EdgeSpec(s)
DerivedGraph (extended LangGraph)
    ↓ execute with full MLFlow tracing
Execution Trace (every new node logged with expansion path)
    ↓ if expansion = persistent
Updated WorkflowConfig (or child config with parent reference)
```

### Expansion Modalities

**Ephemeral expansion** (default):
- New nodes exist only for this execution
- Nothing written back to YAML
- Useful for: exploratory runs, dynamic depth research, one-off sub-tasks
- Fully traced via MLFlow — you can replay the exact expansion

**Persistent expansion**:
- New nodes written back to config (or as a child config deriving from parent)
- Workflow "learns" new structure across runs
- Useful for: when a successful ephemeral expansion proves valuable
- Requires explicit opt-in: `expansion: persistent` + review mechanism

### Expansion Triggers

Expansion can be triggered by:
1. **LLM decision** — node output includes an expansion signal
2. **Rule-based** — e.g., "if this node returns more than N items, spawn a parallel summarizer for each"
3. **Failure-based** — if a node fails repeatedly, expansion engine proposes an alternative path

Rule-based triggers (option 2) are available at Level 1 without the expansion engine. They are deterministic and fully auditable.

---

## Path-Based Traceability

Every execution has a canonical path:

```
workflow:research_agent@v1.2
  → node:search
  → node:evaluate [quality_score=4, condition=retry]
  → node:search [loop_iter=2]
  → node:evaluate [quality_score=8, condition=pass]
  → node:summarize
  → [expansion:ephemeral] node:deep_dive_ai_safety [source=expansion_engine]
  → node:finalize
  → END
```

Path format: `{workflow_name}@{version}/{node_id}[{context}]/{...}`

This path is:
- Stored in MLFlow as a trace attribute
- Replayable: given the same path + input, the execution can be reproduced
- Diffable: two paths from the same workflow can be compared to see where they diverged
- Auditable: enterprise compliance can inspect every decision point

Contrast with traditional agents where the "path" is a free-form reasoning string that cannot be systematically replayed.

---

## Two Tiers of Memory

The current v1.0 memory system is **content memory**: key-value facts extracted from LLM outputs, injected into future prompts. This is useful for personalization and context retention.

Phase 2 introduces **structural memory** as a distinct second tier:

| Tier | Name | Stores | Used By | Scope |
|------|------|--------|---------|-------|
| 1 | **Content memory** (v1.0) | Facts, context, preferences | Prompts in nodes | Per-agent |
| 2 | **Structural memory** (Phase 2) | Workflow patterns, successful expansion paths, routing decisions, node performance | Expansion engine | Per-workflow-type |

Structural memory enables self-evolution:
- "For research tasks with topic=AI Safety, the deep_dive expansion produced high-quality output 4/5 times"
- "When quality_score < 5, looping twice produced better results than looping once"
- "The web_search → scrape → synthesize chain works better than web_search → summarize for technical topics"

These patterns are stored as structured records, not free-form text. The expansion engine reads structural memory when making expansion decisions, biasing toward historically successful paths.

### Memory Schema (Phase 2 design, not final)

```
StructuralMemoryRecord:
  workflow_name: str
  pattern_type: expansion | routing | node_performance
  context: dict          # input characteristics that triggered this pattern
  action: dict           # what was done
  outcome: dict          # quality metrics, user feedback
  confidence: float      # 0-1, updated via Bayesian update
  run_count: int
  last_seen: datetime
```

---

## Workflow Evolution Lifecycle

```
Design (YAML) → Run (deterministic) → Observe (MLFlow traces)
       ↑                                        ↓
       └── Persist (if expansion approved) ← Expand (if needed)
```

At any point, the workflow author can:
1. **Review expansion history**: What new paths were generated?
2. **Approve/reject expansions**: Promote ephemeral → persistent
3. **Prune structural memory**: Remove patterns that no longer apply
4. **Version the workflow**: Tag a config snapshot as a named version

Automated evolution (without human review) is Level 3 only and requires explicit opt-in.

---

## The Expansion Engine

The expansion engine is itself a workflow — a meta-workflow that takes the current execution context and produces new graph structure:

```yaml
# expansion_engine.yaml (internal, not user-facing)
nodes:
  - id: read_context
    prompt: "Current workflow: {workflow_name}. Task: {task_description}. Gap: {expansion_trigger}."
    outputs: [task_analysis]

  - id: consult_structural_memory
    tools: [structural_memory_search]
    outputs: [relevant_patterns]

  - id: generate_expansion
    prompt: "Given task analysis and patterns, propose new nodes for this workflow."
    output_schema:
      type: object
      fields:
        - name: new_nodes
          type: list[NodeSpec]
        - name: rationale
          type: str
    outputs: [new_nodes, rationale]

  - id: validate_expansion
    prompt: "Validate that proposed nodes are within autonomy level {autonomy_level} constraints."
    outputs: [validated, rejection_reason]

edges:
  - {from: START, to: read_context}
  - {from: read_context, to: consult_structural_memory}
  - {from: consult_structural_memory, to: generate_expansion}
  - {from: generate_expansion, to: validate_expansion}
  - from: validate_expansion
    routes:
      - condition: {logic: "state.validated == true"}
        to: END
      - condition: {logic: "default"}
        to: END  # Return empty expansion if validation fails
```

The expansion engine runs synchronously within the parent workflow's execution context. Its output is immediately applied to the LangGraph before the next node executes.

---

## Integration with Optimization (MLFlow + DSPy)

**Current approach (Phase 1.1)**: MLFlow 3.9 for observability — traces, costs, latency per node. Gives you the data to manually improve workflows.

**Phase 2 approach**: MLFlow evaluation framework for automated quality scoring. Define a metric (e.g., "output quality score from LLM-as-judge"), run evaluation sweeps, identify which nodes/paths underperform.

**Phase 3 (conditional)**: DSPy prompt optimization. If MLFlow evaluation reveals consistent underperformance that manual prompt tuning cannot fix — especially across different LLMs — DSPy compilation is the right tool. DSPy treats prompts as learnable parameters and optimizes them against a metric, producing model-specific compiled programs.

The decision to add DSPy is explicitly deferred and conditional. It will be revisited when:
1. MLFlow evaluation is fully integrated (Phase 2)
2. Cross-LLM consistency is tested and found insufficient
3. The cost of DSPy compilation per workflow is understood

DSPy and MLFlow are complementary, not competing:
- MLFlow: "Did this run succeed? Where was it slow/expensive?"
- DSPy: "How do I make the prompts better across all models?"

---

## VenaAI GTM — Phase 1 Reference Case

The immediate use case (VenaAI GTM workflows: copy generation, research, lead enrichment) lives at **Level 0 autonomy** — fully deterministic, no expansion. This is intentional and correct for that use case.

The characteristics that make GTM workflows a good Phase 1 fit:
- Fine-tuned once, run many times with changing inputs (topic, company, ICP)
- Consistent output structure required (copy format, research schema)
- Cost predictability matters
- Memory disabled per run for consistency (via T-014 runtime override)

As workflows mature, they may move to Level 1 autonomy — where a research workflow can select from a library of pre-defined sub-workflows (deep dive, competitive analysis, trend synthesis) based on the input topic. This is the bridge from Phase 1 to Phase 2.

---

## What Phase 2 Is NOT

To keep scope clear:

- **Not an open-ended agent system**: Expansion is bounded by autonomy level and structural constraints. Level 0-2 is not AutoGPT.
- **Not a visual builder**: Config remains code-first. The expansion engine generates YAML/config records, not a drag-and-drop UI.
- **Not multi-tenant**: Single user/team scope in Phase 2. Enterprise multi-tenancy is Phase 3.
- **Not a model marketplace**: The tool registry expands, but there is no marketplace or third-party plugin system.
- **Not autonomous without human oversight**: Persistent expansion requires explicit human approval in Phase 2. Fully autonomous evolution is Level 3 / Phase 3+.

---

*This document is a vision record. It does not authorize any implementation. Phase 2 begins when explicitly decided by the project owner.*
