# LLM Providers Module

The LLM module provides multi-provider support for Large Language Model integrations.

## Provider Interface

### BaseLLMProvider

```{py:class} configurable_agents.llm.provider.BaseLLMProvider
```

Abstract base class for LLM providers.

**Methods:**
- `generate(prompt: str, **kwargs) -> str` - Generate text from prompt
- `generate_stream(prompt: str, **kwargs) -> Iterator[str]` - Stream generated text

## Implementations

### Google Provider

```{py:class} configurable_agents.llm.google.GoogleProvider
```

Google Gemini LLM provider.

**Configuration:**

```python
from configurable_agents.llm.google import GoogleProvider

provider = GoogleProvider(
    model="gemini-1.5-flash",
    api_key="your-api-key",
    temperature=0.7,
    max_tokens=1024
)
```

**Environment Variables:**
- `GOOGLE_API_KEY` - Google API key

### LiteLLM Provider

```{py:class} configurable_agents.llm.litellm_provider.LiteLLMProvider
```

Multi-provider wrapper using LiteLLM.

**Supported Providers:**
- OpenAI (`gpt-4`, `gpt-3.5-turbo`)
- Anthropic (`claude-3-opus`, `claude-3-sonnet`)
- Ollama (local models)
- Cohere, Hugging Face, and more

**Configuration:**

```python
from configurable_agents.llm.litellm_provider import LiteLLMProvider

provider = LiteLLMProvider(
    model="openai/gpt-4",
    api_key="your-api-key",
    temperature=0.7
)
```

**Environment Variables:**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OLLAMA_BASE_URL` - Ollama server URL (default: `http://localhost:11434`)

## Full API

```{py:module} configurable_agents.llm
```

## See Also

- [Configuration Reference](../CONFIG_REFERENCE.md) - LLM configuration options
- [Tools Module](tools.md) - Tool integrations
