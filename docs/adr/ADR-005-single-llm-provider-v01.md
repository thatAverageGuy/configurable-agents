# ADR-005: Single LLM Provider (Google Gemini) in v0.1

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

The system needs to call LLMs to execute workflow nodes. Multiple LLM providers exist:

- **Google (Gemini)**: gemini-2.0-flash-exp, gemini-1.5-pro, etc.
- **OpenAI (GPT)**: gpt-4o, gpt-4o-mini, o1, etc.
- **Anthropic (Claude)**: claude-3-5-sonnet, claude-3-5-haiku, etc.
- **Local (Ollama)**: llama3, mistral, etc.

Users may want to:
1. Switch between providers based on task
2. Use cheapest provider for simple tasks
3. Use local models for privacy/cost
4. Compare providers for same task

---

## Decision

**v0.1 will support ONLY Google Gemini.**

Multi-provider support is deferred to v0.2+.

---

## Rationale

### 1. Faster Time to Value

**Single provider**:
- Implement one LLM integration
- Test one API
- Handle one set of errors
- Document one provider

**Estimated time**: 1 week

**Multi-provider**:
- Implement 3+ integrations
- Handle provider-specific quirks (rate limits, errors, features)
- Build abstraction layer
- Test all combinations
- Document all providers

**Estimated time**: 3-4 weeks

**Tradeoff**: Get to v0.1 faster with single provider, add others later.

### 2. Gemini is Sufficient for v0.1

**Gemini advantages**:
- **Good free tier**: 1500 requests/day (enough for development)
- **Fast**: Low latency (important for testing)
- **Cheap**: $0.00 for flash models (cost-effective for users)
- **Structured outputs**: Native JSON mode (required for our Pydantic schemas)
- **Tool calling**: Supports function calling (for tool integration)
- **Good quality**: Competitive with GPT-4 for most tasks

**For v0.1 goals**, Gemini covers all needs.

### 3. Provider Abstraction Can Come Later

**v0.1 implementation**:
```python
# Direct Gemini integration
from langchain_google_genai import ChatGoogleGenerativeAI

def create_llm(config):
    return ChatGoogleGenerativeAI(
        model=config['model'],
        temperature=config['temperature']
    )
```

**v0.2 implementation** (after we learn what we need):
```python
# Provider abstraction
class LLMProvider(ABC):
    def create_llm(self, config): ...

class GeminiProvider(LLMProvider):
    def create_llm(self, config):
        return ChatGoogleGenerativeAI(...)

class OpenAIProvider(LLMProvider):
    def create_llm(self, config):
        return ChatOpenAI(...)

# Factory
def create_llm(config):
    provider = config.get('provider', 'google')
    if provider == 'google':
        return GeminiProvider().create_llm(config)
    elif provider == 'openai':
        return OpenAIProvider().create_llm(config)
```

**Why wait**:
- We don't know what abstraction we need yet
- Premature abstraction is wasteful
- Better to abstract based on real needs, not guessed ones

### 4. User Feedback Will Guide Multi-Provider Design

**Questions we'll answer in v0.1**:
- Do users want per-node provider selection?
- Do users want fallback providers (if Gemini rate-limited)?
- Do users need provider-specific features?
- What are common provider switching patterns?

**These answers inform v0.2 design.**

---

## Alternatives Considered

### Alternative 1: Support All Major Providers (Google, OpenAI, Anthropic)

**Config example**:
```yaml
config:
  llm:
    provider: google  # or openai, anthropic
    model: gemini-2.0-flash-exp
```

**Pros**:
- Users have choice from day one
- Can compare providers easily
- Future-proof

**Cons**:
- **3-4 weeks extra development** (dealbreaker for v0.1)
- Need to handle provider-specific quirks
- More testing surface
- More documentation
- Delays getting user feedback on core features

**Why rejected**: Too slow for v0.1. Add in v0.2.

### Alternative 2: Support Ollama (Local Models) Only

**Rationale**: Privacy-first, no API costs

**Pros**:
- No API keys needed
- Free to use
- Privacy (data doesn't leave machine)

**Cons**:
- **Slower inference** (local GPU/CPU)
- **Lower quality** (smaller models)
- **Setup complexity** (users must install Ollama)
- **Not beginner-friendly**

**Why rejected**: Gemini's free tier is good enough, and faster/easier for beginners.

### Alternative 3: Support OpenAI Only

**Pros**:
- Industry standard
- Best quality (GPT-4)
- Great documentation

**Cons**:
- **No free tier** (users need API key + billing)
- **More expensive** ($0.01-0.03 per 1K tokens)
- **Harder for beginners** (need credit card)

**Why rejected**: Gemini's free tier makes it easier for users to get started.

### Alternative 4: Provider-Agnostic Abstraction from Day One

**Approach**: Build abstraction layer, support 1 provider initially, easy to add more.

**Example**:
```python
class LLMProvider(ABC):
    @abstractmethod
    def call(self, prompt: str, schema: Type[BaseModel]) -> BaseModel:
        pass

class GeminiProvider(LLMProvider):
    def call(self, prompt, schema):
        # Gemini-specific implementation
        pass
```

**Pros**:
- Clean architecture
- Easy to add providers later

**Cons**:
- **Premature abstraction**
- Abstraction may not fit future providers
- Extra code with no immediate value
- Slower development

**Why rejected (for v0.1)**: YAGNI (You Aren't Gonna Need It). Abstract when we have 2+ implementations.

---

## Consequences

### Positive Consequences

1. **Faster Development**
   - 1 week vs 3-4 weeks
   - Can focus on core features
   - Reach users faster

2. **Simpler Codebase**
   - Less code to maintain
   - Easier to understand
   - Fewer edge cases

3. **Better Testing**
   - Test one provider thoroughly
   - Understand its quirks deeply

4. **Lower Barrier for Users**
   - Gemini free tier → no API costs
   - Easy to get started

5. **Clearer Scope**
   - v0.1 is intentionally limited
   - Sets expectations

### Negative Consequences

1. **Limited Choice**
   - Users must use Gemini
   - Can't use GPT-4, Claude, or local models

2. **Vendor Lock-In (Temporary)**
   - Configs use Gemini models
   - **Mitigation**: v0.2 adds multi-provider, configs can be migrated

3. **Provider-Specific Failures**
   - If Gemini has outage, workflows fail
   - **Mitigation**: Document in v0.1 limitations, add fallbacks in v0.2

4. **May Not Fit All Use Cases**
   - Some tasks may need GPT-4 quality
   - **Mitigation**: v0.2 adds other providers

### Risks

#### Risk 1: Gemini API Changes

**Likelihood**: Low (Google has stable APIs)
**Impact**: High (breaks all workflows)

**Mitigation**:
- Pin LangChain version
- Monitor Gemini API changelog
- Test with new versions before upgrading

#### Risk 2: Gemini Free Tier Removed

**Likelihood**: Medium (Google could change policy)
**Impact**: High (users need paid accounts)

**Mitigation**:
- Document that free tier may change
- Add Ollama support in v0.2 as free alternative
- v0.2 multi-provider allows users to switch

#### Risk 3: Users Demand Multi-Provider Immediately

**Likelihood**: Medium
**Impact**: Medium (user frustration)

**Mitigation**:
- Clearly document v0.1 limitations
- Roadmap shows v0.2 has multi-provider
- Collect feedback on which providers to prioritize

#### Risk 4: Hard to Add Providers Later

**Likelihood**: Low
**Impact**: High

**If we hardcode Gemini everywhere**:
```python
# Bad: Gemini hardcoded in many places
from langchain_google_genai import ChatGoogleGenerativeAI

def execute_node(node):
    llm = ChatGoogleGenerativeAI(...)  # Hardcoded
    result = llm.invoke(...)
```

**Mitigation**: Encapsulate LLM creation
```python
# Good: LLM creation is centralized
def create_llm(config):
    # All Gemini logic in one place
    return ChatGoogleGenerativeAI(...)

def execute_node(node, llm):
    # Doesn't know about provider
    result = llm.invoke(...)
```

**In v0.2**, we only change `create_llm()`, not all callsites.

---

## Migration Path to Multi-Provider (v0.2)

### Step 1: Add Provider Field (v0.2)

```yaml
config:
  llm:
    provider: google  # NEW: Default to google for backwards compat
    model: gemini-2.0-flash-exp
```

### Step 2: Implement Provider Factory

```python
class LLMProvider(ABC):
    @abstractmethod
    def create_llm(self, config: dict) -> BaseChatModel:
        pass

class GoogleProvider(LLMProvider):
    def create_llm(self, config):
        return ChatGoogleGenerativeAI(...)

class OpenAIProvider(LLMProvider):
    def create_llm(self, config):
        return ChatOpenAI(...)

def get_provider(name: str) -> LLMProvider:
    providers = {
        'google': GoogleProvider(),
        'openai': OpenAIProvider(),
        'anthropic': AnthropicProvider(),
    }
    return providers[name]
```

### Step 3: Update Node Execution

```python
# v0.1
def execute_node(node_config, state):
    llm = create_llm(global_config['llm'])  # Always Gemini
    ...

# v0.2
def execute_node(node_config, state):
    # Merge global + node config
    llm_config = merge_llm_config(global_config['llm'], node_config.get('llm', {}))

    # Get provider
    provider = get_provider(llm_config['provider'])
    llm = provider.create_llm(llm_config)
    ...
```

### Step 4: Handle Provider-Specific Features

```python
# Some providers support features others don't
if provider.supports_structured_output():
    result = llm.invoke(prompt, response_format=schema)
else:
    # Fallback: prompt engineering + JSON parsing
    result = llm.invoke(prompt + "\nReturn JSON:")
    parsed = json.loads(result)
```

---

## Per-Node Provider Selection (v0.3+)

```yaml
nodes:
  - id: research
    llm:
      provider: google  # Use Gemini (fast, cheap)
      model: gemini-2.0-flash-exp

  - id: write
    llm:
      provider: anthropic  # Use Claude (better writing)
      model: claude-3-5-sonnet

  - id: review
    llm:
      provider: openai  # Use GPT-4 (best reasoning)
      model: gpt-4o
```

---

## Default Model Selection

### v0.1 Defaults

```yaml
config:
  llm:
    provider: google
    model: gemini-2.0-flash-exp  # Default
    temperature: 0.7
```

**Why `gemini-2.0-flash-exp`?**
- **Free tier**: 1500 requests/day
- **Fast**: Low latency (~1-2 seconds)
- **Good quality**: Competitive with GPT-4 Turbo
- **Cheap**: $0.00 (flash) or $0.00015/1K tokens (paid tier)

### Alternative Gemini Models (v0.1)

Users can override in config:
- `gemini-2.0-flash-exp`: Fast, cheap, good quality (DEFAULT)
- `gemini-2.0-flash-lite`: Faster, simpler tasks
- `gemini-1.5-pro`: Higher quality, slower, more expensive
- `gemini-1.5-flash`: Balance of speed and quality

---

## Documentation Strategy

### Clearly Document v0.1 Limitations

In README and docs:
```markdown
## Supported LLM Providers (v0.1)

**v0.1 supports Google Gemini only.**

Supported models:
- gemini-2.0-flash-exp (default, free tier)
- gemini-2.0-flash-lite
- gemini-1.5-pro
- gemini-1.5-flash

**Coming in v0.2:**
- OpenAI (GPT-4, GPT-4o, etc.)
- Anthropic (Claude 3.5 Sonnet, etc.)
- Ollama (local models)

See [Task Breakdown](../TASKS.md) for timeline.
```

### Gemini Setup Guide

```markdown
## Getting Started with Gemini

1. Get API key: https://makersuite.google.com/app/apikey
2. Set environment variable:
   ```bash
   export GOOGLE_API_KEY="your-api-key"
   ```
3. Run workflow:
   ```bash
   python -m configurable_agents run workflow.yaml
   ```

**Free tier**: 1500 requests/day (more than enough for development)
```

---

## Testing Strategy

### T-009: LLM Provider Tests

**Unit tests**:
- Create LLM with various configs
- Test parameter passing (temperature, max_tokens)
- Mock API calls

**Integration tests** (with real API):
- Test simple prompt
- Test structured output (Pydantic schema)
- Test with tools
- Test error handling (rate limit, timeout)

**Mark as slow tests** (run separately in CI):
```python
@pytest.mark.slow
@pytest.mark.integration
def test_gemini_structured_output_real_api():
    # Requires GOOGLE_API_KEY
    ...
```

---

## Future: Provider Comparison Tool (v0.3+)

```bash
# Run same workflow with different providers
python -m configurable_agents compare workflow.yaml \
  --providers google,openai,anthropic \
  --input topic="AI Safety"

Results:
  Google (gemini-2.0-flash-exp):
    Cost: $0.001
    Time: 2.3s
    Quality: 8/10

  OpenAI (gpt-4o):
    Cost: $0.015
    Time: 3.1s
    Quality: 9/10

  Anthropic (claude-3-5-sonnet):
    Cost: $0.012
    Time: 2.7s
    Quality: 9/10
```

---

## References

- Gemini API: https://ai.google.dev/
- Gemini pricing: https://ai.google.dev/pricing
- LangChain Google GenAI: https://python.langchain.com/docs/integrations/chat/google_generative_ai

---

## Notes

This decision prioritizes **speed to v0.1** over **feature completeness**.

Multi-provider support is valuable, but not critical for validating the core architecture. Better to ship v0.1 with one provider, learn from users, then add others in v0.2.

**Key principle**: Start focused, expand based on demand.

**Quote**: "Premature optimization is the root of all evil" - Donald Knuth
**Corollary**: "Premature abstraction is premature optimization."

---

## Implementation Status

**Status**: 2705 Implemented in v0.1
**Related Tasks**: T-009 (LLM Provider), T-012 (Graph Builder), T-013 (Runtime Executor)
**Enforcement**: Feature gating (T-004.5) blocks unsupported features
**Date Implemented**: 2026-01-26 to 2026-01-27

This design constraint is enforced by:
1. Config validator - Rejects unsupported features at parse time
2. Feature gating - Hard blocks for v0.2+ features
3. Limited implementation - Only v0.1 features implemented

---

## Superseded By

None (current)
