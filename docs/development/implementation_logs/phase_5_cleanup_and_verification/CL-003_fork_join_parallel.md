# CL-003: Fork-Join Parallel Replacement

**Task**: Replace MAP/Send parallel with fork-join parallel
**Date**: 2026-02-08
**Status**: COMPLETE
**Change Level**: 3 (STRUCTURAL — multi-file, new abstraction)

---

## Problem

Config 07 (parallel execution) crashed with `'dict' object has no attribute 'model_copy'`
because the MAP pattern used LangGraph `Send` objects that pass raw dicts as state.
Prior session fixes (dict returns, dict-to-model conversion) got the workflow running but
exposed deeper issues:

1. **List fields explode** — `_list_concat_reducer` fires on every field in full state return
2. **Parallel item not surfaced** — `_parallel_item` injected by Send but never reaches prompt
3. **Send objects incompatible** — Pass raw dicts, but Pydantic models expected

## Solution

Replace MAP parallel (Send-based) with fork-join parallel (native LangGraph edges).

Fork-join: different nodes run concurrently via multiple `add_edge()` calls.
No Send objects, no dict-vs-model issues.

**Schema change**: `EdgeConfig.to` accepts `Union[str, List[str]]`:
```yaml
# Fork-join: both nodes run in parallel
edges:
  - from: START
    to: [analyze_pros, analyze_cons]
```

## Implementation (10 Phases)

### Phase 1: Schema
- Deleted `ParallelConfig` class
- Changed `EdgeConfig.to`: `Optional[str]` → `Optional[Union[str, List[str]]]`
- Removed `parallel` field from `EdgeConfig`
- Added list `to` validation: min 2 targets, no duplicates, no empty strings

### Phase 2: Exports cleanup
- Removed `ParallelConfig` from `config/__init__.py`
- Removed parallel imports from `core/__init__.py`

### Phase 3: Validator
- Removed `_validate_parallel_edges()` call and function
- Updated `_validate_edge_references` for list `to`
- Updated `_validate_graph_structure` adjacency building for list `to`
- Changed START edge count: counts EdgeConfig objects, not adjacency set size

### Phase 4: Graph builder
- Removed `create_fan_out_function` import
- Removed `state_model` param from `make_node_function`
- Updated `_add_edge`: list `to` → multiple `add_edge()` calls
- Updated `_describe_edge` for list `to`

### Phase 5: Delete parallel.py
- Removed entire 149-line Send-based parallel module

### Phase 6: Dict validation in node executor
- Added validation after building updates dict:
  ```python
  merged = {**state.model_dump(), **updates}
  type(state).model_validate(merged)
  ```

### Phase 7-8: Rewrite test configs
- Config 07: Two branch nodes (`analyze_pros`, `analyze_cons`) fork from START, join at `combine`
- Config 12: Proper `routes:` and `loop:` syntax, sequential deep path

### Phase 9: Update tests
- Deleted `test_parallel.py`
- Added `TestEdgeConfigForkJoin` in test_schema.py
- Added `test_fork_join_edge_supported` in test_graph_builder.py
- Added fork-join validator tests in test_validator.py

### Phase 10: Updated test_configs/README.md

## Files Changed (14 total)

| File | Action |
|------|--------|
| `src/configurable_agents/config/schema.py` | Modified |
| `src/configurable_agents/config/__init__.py` | Modified |
| `src/configurable_agents/config/validator.py` | Modified |
| `src/configurable_agents/core/graph_builder.py` | Modified |
| `src/configurable_agents/core/parallel.py` | **DELETED** |
| `src/configurable_agents/core/__init__.py` | Modified |
| `src/configurable_agents/core/node_executor.py` | Modified |
| `test_configs/07_parallel_execution.yaml` | Rewritten |
| `test_configs/12_full_featured.yaml` | Rewritten |
| `test_configs/README.md` | Updated |
| `tests/core/test_parallel.py` | **DELETED** |
| `tests/core/test_graph_builder.py` | Modified |
| `tests/config/test_schema.py` | Modified |
| `tests/config/test_validator.py` | Modified |

## Testing

### Unit Tests
- 1366 passed, 25 failed, 37 skipped, 23 errors
- All failures are pre-existing (dict-vs-Pydantic, storage unpacking, deploy artifacts)
- Zero new failures introduced

### Test Config Execution (all 12)
All configs validate and execute successfully:
- Config 07 (fork-join): `topic=AI` → distinct pros, cons, summary
- Config 12 (full-featured): Both shallow and deep paths verified

### User Manual Verification
- Config 07: `--input topic="AI"` → fork-join produces correct parallel results
- Config 12 shallow: `--input query="Latest AI news" --input depth="shallow"` → works
- Config 12 deep: `--input query="Latest AI news" --input depth="deep"` → works, `is_refined=true`

## Issues Encountered

1. **NameError: 'Type' not defined** — Accidentally removed `Type` from graph_builder imports.
   `build_graph` signature uses `Type[BaseModel]`. Fixed by adding it back.

2. **Config 12 unreachable nodes** — Routes can only target single nodes, so fork-join
   within a route branch doesn't work. Made deep path sequential instead.

## Key Decisions

- Fork-join over MAP: MAP uses Send objects (raw dicts), fork-join uses native edges (no issues)
- List `to` minimum 2 targets: Single-target list is meaningless, use string instead
- START edge count by EdgeConfig objects: A single edge with `to: [a, b]` is one entry point
