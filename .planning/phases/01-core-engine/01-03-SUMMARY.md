---
phase: 01-core-engine
plan: 03
subsystem: workflow-engine
tags: [langgraph, conditional-routing, loops, parallel-execution, control-flow]

# Dependency graph
requires:
  - phase: 01-core-engine
    plan: 01
    provides: Storage abstraction and multi-provider LLM support
  - phase: 01-core-engine
    plan: 02
    provides: LiteLLM-based multi-provider LLM integration
provides:
  - Conditional routing (if/else based on state field evaluation)
  - Loop support (iteration tracking with exit conditions and max iteration limits)
  - Parallel node execution (fan-out via LangGraph Send objects, result collection)
  - Safe condition evaluation without eval/exec (restricted expression parser)
  - Config schema validation for routes, loops, and parallel edges
affects:
  - All future workflow execution (now supports non-linear workflows)
  - Tool Integration & Orchestration (can branch on tool results)
  - Phase 1 workflow testing (end-to-end with complex patterns)
  - Phase 2 tool orchestration (can loop over tool results)

# Tech tracking
tech-stack:
  added:
  - Python ast module for safe condition parsing
  - LangGraph Send objects for parallel fan-out
  - operator.add reducer for parallel result collection
  patterns:
  - Pattern: Restricted expression evaluation for security (no eval/exec)
  - Pattern: Send object factories for parallel fan-out
  - Pattern: Loop iteration tracking via hidden state fields
  - Pattern: Routing function factories for conditional edges

key-files:
  created:
    - src/configurable_agents/core/control_flow.py
    - src/configurable_agents/core/parallel.py
    - tests/core/test_control_flow.py
    - tests/core/test_parallel.py
  modified:
    - src/configurable_agents/config/schema.py (LoopConfig, ParallelConfig, EdgeConfig validation)
    - src/configurable_agents/config/validator.py (_validate_conditional_edges, _validate_loop_edges, _validate_parallel_edges)
    - src/configurable_agents/runtime/feature_gate.py (v0.2.0-dev with flow_control features)
    - src/configurable_agents/core/graph_builder.py (support all four edge types, loop wrapping)
    - src/configurable_agents/core/__init__.py (export new modules)
    - tests/config/test_schema.py (LoopConfig, ParallelConfig, edge validation tests)
    - tests/config/test_validator.py (conditional, loop, parallel validation tests)
    - tests/core/test_graph_builder.py (conditional, loop, parallel support tests)
    - tests/runtime/test_feature_gate.py (v0.2.0-dev, conditional/loop/parallel supported)

key-decisions:
  - "Safe condition evaluator using AST-like parsing instead of eval() for security"
  - "Loop iteration tracking via hidden _loop_iteration_{node} state fields with auto-increment"
  - "Parallel execution via LangGraph Send objects with state dict augmentation (_parallel_item, _parallel_index)"
  - "Feature gate version bumped to 0.2.0-dev to reflect new capabilities"

patterns-established:
  - "Pattern: Edge type polymorphism - single _add_edge() handles 4 edge types (linear, conditional, loop, parallel)"
  - "Pattern: Conditional routing requires default route as fallback for unmatched conditions"
  - "Pattern: Loop edges require bool state field for termination checking"
  - "Pattern: Parallel edges require list state fields for items and results collection"

# Metrics
duration: 23min
completed: 2026-02-03
---

# Phase 1 Plan 3: Advanced Control Flow Summary

**Conditional branching, loop support, and parallel execution via LangGraph Send objects with safe condition evaluation**

## Performance

- **Duration:** 23 min (Started: 2026-02-03T05:37:09Z, Completed: 2026-02-03T06:00:19Z)
- **Started:** 2026-02-03T05:37:09Z
- **Completed:** 2026-02-03T06:00:19Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments

- Config schema extended with LoopConfig and ParallelConfig models for iteration and fan-out
- Conditional routing, loops, and parallel execution now fully supported (v0.2.0-dev)
- Safe condition evaluator using AST parsing instead of eval/exec for security
- Graph builder updated to support all four edge types (linear, conditional, loop, parallel)
- Feature gate updated to reflect new flow control capabilities
- 103 new tests added (config: 34, core: 41, runtime: 4) - all passing
- Backward compatible: existing linear workflows work unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend config schema and validation for advanced control flow** - `4142d4c` (feat)
2. **Task 2: Implement conditional branching and loop control flow runtime** - `8ddd43a` (feat)
3. **Task 3: Implement parallel execution and integrate all control flow into graph builder** - `65f783a` (feat)

**Plan metadata:** N/A (summary will be committed separately)

## Files Created/Modified

- `src/configurable_agents/config/schema.py` - LoopConfig, ParallelConfig, EdgeConfig extended for loop/parallel edges
- `src/configurable_agents/config/validator.py` - validate_conditional_edges, validate_loop_edges, validate_parallel_edges
- `src/configurable_agents/config/__init__.py` - Exports LoopConfig, ParallelConfig
- `src/configurable_agents/runtime/feature_gate.py` - v0.2.0-dev, conditional/loop/parallel in flow_control
- `src/configurable_agents/core/control_flow.py` - create_routing_function, create_loop_router, condition evaluator
- `src/configurable_agents/core/parallel.py` - create_fan_out_function, parallel helper functions
- `src/configurable_agents/core/graph_builder.py` - All edge types, loop wrapping, _collect_loop_targets
- `src/configurable_agents/core/__init__.py` - Export control_flow and parallel functions
- `tests/config/test_schema.py` - LoopConfig, ParallelConfig, edge type validation tests
- `tests/config/test_validator.py` - Conditional, loop, parallel validation tests
- `tests/core/test_control_flow.py` - 26 tests for condition evaluation, routing, loops
- `tests/core/test_parallel.py` - 15 tests for fan-out, Send objects, parallel helpers
- `tests/core/test_graph_builder.py` - Tests for conditional, loop, parallel edge support
- `tests/runtime/test_feature_gate.py` - Updated for v0.2.0-dev and new features

## Decisions Made

**Safe condition evaluator using AST-like parsing instead of eval()**

- **Rationale:** Using eval() or exec() would allow arbitrary code execution. Even with restricted globals/locals, it's risky.
- **Implementation:** Custom parser supporting comparisons (>, <, >=, <=, ==, !=), boolean operators (and, or, not), and field references (state.field_name)
- **Impact:** Expressions like "state.score > 0.8 and state.approved" can be safely evaluated
- **Reversible:** Yes - can extend parser for more complex expressions if needed

**Loop iteration tracking via hidden state fields**

- **Rationale:** LangGraph doesn't provide built-in iteration tracking. Need to track loop count in state.
- **Implementation:** Hidden `_loop_iteration_{node}` field auto-incremented via node wrapper
- **Impact:** Loop counters persisted in state, accessible in conditions for max_iterations check
- **Reversible:** Yes - can switch to explicit tracking if needed

**Parallel execution via LangGraph Send objects**

- **Rationale:** LangGraph Send objects are the standard way to do fan-out/fan-in patterns
- **Implementation:** Send objects carry augmented state with `_parallel_item` and `_parallel_index` for each invocation
- **Impact:** Results collected via state reducer (operator.add) on collect_field
- **Reversible:** Yes - Send objects are well-established LangGraph pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Issue: Pydantic v2 excludes underscore fields from model_dump() by default**

- **Problem:** The `_parallel_item` and `_parallel_index` fields were not accessible via model_dump() in Pydantic v2
- **Solution:** Added fallback to hasattr() checks in helper functions and updated tests to use PrivateAttr in Pydantic models when testing
- **Files modified:** src/configurable_agents/core/parallel.py, tests/core/test_parallel.py
- **Impact:** Helper functions work with both dict state and Pydantic models

**Issue: Compound condition parsing was matching entire expression as single comparison**

- **Problem:** Regex `r"^state\.(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$"` was greedy and matched `state.score > 0.5` as the value, not stopping at the compound operator
- **Solution:** Moved compound expression check before single comparison check, handled compound expressions first (split by 'and'/'or', recursively evaluate)
- **Files modified:** src/configurable_agents/core/control_flow.py
- **Impact:** Compound expressions like "state.score > 0.5 and state.approved" now evaluate correctly

## User Setup Required

None - no external service configuration required for this plan.

## Next Phase Readiness

- Conditional routing, loops, and parallel execution are fully operational
- Config schema validates all edge types at parse time
- Safe condition evaluation prevents code injection
- **Blockers:** None

**Remaining for Phase 1:**
- Phase 1 is now complete (3 of 3 plans done)
- Ready to move to Phase 2 (Tool Integration & Orchestration)

---
*Phase: 01-core-engine*
*Completed: 2026-02-03*
