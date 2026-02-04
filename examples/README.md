# Workflow Examples

Example workflow configurations for Configurable Agents.

## Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up API key
export GOOGLE_API_KEY="your-key-here"  # Unix/Linux/macOS
# or
set GOOGLE_API_KEY=your-key-here  # Windows
```

## Quick Start

### Using the CLI (Command-Line Interface)

**Run a workflow:**
```bash
# With inputs
configurable-agents run simple_workflow.yaml --input name="Alice"

# Multiple inputs
configurable-agents run workflow.yaml --input topic="AI" --input count=5

# With verbose logging
configurable-agents run workflow.yaml --input name="Bob" --verbose
```

**Validate a workflow:**
```bash
# Check config without executing
configurable-agents validate simple_workflow.yaml
```

**Input formats:**
```bash
# Strings (with or without quotes)
--input topic="AI Safety"
--input name=Alice

# Numbers (parsed automatically)
--input count=5
--input temperature=0.7

# Booleans
--input enabled=true
--input debug=false

# Lists (JSON format)
--input 'tags=["ai", "safety"]'

# Objects (JSON format)
--input 'metadata={"author": "Alice", "version": 1}'
```

### Using the Runtime Executor (Python)

```python
from configurable_agents.runtime import run_workflow

# Execute workflow from file
result = run_workflow("simple_workflow.yaml", {"name": "Alice"})

print(result["greeting"])
# Output: "Hello Alice! How are you doing today?"
```

### Validating Workflows

```python
from configurable_agents.runtime import validate_workflow

# Validate without executing
try:
    validate_workflow("simple_workflow.yaml")
    print("✅ Config is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")
```

### Using Pre-loaded Configs

```python
from configurable_agents.config import parse_config_file, WorkflowConfig
from configurable_agents.runtime import run_workflow_from_config

# Load and parse config
config_dict = parse_config_file("simple_workflow.yaml")
config = WorkflowConfig(**config_dict)

# Execute from config object
result = run_workflow_from_config(config, {"name": "Bob"})
```

## Available Examples

### 1. echo.yaml ⭐ (Simplest)

**Complexity**: Minimal
**What it demonstrates**: The absolute basics

The simplest possible workflow - takes a message and echoes it back. Perfect for testing your installation and understanding the basic config structure.

**Features:**
- Minimal configuration (1 node, 1 input, 1 output)
- No tools required
- Pure LLM text processing

**Usage:**
```bash
configurable-agents run echo.yaml --input message="Hello, World!"
```

**Python:**
```python
result = run_workflow("examples/echo.yaml", {"message": "Hello!"})
print(result["result"])
```

**Learn more**: See [echo_README.md](echo_README.md)

---

### 2. simple_workflow.yaml ⭐⭐ (Basic)

**Complexity**: Basic
**What it demonstrates**: Simple state and personalization

A basic greeting workflow with personalized output.

**Features:**
- Single node execution
- Prompt template with variable substitution
- Structured output
- State management

**Usage:**
```bash
configurable-agents run simple_workflow.yaml --input name="Alice"
```

**Python:**
```python
result = run_workflow("examples/simple_workflow.yaml", {"name": "Alice"})
print(result["greeting"])
```

---

### 3. article_writer.yaml ⭐⭐⭐ (Intermediate)

**Complexity**: Intermediate
**What it demonstrates**: Multi-step workflows with tools

A production-like workflow that researches a topic using web search, then writes a comprehensive article.

**Features:**
- Multi-node sequential workflow (research → write)
- Tool integration (serper_search for web search)
- State flowing between nodes
- Multiple output fields from single node
- Global configuration (LLM settings, timeouts)

**Prerequisites:**
```bash
export GOOGLE_API_KEY="your-google-key"
export SERPER_API_KEY="your-serper-key"
# Get Serper key: https://serper.dev (free tier: 2,500 searches)
```

**Usage:**
```bash
configurable-agents run article_writer.yaml --input topic="AI Safety"
```

**Python:**
```python
result = run_workflow("examples/article_writer.yaml", {"topic": "AI Safety"})
print(result["article"])
print(f"Word count: {result['word_count']}")
```

**Learn more**: See [article_writer_README.md](article_writer_README.md)

---

### 4. nested_state.yaml ⭐⭐ (Intermediate)

**Complexity**: Intermediate
**What it demonstrates**: Nested object types and complex state

Generates a user profile with nested structure (bio, traits, topics, score).

**Features:**
- Object types with nested schemas
- List types (arrays of strings)
- Complex state with multiple levels
- Structured nested output generation

**Usage:**
```bash
configurable-agents run nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics", "philosophy"]'
```

**Python:**
```python
result = run_workflow(
    "examples/nested_state.yaml",
    {
        "name": "Alice",
        "interests": ["AI", "robotics", "philosophy"]
    }
)
profile = result["profile"]
print(f"Bio: {profile['bio']}")
print(f"Traits: {profile['personality_traits']}")
```

**Learn more**: See [nested_state_README.md](nested_state_README.md)

---

### 5. type_enforcement.yaml ⭐⭐⭐ (Advanced)

**Complexity**: Advanced
**What it demonstrates**: Complete type system and enforcement

A comprehensive demonstration of type enforcement across all supported types: int, bool, float, list, dict, and nested objects.

**Features:**
- All type system types demonstrated
- Multiple typed outputs from single node
- Type validation at multiple levels
- Automatic retry on type mismatches
- Shows how structured outputs work

**Usage:**
```bash
configurable-agents run type_enforcement.yaml --input topic="Artificial Intelligence"
```

**Python:**
```python
result = run_workflow("examples/type_enforcement.yaml", {"topic": "AI"})
print(f"Score: {result['score']} (type: {type(result['score']).__name__})")
print(f"Trending: {result['is_trending']}")
print(f"Keywords: {result['keywords']}")
print(f"Analysis: {result['analysis']}")
```

**Learn more**: See [type_enforcement_README.md](type_enforcement_README.md)

---

## Example Summary Table

| Example | Complexity | Nodes | Tools | Code | MLFlow | Key Learning |
|---------|------------|-------|-------|------|--------|--------------|
| echo.yaml | ⭐ Minimal | 1 | ❌ | ❌ | ❌ | Basic structure |
| simple_workflow.yaml | ⭐⭐ Basic | 1 | ❌ | ❌ | ❌ | State & prompts |
| article_writer.yaml | ⭐⭐⭐ Intermediate | 2 | ✅ | ❌ | Optional | Multi-step + tools |
| nested_state.yaml | ⭐⭐ Intermediate | 1 | ❌ | ❌ | ❌ | Nested objects |
| type_enforcement.yaml | ⭐⭐⭐ Advanced | 1 | ❌ | ❌ | ❌ | Type system |
| mlflow_optimization.yaml | ⭐⭐⭐ Advanced | 1 | ✅ | ❌ | ✅ | A/B testing & optimization |
| sandbox_example.yaml | ⭐⭐⭐ Advanced | 1 | ❌ | ✅ | Optional | Code execution sandbox |
| webhook_integration/ | ⭐⭐⭐⭐ Production | 2 | ✅ | ❌ | Optional | Event-driven automation |
| multi_agent_collaboration/ | ⭐⭐⭐⭐⭐ Advanced | 3+ | ✅ | ❌ | ✅ | Orchestrated multi-agent |
| performance_tuning/ | ⭐⭐⭐⭐ Production | 2 | ✅ | ❌ | ✅ | Performance optimization |

## Recommended Learning Path

### Level 1: Getting Started (⭐)
1. **[echo.yaml](echo.yaml)** - Verify installation works (5 min)
2. **[simple_workflow.yaml](simple_workflow.yaml)** - Understand state and prompts (10 min)

### Level 2: Intermediate (⭐⭐)
3. **[article_writer.yaml](article_writer/)** - Multi-step with tools (20 min)
4. **[nested_state.yaml](nested_state/)** - Complex data structures (15 min)

### Level 3: Advanced (⭐⭐⭐)
5. **[type_enforcement.yaml](type_enforcement/)** - Type system mastery (20 min)
6. **[tools_example.yaml](tools_example/)** - Tool integrations (15 min)
7. **[mlflow_optimization.yaml](mlflow_optimization/)** - A/B testing and optimization (30 min)

### Level 4: Production-Ready (⭐⭐⭐⭐)
8. **[sandbox_example.yaml](sandbox_example/)** - Code execution sandboxing (20 min)
9. **[webhook_integration/](webhook_integration/)** - Event-driven automation (30 min)
10. **[performance_tuning/](performance_tuning/)** - Production optimization (45 min)

### Level 5: Real-World Integrations (⭐⭐⭐⭐⭐)
11. **[multi_agent_collaboration/](multi_agent_collaboration/)** - Orchestrated multi-agent systems (60 min)

## Advanced Examples

### 6. webhook_integration/ ⭐⭐⭐⭐ (Production)

**Complexity**: Production
**What it demonstrates**: Event-driven automation with external webhooks

Trigger workflows from external services (GitHub, Stripe, custom systems) via webhooks.

**Features:**
- Webhook triggering with generic endpoint
- Event processing and logging
- Notification formatting
- MLFlow tracking for webhook events
- Production deployment with HMAC signature verification

**Prerequisites:**
- Dashboard server running
- Ngrok or public IP for testing

**Usage:**
```bash
# Start dashboard
configurable-agents dashboard --port 8000

# Send webhook
curl -X POST http://localhost:8000/webhooks/generic \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "slack_notification", "inputs": {...}}'
```

**Learn more**: [webhook_integration/README.md](webhook_integration/README.md)

---

### 7. multi_agent_collaboration/ ⭐⭐⭐⭐⭐ (Advanced)

**Complexity**: Advanced
**What it demonstrates**: Orchestrated multi-agent systems

Orchestrate multiple specialist agents working in parallel to accomplish complex tasks.

**Features:**
- Agent registration and discovery
- Metadata-based agent filtering
- Parallel agent execution
- Orchestrator pattern
- Multi-agent coordination

**Prerequisites:**
- Agent registry running
- Multiple agent instances registered

**Usage:**
```bash
# Start registry
configurable-agents registry --port 8000

# Register specialist agents
configurable-agents agent start --name researcher --port 8001
configurable-agents agent start --name analyst --port 8002

# Run orchestrated workflow
configurable-agents run multi_agent_collaboration.yaml \
  --orchestrator-url http://localhost:8000
```

**Learn more**: [multi_agent_collaboration/README.md](multi_agent_collaboration/README.md)

---

### 8. performance_tuning/ ⭐⭐⭐⭐ (Production)

**Complexity**: Production
**What it demonstrates**: Performance optimization techniques

Demonstrates various performance optimization techniques to reduce cost and latency.

**Features:**
- Model selection (cheaper vs expensive models)
- Response caching (cache configuration)
- A/B testing (prompt optimization)
- Quality gates (cost/latency thresholds)
- Performance benchmarking

**Prerequisites:**
- MLFlow setup
- Basic performance concepts

**Usage:**
```bash
# Run benchmark
python benchmark.py

# Run optimized workflow
configurable-agents run performance_tuning.yaml \
  --query "performance optimization"

# View A/B test results
configurable-agents optimization evaluate \
  --workflow performance_tuning.yaml \
  --experiment-name "performance_optimization"
```

**Expected Results:**
- 60-80% cost reduction vs baseline
- 50-60% latency reduction vs baseline

**Learn more**: [performance_tuning/README.md](performance_tuning/README.md)

---

## Error Handling

The executor provides comprehensive error handling:

```python
from configurable_agents.runtime import (
    run_workflow,
    ConfigLoadError,       # Config file not found or invalid syntax
    ConfigValidationError, # Config validation failed
    StateInitializationError, # Invalid input values
    GraphBuildError,       # Graph construction failed
    WorkflowExecutionError, # Node execution failed
)

try:
    result = run_workflow("workflow.yaml", {"name": "Alice"})
except ConfigLoadError as e:
    print(f"Failed to load config: {e}")
except ConfigValidationError as e:
    print(f"Invalid config: {e}")
except StateInitializationError as e:
    print(f"Invalid inputs: {e}")
except WorkflowExecutionError as e:
    print(f"Execution failed: {e}")
```

## Verbose Logging

Enable detailed logging for debugging:

**CLI:**
```bash
configurable-agents run workflow.yaml --input name="Alice" --verbose
```

**Python:**
```python
result = run_workflow("workflow.yaml", {"name": "Alice"}, verbose=True)
```

## Notes

- All examples require Google Gemini API key (v0.1 limitation)
- Multi-LLM support coming in v0.2+
- Conditional routing coming in v0.2+
- See [docs/SPEC.md](../docs/SPEC.md) for complete config schema reference

## Next Steps

1. Explore the [full spec](../docs/SPEC.md)
2. Read the [architecture docs](../docs/ARCHITECTURE.md)
3. Check the [roadmap](../docs/PROJECT_VISION.md)

---

**Note**: These examples are minimal demonstrations. Production workflows will have:
- Multiple nodes in sequence
- Tool integration (web search, APIs)
- Complex state management
- Error handling and retries
