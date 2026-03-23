# T-015: Memory Fact Extraction — Make Opt-In

**Status**: TODO
**Priority**: HIGH
**Created**: 2026-03-23

---

## Problem

Every node with `memory.enabled: true` makes an extra full LLM API call to extract "facts" from the node's output via `_extract_memory_facts()`. This call:

1. Uses the same LLM as the node itself (potentially GPT-4 / Claude Opus)
2. Is always-on — no way to disable without disabling memory entirely
3. Doubles LLM cost and latency for every memory-enabled node
4. Is never surfaced to the user (no log indicating it happened)

For a 5-node workflow with memory enabled, 10 LLM calls are made, not 5. With no visibility into this.

The extraction is also of questionable value for deterministic/template workflows (GTM copy generation, structured research) where the goal is consistent output, not learning facts for future runs.

---

## Success Criteria

- `memory.extract_facts: false` (new default) disables the extraction LLM call
- `memory.extract_facts: true` enables extraction — user explicitly opts in
- `memory.extraction_model` allows specifying a cheaper model for extraction (e.g., `gpt-4o-mini`)
- Existing configs with `memory.enabled: true` and no `extract_facts` field default to `false` (opt-in)
- When extraction runs, it is logged at INFO level with the model used and facts extracted count

---

## Implementation Approach

### Step 1: Add `extract_facts` and `extraction_model` to `MemoryConfig`

**File**: `src/configurable_agents/config/schema.py`

```python
class MemoryConfig(BaseModel):
    enabled: bool = Field(False)
    default_scope: Literal["agent", "workflow", "node"] = Field("agent")
    max_entries: int = Field(50)
    extract_facts: bool = Field(
        False,
        description="Enable automatic fact extraction from node outputs. "
                    "Makes an extra LLM call per node. Default: False (opt-in)."
    )
    extraction_model: Optional[str] = Field(
        None,
        description="Model to use for fact extraction (e.g., 'gpt-4o-mini'). "
                    "If None, uses the node's configured LLM. A cheaper model is recommended."
    )
```

### Step 2: Guard extraction call in `execute_node()`

**File**: `src/configurable_agents/core/node_executor.py`

In the memory write section (currently lines ~648-664), wrap with guard:

```python
if agent_memory is not None:
    # Write explicit outputs to memory if enabled
    # (auto-extraction is opt-in — see memory.extract_facts)
    if memory_config and memory_config.extract_facts:
        try:
            # Use extraction model if specified, otherwise node's LLM
            extraction_llm = llm
            if memory_config.extraction_model:
                extraction_llm = create_llm(_build_extraction_llm_config(
                    memory_config.extraction_model, merged_llm_config
                ))

            output_summary = "; ".join(f"{k}={v}" for k, v in updates.items() if v)
            facts = _extract_memory_facts(extraction_llm, resolved_prompt, output_summary)

            if facts:
                for key, value in facts:
                    agent_memory.write(key, value)
                logger.info(
                    f"Node '{node_id}': Extracted and stored {len(facts)} memory facts "
                    f"(model: {memory_config.extraction_model or 'node LLM'})"
                )
            else:
                logger.debug(f"Node '{node_id}': No facts extracted for memory")
        except Exception as e:
            logger.warning(f"Node '{node_id}': Memory fact extraction failed: {e}")
    else:
        logger.debug(
            f"Node '{node_id}': Memory enabled but extract_facts=False — "
            "skipping fact extraction. Set memory.extract_facts: true to enable."
        )
```

### Step 3: Helper to build extraction LLM config

```python
def _build_extraction_llm_config(model_name: str, base_config) -> LLMConfig:
    """Build minimal LLM config for fact extraction using specified model."""
    # Parse provider from model name or inherit from base config
    # e.g., "gpt-4o-mini" → provider=openai, model=gpt-4o-mini
    # e.g., "claude-haiku-4-5" → provider=anthropic
    provider = _infer_provider_from_model(model_name) or base_config.provider
    return LLMConfig(provider=provider, model=model_name, temperature=0.0)
```

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/config/schema.py` | Add `extract_facts`, `extraction_model` to `MemoryConfig` |
| `src/configurable_agents/core/node_executor.py` | Guard extraction call with `extract_facts` flag, add extraction model support |

---

## Testing Strategy

**Unit tests**:
- Verify `extract_facts: false` (default) results in zero extraction LLM calls
- Verify `extract_facts: true` triggers extraction call
- Verify `extraction_model: "gpt-4o-mini"` creates a different LLM for extraction

**Integration tests**:
- Memory-enabled workflow without `extract_facts` → no extra LLM calls, memory write still works for manual writes (if any)
- Memory-enabled workflow with `extract_facts: true` → extraction happens, facts stored
- Verify existing memory configs are not broken (default to `extract_facts: false`)

---

## Migration Notes

- **Breaking change for existing memory users**: If you currently rely on automatic fact extraction, add `extract_facts: true` to your `memory` config block.
- The extraction behavior was undocumented and carried hidden cost — making it opt-in is the correct default.
- This change is composable with T-014: `--memory-scope none` disables memory entirely; this controls whether extraction runs when memory IS enabled.
