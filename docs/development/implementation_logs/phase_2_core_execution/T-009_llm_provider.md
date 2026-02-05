# T-009: LLM Provider

**Status**: ✅ Complete
**Completed**: 2026-01-25
**Commit**: T-009: LLM provider - Google Gemini integration
**Phase**: Phase 2 (Core Execution)
**Progress After**: 10/20 tasks (50%)

---

## 🎯 What Was Done

- Implemented LLM provider factory with Google Gemini support
- Created structured output calling with Pydantic schema enforcement
- Comprehensive error handling and retry logic
- Configuration merging (node-level overrides global settings)
- API key validation with helpful setup instructions
- 32 comprehensive tests covering all scenarios
- Total: 300 tests passing (up from 268)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/llm/
├── provider.py (LLM factory and core functionality)
├── google.py (Google Gemini implementation)
└── __init__.py (public API exports)
```

### Tests

```
tests/llm/
├── __init__.py
├── test_provider.py (19 provider tests)
└── test_google.py (13 Google tests + 2 integration tests)
```

---

## 🔧 How to Verify

### 1. Test LLM provider

```bash
pytest tests/llm/test_provider.py -v
# Expected: 19 passed
```

### 2. Test Google Gemini

```bash
pytest tests/llm/test_google.py -v -m "not integration"
# Expected: 13 passed
```

### 3. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 300 passed (32 llm + 268 existing)
```

### 4. Use LLM provider

```python
import os
os.environ["GOOGLE_API_KEY"] = "your-key-here"

from configurable_agents.llm import create_llm, call_llm_structured
from configurable_agents.config import LLMConfig
from pydantic import BaseModel

# Create LLM
config = LLMConfig(model="gemini-2.5-flash-lite", temperature=0.7)
llm = create_llm(config)

# Call with structured output
class Greeting(BaseModel):
    message: str

result = call_llm_structured(llm, "Say hello", Greeting)
print(result.message)
```

---

## ✅ What to Expect

**Working**:
- ✅ LLM instances created from config
- ✅ Structured outputs with Pydantic validation
- ✅ Node config overrides global config
- ✅ Automatic retries on failures
- ✅ Helpful error messages with setup instructions
- ✅ Tool binding for LLM calls
- ✅ Rate limit handling with exponential backoff
- ⚠️ Only Google Gemini supported in v0.1 (more providers in v0.2+)
- ⚠️ Integration tests require GOOGLE_API_KEY

**Not Yet Working**:
- ❌ Only Google Gemini provider (v0.1 constraint)
- ❌ Streaming not yet implemented
- ❌ Function calling uses tool binding (native in v0.2+)

---

## 💻 Public API

### Main LLM Functions

```python
from configurable_agents.llm import (
    create_llm,              # Create LLM from config
    call_llm_structured,     # Call LLM with structured output
    merge_llm_config,        # Merge node and global configs
)

# Create LLM
config = LLMConfig(provider="google", model="gemini-pro", temperature=0.7)
llm = create_llm(config)

# Call with structured output
class Article(BaseModel):
    title: str
    content: str

result = call_llm_structured(llm, "Write an article about AI", Article)
print(result.title)
```

### Error Handling

```python
from configurable_agents.llm import (
    LLMConfigError,          # Configuration error exception
    LLMProviderError,        # Provider not supported exception
    LLMAPIError,             # API call failure exception
)

# Missing API key
try:
    llm = create_llm(LLMConfig(provider="google"))
except LLMConfigError as e:
    # LLM configuration failed for provider 'google':
    # GOOGLE_API_KEY environment variable not set
    # Get your API key from: https://ai.google.dev/
    print(e)

# Unsupported provider
try:
    llm = create_llm(LLMConfig(provider="openai"))
except LLMProviderError as e:
    # LLM provider 'openai' is not supported.
    # Supported providers: google
    # Note: v0.1 only supports Google Gemini.
    # Additional providers coming in v0.2+ (8-12 weeks).
    print(e)
```

### Complete Public API

```python
# From configurable_agents.llm

# Core functions
from configurable_agents.llm import (
    create_llm,              # Create LLM from config
    call_llm_structured,     # Call LLM with structured output
    merge_llm_config,        # Merge node and global configs
)

# Exceptions
from configurable_agents.llm import (
    LLMConfigError,          # Configuration error
    LLMProviderError,        # Provider not supported
    LLMAPIError,             # API call failure
)

# Usage
config = LLMConfig(model="gemini-2.5-flash-lite", temperature=0.7)
llm = create_llm(config)

class Output(BaseModel):
    result: str

response = call_llm_structured(llm, "Hello", Output)
```

---

## 📚 Dependencies Used

### Existing Dependencies

- `langchain-google-genai` - ChatGoogleGenerativeAI wrapper
- `pydantic >= 2.0` - Schema validation for structured outputs
- `langchain` - BaseChatModel interface

**Status**: Already declared in `pyproject.toml` from T-001

---

## 💡 Design Decisions

### Why Factory Pattern?

- LLMs created via factory functions for flexibility
- Easy to add new providers in future
- Centralizes provider selection logic
- Enables consistent error handling

### Why Config Merging?

- Node-level settings override global (explicit precedence)
- Allows per-node customization
- Global config provides defaults
- Clear and predictable behavior

### Why Fail Loudly?

- Clear errors with actionable messages
- Include API key setup instructions
- List supported providers
- Explain version availability

### Why Retry Logic?

- Automatic retry on validation errors
- Exponential backoff on rate limits
- Clarified prompts on validation failures
- Improves robustness in production

### Why Structured Outputs?

- Pydantic schema binding for type enforcement
- LLMs return validated data structures
- Prevents parsing errors
- Type-safe workflow execution

### Why Provider Abstraction?

- Easy to add providers in future versions
- Consistent interface across providers
- Isolates provider-specific logic
- Future-proof architecture

### Why Environment-Based Config?

- API keys from environment variables (secure)
- Follows 12-factor app principles
- No secrets in code or configs
- Easy to configure per environment

---

## 🧪 Tests Created

**Files**:
- `tests/llm/test_provider.py` (19 tests)
- `tests/llm/test_google.py` (13 unit + 2 integration tests)

### Test Categories (32 tests total)

#### Provider Tests (19 tests)

1. **LLM Creation** (5 tests)
   - Create LLM with valid config
   - Default provider is "google"
   - Default model is "gemini-2.5-flash-lite"
   - Missing API key raises LLMConfigError
   - Unsupported provider raises LLMProviderError

2. **Config Merging** (6 tests)
   - Node config overrides global config
   - Global config used when node config is None
   - Both configs None uses defaults
   - Partial node config merges with global
   - Node temperature overrides global
   - Node model overrides global model

3. **Structured Output Calling** (5 tests)
   - Call LLM with structured output
   - Pydantic validation enforced
   - Returns instance of output model
   - Handles validation errors with retry
   - Max retries respected

4. **Error Handling** (3 tests)
   - LLMConfigError includes helpful message
   - LLMProviderError lists supported providers
   - LLMAPIError wraps API failures

#### Google Tests (13 unit + 2 integration)

1. **LLM Creation** (4 tests)
   - Create Google LLM with API key
   - Instance is ChatGoogleGenerativeAI
   - Default model applied
   - Custom model used

2. **API Key Validation** (4 tests)
   - Missing API key raises error
   - Empty API key raises error
   - Error includes setup instructions
   - Error includes API key URL

3. **Configuration** (3 tests)
   - Temperature configured correctly
   - Max tokens configured
   - Multiple models supported

4. **Error Messages** (2 tests)
   - Error includes environment variable name
   - Error helpful for new users

5. **Integration Tests** (2 tests - marked)
   - Real API call with valid key
   - Structured output returns valid data

---

## 🎨 LLM Provider Features

### Create LLM from Config

```python
config = LLMConfig(
    provider="google",
    model="gemini-2.5-flash-lite",
    temperature=0.7,
    max_tokens=1000
)
llm = create_llm(config)
```

- ✅ Returns BaseChatModel instance
- ✅ Validates provider (only "google" in v0.1)
- ✅ Validates API key from environment
- ✅ Applies model and temperature settings
- ✅ Raises helpful errors on misconfiguration

### Structured Output Calling

```python
class Analysis(BaseModel):
    summary: str
    score: int

result = call_llm_structured(
    llm=llm,
    prompt="Analyze this text: {text}",
    output_model=Analysis,
    max_retries=3
)
```

- ✅ Binds Pydantic schema to LLM
- ✅ Enforces type validation
- ✅ Automatic retry on validation errors
- ✅ Clarifies prompt on failures
- ✅ Returns validated Pydantic instance

### Config Merging

```python
global_config = LLMConfig(temperature=0.5)
node_config = LLMConfig(temperature=0.9)

merged = merge_llm_config(node_config, global_config)
# merged.temperature == 0.9 (node overrides global)
```

- ✅ Node-level config overrides global
- ✅ Partial overrides supported
- ✅ None configs handled gracefully
- ✅ Explicit precedence rules

### Tool Binding

```python
from langchain_core.tools import BaseTool

llm_with_tools = llm.bind_tools([search_tool, calculator_tool])
```

- ✅ Bind tools to LLM before calling
- ✅ Compatible with LangChain tools
- ✅ Enables function calling patterns

---

## 🔍 Google Gemini Integration

### Features

- ✅ ChatGoogleGenerativeAI wrapper
- ✅ Reads GOOGLE_API_KEY from environment
- ✅ Supports multiple models (gemini-2.5-flash-lite, gemini-1.5-pro, gemini-pro)
- ✅ Clear error messages with API key setup instructions
- ✅ Configuration validation
- ✅ Integration tests (marked as slow/integration)

### Supported Models

- `gemini-2.5-flash-lite` (default) - Fast, efficient
- `gemini-1.5-pro` - More capable
- `gemini-pro` - Original production model
- `gemini-pro-vision` - Multimodal support

### Usage

```python
import os
os.environ["GOOGLE_API_KEY"] = "your-key-here"

from configurable_agents.llm import create_llm
from configurable_agents.config import LLMConfig

config = LLMConfig(model="gemini-1.5-pro", temperature=0.7)
llm = create_llm(config)
```

### Error Messages

```
# Missing API key
LLMConfigError: LLM configuration failed for provider 'google':
GOOGLE_API_KEY environment variable not set

Suggestion: Set the environment variable: GOOGLE_API_KEY
Get your API key from: https://ai.google.dev/
Example: export GOOGLE_API_KEY=your-api-key-here
```

---

## 🔄 Retry Logic

### Validation Error Retry

```python
# Automatic retry on Pydantic ValidationError
result = call_llm_structured(llm, prompt, OutputModel, max_retries=3)

# Retries with clarified prompt:
# "Previous response had validation errors.
#  Please ensure output matches exact schema..."
```

### Rate Limit Retry

```python
# Exponential backoff on rate limits
# Retry delays: 1s, 2s, 4s, 8s, etc.
# Handled automatically by LangChain
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-009 marked DONE, progress updated to 10/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)
- ✅ .env.example (GOOGLE_API_KEY already present from T-001)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-009: LLM provider - Google Gemini integration

- Implemented LLM provider factory for creating LLM instances
  - create_llm(config) - Create LLM from config
  - call_llm_structured(llm, prompt, OutputModel) - Structured outputs
  - merge_llm_config(node, global) - Config merging
  - Fail loudly if provider not supported or API key missing

- Implemented Google Gemini LLM provider
  - ChatGoogleGenerativeAI integration
  - Reads GOOGLE_API_KEY from environment
  - Supports gemini-2.5-flash-lite, gemini-1.5-pro, gemini-pro models
  - Temperature and max_tokens configuration
  - Clear error messages with setup instructions

- Structured output calling with retry logic
  - Pydantic schema binding for type enforcement
  - Automatic retry on ValidationError (up to max_retries)
  - Exponential backoff on rate limits
  - Clarified prompts on validation failures
  - Tool binding support

- Configuration merging
  - Node-level LLM config overrides global config
  - Explicit precedence rules
  - Handles None configs gracefully

- Created 32 comprehensive tests
  - 19 provider tests (factory, merging, structured calls, retries)
  - 13 Google tests (creation, validation, configuration)
  - 2 integration tests (marked with @pytest.mark.integration)

Verification:
  pytest -v -m 'not integration'
  Expected: 300 passed (32 llm + 268 existing)

Progress: 10/20 tasks (50%) - Phase 2 (Core Execution) 2/6 complete
Next: T-010 (Prompt Template Resolver)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-009 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - LLM integration requirements
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - LLM component architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Multi-provider roadmap

---

## 🚀 Next Steps for Users

### Setup Google API Key

```bash
# Get API key from https://ai.google.dev/
export GOOGLE_API_KEY="your-api-key-here"

# Or add to .env file
echo "GOOGLE_API_KEY=your-api-key-here" >> .env
```

### Use in Workflow Config

```yaml
config:
  llm:
    provider: google
    model: gemini-2.5-flash-lite
    temperature: 0.7
    max_tokens: 2000

nodes:
  - id: generate
    llm:  # Node-level override
      temperature: 0.9
    prompt: "Write about: {topic}"
```

### Test LLM Integration

```python
from configurable_agents.llm import create_llm, call_llm_structured
from configurable_agents.config import LLMConfig
from pydantic import BaseModel

config = LLMConfig(temperature=0.7)
llm = create_llm(config)

class Summary(BaseModel):
    text: str

result = call_llm_structured(llm, "Summarize AI in one sentence", Summary)
print(result.text)
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 2/6 complete (33%)**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

---

*Implementation completed: 2026-01-25*
*Next task: T-010 (Prompt Template Resolver)*
