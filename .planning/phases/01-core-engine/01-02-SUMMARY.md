---
phase: 01-core-engine
plan: 02
subsystem: llm-integration
tags: [litellm, multi-provider, langchain, cost-tracking]

# Dependency graph
requires:
  - phase: 01-core-engine
    plan: 01
    provides: Storage abstraction and config infrastructure
provides:
  - LiteLLM-based multi-provider LLM integration (OpenAI, Anthropic, Google, Ollama)
  - Cost estimation using LiteLLM pricing data
  - Config schema validation for all 4 providers
  - Comprehensive test coverage for multi-provider routing
affects:
  - All future workflow execution (multi-provider LLM selection via YAML)
  - Cost tracking and reporting across providers
  - Phase 1 workflow testing with different LLM backends

# Tech tracking
tech-stack:
  added:
    - litellm>=1.80.0 (multi-provider LLM abstraction)
  patterns:
    - Provider factory pattern with graceful degradation
    - Model string mapping (provider/model format for LiteLLM)
    - Direct provider path for Google (optimal LangChain compatibility)
    - LiteLLM via ChatLiteLLM wrapper for BaseChatModel interface

key-files:
  created:
    - src/configurable_agents/llm/litellm_provider.py
    - tests/llm/test_litellm_provider.py
  modified:
    - src/configurable_agents/llm/provider.py (multi-provider routing)
    - src/configurable_agents/config/schema.py (provider validation, api_base field)
    - src/configurable_agents/runtime/feature_gate.py (multi-provider feature listing)
    - src/configurable_agents/observability/cost_estimator.py (LiteLLM cost_per_token)
    - tests/llm/test_provider.py (multi-provider routing tests)
    - pyproject.toml (litellm>=1.80.0 dependency)

key-decisions:
  - "Google provider uses direct implementation (not LiteLLM) for optimal LangChain compatibility with bind_tools and with_structured_output"
  - "LiteLLM reserved for OpenAI, Anthropic, and Ollama providers"
  - "Ollama uses ollama_chat/ prefix per LiteLLM best practices (not ollama/)"
  - "Ollama local models tracked as zero-cost"
  - "Google Gemini uses gemini/ prefix in LiteLLM (not google/)"

patterns-established:
  - "Pattern: Provider factory with fallback - LiteLLM primary, direct Google for compatibility"
  - "Pattern: LITELLM_AVAILABLE flag for graceful degradation when dependency missing"
  - "Pattern: Model string mapping function converts config to LiteLLM format"

# Metrics
duration: 23min
completed: 2026-02-03
---

# Phase 1 Plan 2: Multi-Provider LLM Support Summary

**LiteLLM-based multi-provider LLM integration supporting OpenAI, Anthropic, Google Gemini, and Ollama local models through unified interface with LangChain BaseChatModel compatibility**

## Performance

- **Duration:** 23 min (Started: 2026-02-03T05:10:56Z, Completed: 2026-02-03T05:34:14Z)
- **Started:** 2026-02-03T05:10:56Z
- **Completed:** 2026-02-03T05:34:14Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- LiteLLM provider module with ChatLiteLLM wrapper for BaseChatModel interface
- Multi-provider factory routing: OpenAI, Anthropic, Google (direct), Ollama via LiteLLM
- Config schema validation for all 4 supported providers with api_base field
- Cost estimation using LiteLLM pricing with Ollama zero-cost tracking
- Feature gate updated to reflect multi-provider as supported
- Comprehensive test suite: 63 LLM tests passing (25 new LiteLLM-specific tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LiteLLM provider and update factory routing** - `5cc2b75` (feat)
2. **Task 2: Update cost estimation and add comprehensive tests** - `6d0c475` (feat)

## Files Created/Modified

- `src/configurable_agents/llm/litellm_provider.py` - LiteLLM provider implementation with model string mapping, ChatLiteLLM wrapper, direct completion function
- `src/configurable_agents/llm/provider.py` - Updated factory routing for all 4 providers, Google uses direct path for compatibility
- `src/configurable_agents/config/schema.py` - Provider field validator, api_base field for custom endpoints
- `src/configurable_agents/runtime/feature_gate.py` - Multi-provider moved from not_supported to llm features
- `src/configurable_agents/observability/cost_estimator.py` - LiteLLM cost_per_token integration, Ollama zero-cost
- `tests/llm/test_litellm_provider.py` - 25 comprehensive tests for model mapping, LLM creation, completion, error handling
- `tests/llm/test_provider.py` - Updated for multi-provider routing behavior
- `pyproject.toml` - Added litellm>=1.80.0 dependency

## Decisions Made

**Google provider uses direct implementation (not LiteLLM) for optimal LangChain compatibility**

- **Rationale:** When routing Google through LiteLLM, LangChain's `bind_tools()` adds `tool_choice="any"` which VertexAI doesn't support. Direct Google provider has better compatibility with LangChain features like `with_structured_output()` and `bind_tools()`.
- **Impact:** OpenAI, Anthropic, and Ollama route through LiteLLM; Google uses the existing `create_google_llm()` path.
- **Reversible:** Yes - can move Google to LiteLLM path once LangChain/LiteLLM compatibility improves.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Google/LiteLLM tool_choice incompatibility**

- **Found during:** Task 2 (integration test verification)
- **Issue:** VertexAI through LiteLLM rejects `tool_choice="any"` added by LangChain's `bind_tools()`. Error: "VertexAI doesn't support tool_choice=any. Supported tool_choice values=['auto', 'required', json object]"
- **Fix:** Changed routing logic to use direct Google provider (`create_google_llm()`) instead of LiteLLM for Google provider. This provides better LangChain compatibility and maintains backward compatibility.
- **Files modified:** `src/configurable_agents/llm/provider.py`
- **Verification:** All integration tests pass (687 passed, 5 pre-existing unrelated failures)
- **Committed in:** `6d0c475` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary for correctness and backward compatibility. No scope creep. Multi-provider goal achieved with Google using optimal path.

## Issues Encountered

**Issue: LiteLLM `drop_params` configuration didn't prevent tool_choice parameter**

- **Problem:** Set `litellm.drop_params = True` and environment variable, but `tool_choice="any"` still caused VertexAI errors
- **Root cause:** LangChain's `bind_tools()` adds parameters at a higher level before LiteLLM can intercept/drop them
- **Solution:** Use direct Google provider path which has better LangChain compatibility

**Issue: Pydantic validates provider before LLMProviderError can be raised**

- **Problem:** Test expected `LLMProviderError` for invalid provider, but Pydantic's `@field_validator` raises `ValidationError` first
- **Solution:** Updated test to expect `ValidationError` for invalid provider

## User Setup Required

None - no external service configuration required for this plan. Users can:
- Set `provider: "ollama"` and `model: "llama3"` in YAML config for local models (requires Ollama running locally)
- Set `provider: "openai"` for OpenAI models (requires `OPENAI_API_KEY` env var)
- Set `provider: "anthropic"` for Anthropic models (requires `ANTHROPIC_API_KEY` env var)
- Set `provider: "google"` for Google models (requires `GOOGLE_API_KEY` env var, uses direct provider)

## Next Phase Readiness

- Multi-provider LLM integration complete for OpenAI, Anthropic, Google, Ollama
- Cost tracking supports all 4 providers with LiteLLM pricing
- Feature gate reflects multi-provider as supported
- **Blockers:** None

**Remaining for Phase 1:**
- Plan 01-03: Workflow execution engine improvements (if any remain)
- Then Phase 1 complete, ready for Phase 2 (Tool Integration & Orchestration)

---
*Phase: 01-core-engine*
*Completed: 2026-02-03*
