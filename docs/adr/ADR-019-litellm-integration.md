# ADR-019: LiteLLM Multi-Provider Integration

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs to support multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama) to give users flexibility in model selection, cost management, and deployment options (cloud vs local).

### Requirements

- **RT-05**: User can configure any supported LLM provider per node
- **RT-06**: User can run workflows entirely on local models via Ollama (zero cloud cost, full privacy)

### Constraints

- Google Gemini provider must maintain direct LangChain implementation for optimal compatibility (ADR-005)
- Other providers (OpenAI, Anthropic) should use LiteLLM abstraction to reduce integration complexity
- Ollama local models must be tracked as zero-cost
- Provider detection must work from model names (e.g., "gpt-4" → OpenAI)

---

## Decision

**Use LiteLLM wrapper for OpenAI, Anthropic, and Ollama providers. Keep Google Gemini as direct LangChain implementation.**

---

## Rationale

### Why LiteLLM for OpenAI/Anthropic/Ollama?

1. **Unified API**: LiteLLM provides consistent interface across 100+ LLM providers
2. **Reduced Integration Surface**: One library instead of separate LangChain providers for each
3. **Automatic Provider Detection**: Infers provider from model name (e.g., "claude-3-opus" → Anthropic)
4. **Cost Tracking**: Built-in token usage and cost estimation
5. **Retry Logic**: Automatic retries with exponential backoff
6. **Structured Output**: Compatible with LangChain's `with_structured_output()`

### Why Direct Implementation for Google?

1. **LangChain Compatibility**: Direct `ChatGoogleGenerativeAI` integration tested and verified (ADR-001)
2. **No Wrapper Overhead**: One less abstraction layer for the most-used provider
3. **Debugging**: Easier to debug issues without LiteLLM indirection
4. **Existing Investment**: Already implemented and tested in v0.1

### Why Hybrid Approach?

- **Best of Both Worlds**: Optimal path for Google (direct), unified abstraction for others (LiteLLM)
- **Migration Path**: Can add more LiteLLM providers without new code
- **Fallback**: If LiteLLM has issues, can fall back to direct LangChain implementations

---

## Implementation

### Architecture

```python
def create_llm(config: LLMConfig) -> BaseChatModel:
    """Create LLM instance based on provider"""
    if config.provider == "google":
        return create_google_llm(config)  # Direct LangChain
    elif config.provider in ["openai", "anthropic", "ollama"]:
        return create_litellm_llm(config)  # LiteLLM wrapper
    else:
        raise LLMProviderError(f"Unsupported provider: {config.provider}")
```

### Provider Detection

```python
def detect_provider(model: str) -> str:
    """Detect provider from model name"""
    if model.startswith("gemini-"):
        return "google"
    elif model.startswith("gpt-"):
        return "openai"
    elif model.startswith("claude-"):
        return "anthropic"
    elif model in ["llama2", "mistral", "codellama"]:
        return "ollama"
    else:
        return "unknown"
```

### Ollama Special Handling

```python
def create_litellm_llm(config: LLMConfig) -> BaseChatModel:
    """Create LiteLLM wrapper"""
    model = config.model
    if config.provider == "ollama":
        model = f"ollama_chat/{model}"  # LiteLLM prefix

    return ChatOpenAI(
        model=model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        # ... other params
    )
```

### Cost Tracking

```python
def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate LLM API cost"""
    if provider == "ollama":
        return 0.0  # Local models are free
    elif provider == "google":
        return GOOGLE_PRICING[model].calculate(input_tokens, output_tokens)
    elif provider in ["openai", "anthropic"]:
        return LiteLLMcost_estimator.estimate(provider, model, input_tokens, output_tokens)
```

---

## Configuration

### Global LLM Config

```yaml
config:
  llm:
    provider: "openai"
    model: "gpt-4-turbo"
    temperature: 0.7
```

### Node-Level Override

```yaml
nodes:
  - id: creative_node
    llm:
      provider: "anthropic"
      model: "claude-3-opus"
      temperature: 0.9
```

### Ollama Local Models

```yaml
config:
  llm:
    provider: "ollama"
    model: "mistral"
    temperature: 0.7
```

---

## Alternatives Considered

### Alternative 1: Direct LangChain for All Providers

**Pros**:
- Maximum control
- No wrapper overhead
- Consistent debugging experience

**Cons**:
- Requires implementing and maintaining 4 separate integrations
- More code to test and maintain
- Slower time to market for v1.0

**Why rejected**: LiteLLM reduces integration surface by 75% while maintaining compatibility.

### Alternative 2: LiteLLM for All Providers (including Google)

**Pros**:
- Most consistent approach
- Single code path for all providers

**Cons**:
- Adds unnecessary abstraction for Google (already working well)
- harder debugging (one more layer)
- Potential LiteLLM bugs for Google provider

**Why rejected**: Google direct implementation is proven and tested. No benefit to adding LiteLLM wrapper.

### Alternative 3: OpenAI Library for All (OpenAI-compatible API)

**Pros**:
- Single library
- OpenAI SDK is well-maintained

**Cons**:
- Not all providers support OpenAI-compatible API (Anthropic has differences)
- Loses provider-specific features
- Locks into OpenAI API semantics

**Why rejected**: Loses flexibility to use provider-specific features.

---

## Consequences

### Positive Consequences

1. **Multi-Provider Support**: Users can choose optimal provider per use case
2. **Cost Optimization**: Users can mix expensive (Claude Opus) and cheap (GPT-3.5) models
3. **Local Privacy**: Ollama support enables fully local workflows
4. **Future-Proof**: Easy to add more LiteLLM providers (Cohere, HuggingFace, etc.)
5. **Reduced Maintenance**: LiteLLM handles provider API updates

### Negative Consequences

1. **LiteLLM Dependency**: Adds another dependency to the project
2. **Debugging Complexity**: Two code paths (direct vs LiteLLM) to debug
3. **Provider Limitations**: Limited by LiteLLM's feature support for each provider
4. **Cost Tracking Complexity**: Need to aggregate costs from multiple sources

### Risks

#### Risk 1: LiteLLM Has Issues with Specific Provider

**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Can fall back to direct LangChain implementation if needed (reversible decision).

#### Risk 2: LiteLLM Cost Estimation Inaccurate

**Likelihood**: Medium
**Impact**: Low
**Mitigation**: Cost tracking is best-effort for OpenAI/Anthropic. Users can verify costs in respective provider dashboards.

#### Risk 3: LiteLLM Abstraction Leaks

**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Comprehensive testing with all supported providers before v1.0 release.

---

## Related Decisions

- [ADR-001](ADR-001-langgraph-execution-engine.md): LangGraph execution engine (compatible with LiteLLM)
- [ADR-005](ADR-005-multi-llm-provider-v10.md): Multi-LLM provider support (v1.0 expansion)
- [ADR-011](ADR-011-mlflow-observability.md): Cost tracking across providers

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/llm/litellm.py` - LiteLLM wrapper implementation
- `src/configurable_agents/llm/provider.py` - Provider factory with LiteLLM support
- `src/configurable_agents/observability/multi_provider_cost_tracker.py` - Cost aggregation

**Testing**: 19 integration tests with real API calls to all supported providers

---

## Superseded By

None (current)
