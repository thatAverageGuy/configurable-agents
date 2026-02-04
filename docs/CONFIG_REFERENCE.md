# Configuration Reference

**User-friendly guide to writing workflow configs**

This guide explains how to write configuration files for Configurable Agents. For complete technical specification, see [SPEC.md](SPEC.md).

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Structure](#basic-structure)
3. [State Definition](#state-definition)
4. [Nodes](#nodes)
5. [Edges (Flow Control)](#edges-flow-control)
6. [Global Configuration](#global-configuration)
7. [Complete Example](#complete-example)
8. [Python API](#python-api)

---

## Overview

A workflow config has 4 main sections:

```yaml
schema_version: "1.0"   # Always "1.0" for now

flow:                   # Workflow metadata (name, description)
  name: my_workflow

state:                  # State fields (inputs and outputs)
  fields: {...}

nodes:                  # LLM tasks (what to do)
  - id: step1
    prompt: "..."

edges:                  # Flow control (order of execution)
  - from: START
    to: step1
```

---

## Basic Structure

### Schema Version

Always use `"1.0"`:

```yaml
schema_version: "1.0"
```

This ensures forward compatibility as new versions are released.

### Flow Metadata

Give your workflow a name and description:

```yaml
flow:
  name: article_writer
  description: "Research and write articles"
  version: "1.0.0"  # Optional
```

**Fields:**
- `name` (required): Unique identifier
- `description` (optional): What the workflow does
- `version` (optional): Workflow version (use semantic versioning)

---

## State Definition

The **state** is your workflow's memory. It holds all data fields (inputs, outputs, intermediate values).

### Basic Types

```yaml
state:
  fields:
    # String
    topic:
      type: str
      required: true
      description: "Topic to research"

    # Integer
    word_count:
      type: int
      default: 0

    # Boolean
    is_complete:
      type: bool
      default: false

    # Float
    confidence_score:
      type: float
      default: 0.0
```

**Type options:**
- `str` - Text
- `int` - Whole numbers
- `float` - Decimal numbers
- `bool` - True/False

### Collection Types

```yaml
state:
  fields:
    # List of strings
    keywords:
      type: list[str]
      default: []

    # List of integers
    scores:
      type: list[int]
      default: []

    # Dictionary (string keys, int values)
    word_frequencies:
      type: dict[str, int]
      default: {}
```

### Nested Objects

For complex data structures:

```yaml
state:
  fields:
    profile:
      type: object
      schema:
        name:
          type: str
          required: true
        age:
          type: int
          required: true
        interests:
          type: list[str]
          default: []
```

**Access nested fields** in prompts: `{state.profile.name}`

### Field Properties

| Property | Description | Example |
|----------|-------------|---------|
| `type` | Data type (required) | `str`, `int`, `list[str]` |
| `required` | Must be provided as input | `required: true` |
| `default` | Default value if not provided | `default: ""` |
| `description` | Human-readable description | `description: "User's name"` |

**Rules:**
- Can't have both `required: true` and `default`
- Required fields must be provided when running the workflow

---

## Nodes

**Nodes** are LLM tasks. Each node:
1. Receives the current state
2. Calls an LLM with a prompt
3. Optionally uses tools (web search, APIs)
4. Updates state with outputs

### Basic Node

```yaml
nodes:
  - id: greet
    prompt: "Generate a greeting for {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str
```

**Required fields:**
- `id` - Unique node identifier
- `prompt` - Instruction for the LLM (can reference state)
- `outputs` - Which state fields to update
- `output_schema` - Expected output structure

### Using Variables in Prompts

Reference state fields with `{state.field}`:

```yaml
prompt: "Write an article about {state.topic} with {state.word_count} words"
```

**Nested state:**
```yaml
prompt: "Create content for {state.profile.name} who likes {state.profile.interests}"
```

### Output Schema

**Simple output** (single value):
```yaml
output_schema:
  type: str  # LLM returns a string
```

**Object output** (multiple fields):
```yaml
output_schema:
  type: object
  fields:
    - name: article
      type: str
      description: "The written article"
    - name: word_count
      type: int
      description: "Number of words"
```

The LLM will return structured data matching this schema.

### Using Tools

Add tools for web search, APIs, etc:

```yaml
nodes:
  - id: research
    prompt: "Research {state.topic} using web search"
    tools: [serper_search]  # Web search tool
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str
```

**Available tools (v0.1):**
- `serper_search` - Web search (requires `SERPER_API_KEY`)

### Input Mappings (Advanced)

Override state values for specific nodes:

```yaml
nodes:
  - id: analyze
    inputs:
      query: "{state.topic}"  # Rename 'topic' to 'query' for this node
    prompt: "Analyze {query}"  # Use 'query' instead of 'state.topic'
```

### Node-Level LLM Config (Advanced)

Override global LLM settings per node:

```yaml
nodes:
  - id: precise_task
    prompt: "..."
    llm:
      temperature: 0.0  # Lower temp for this node
      model: "gemini-1.5-pro"
```

---

## Edges (Flow Control)

**Edges** define the execution order. In v0.1, only **linear flows** are supported (straight line, no branching).

### Basic Flow

```yaml
edges:
  - from: START
    to: step1
  - from: step1
    to: step2
  - from: step2
    to: END
```

This creates: `START → step1 → step2 → END`

**Special nodes:**
- `START` - Entry point (always first)
- `END` - Exit point (always last)

### Rules (v0.1)

- Must start with `START`
- Must end with `END`
- No branching (if/else)
- No loops
- Each node can only have one incoming and one outgoing edge

**Coming in v0.2:** Conditional routing, loops, retries

---

## Global Configuration

Optional settings that apply to all nodes.

### LLM Settings

```yaml
config:
  llm:
    provider: google
    model: "gemini-1.5-flash"
    temperature: 0.7
    max_tokens: 2048
```

**Fields:**
- `provider` - LLM provider (only `google` in v0.1)
- `model` - Model name (default: `gemini-1.5-flash`)
- `temperature` - Creativity (0.0-1.0, default: 0.7)
- `max_tokens` - Max output length (default: 2048)

### Execution Settings

```yaml
config:
  execution:
    timeout_seconds: 60
    max_retries: 3
```

**Fields:**
- `timeout_seconds` - Max time per node (default: 60)
- `max_retries` - Retry count on failures (default: 3)

### MLFlow 3.9 Observability (v0.1+)

Track workflow costs, tokens, and performance with MLFlow 3.9 automatic tracing:

```yaml
config:
  observability:
    mlflow:
      # Core settings
      enabled: true                          # Enable tracking (default: false)
      tracking_uri: "sqlite:///mlflow.db"    # Storage backend (default)
      experiment_name: "my_workflows"        # Group related runs

      # MLflow 3.9 features
      async_logging: true                    # Async trace logging (default: true)

      # Artifact control
      log_artifacts: true                    # Save artifacts (default: true)
      artifact_level: "standard"             # minimal | standard | full

      # Optional
      run_name: null                         # Custom run naming (optional)
```

**enabled** (bool, default: `false`):
- Master switch for MLFlow tracking
- When disabled, zero performance overhead
- Activates MLflow 3.9 automatic tracing (`mlflow.langchain.autolog()`)

**tracking_uri** (str, default: `"sqlite:///mlflow.db"`):
- Where to store tracking data
- **Recommended**: `sqlite:///mlflow.db` (default in MLflow 3.9)
- **Deprecated**: `file://./mlruns` (still works, but shows warning)
- **Remote**: `postgresql://...`, `s3://...`, `databricks://...`

**experiment_name** (str, default: `"configurable_agents"`):
- Logical grouping for related workflow runs
- Use meaningful names: `"production"`, `"testing"`, `"article_workflows"`

**async_logging** (bool, default: `true`):
- **NEW in MLflow 3.9**: Enable async trace logging
- Zero-latency production mode (non-blocking I/O)
- Traces appear in UI with < 1s delay

**log_artifacts** (bool, default: `true`):
- Save artifacts (cost summaries, traces)
- Disable to reduce storage usage

**artifact_level** (str, default: `"standard"`):
- `"minimal"`: Only cost summary
- `"standard"`: Cost summary + basic traces
- `"full"`: Everything (including prompts/responses)

**run_name** (str, optional):
- Template for individual run names
- If not specified, MLFlow generates timestamp-based names

**What gets tracked automatically:**
- ✅ Workflow execution traces (root span)
- ✅ Node execution spans (child spans)
- ✅ Token usage per node (automatic from LLM responses)
- ✅ Model names and parameters
- ✅ Cost breakdown (computed from token usage)
- ✅ Execution timestamps and durations

**View traces:**
```bash
# After running workflows with observability enabled
mlflow ui --backend-store-uri sqlite:///mlflow.db

# Open http://localhost:5000 in your browser
```

**Cost reporting:**
```bash
# View costs for last 7 days
configurable-agents report costs --period last_7_days --breakdown

# Export to CSV
configurable-agents report costs --output report.csv --format csv
```

**Migration from pre-3.9:**
See [MLFLOW_39_USER_MIGRATION_GUIDE.md](MLFLOW_39_USER_MIGRATION_GUIDE.md) for migration instructions.

For comprehensive documentation, see [OBSERVABILITY.md](OBSERVABILITY.md).

### Logging

```yaml
config:
  observability:
    logging:
      level: INFO
      format: json
```

**Levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`

---

## Complete Example

Here's a full workflow that researches a topic and writes an article:

```yaml
schema_version: "1.0"

flow:
  name: article_writer
  description: "Research and write articles"
  version: "1.0.0"

state:
  fields:
    topic:
      type: str
      required: true
      description: "Topic to write about"

    research:
      type: str
      default: ""
      description: "Research findings"

    article:
      type: str
      default: ""
      description: "Final article"

    word_count:
      type: int
      default: 0
      description: "Article word count"

nodes:
  - id: research
    prompt: |
      Research the topic: {state.topic}
      Find key facts, recent developments, and interesting insights.
    tools: [serper_search]
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str
          description: "Research findings and sources"

  - id: write
    prompt: |
      Write a comprehensive article about {state.topic}.

      Use this research:
      {state.research}

      Write 500-800 words with clear structure.
    outputs: [article, word_count]
    output_schema:
      type: object
      fields:
        - name: article
          type: str
          description: "The complete article"
        - name: word_count
          type: int
          description: "Number of words in article"

edges:
  - from: START
    to: research
  - from: research
    to: write
  - from: write
    to: END

config:
  llm:
    model: "gemini-1.5-flash"
    temperature: 0.7

  execution:
    timeout_seconds: 120
    max_retries: 3

  observability:
    logging:
      level: INFO
```

**Run it:**
```bash
configurable-agents run article_writer.yaml --input topic="AI Safety"
```

---

## Python API

Use workflows programmatically:

```python
from configurable_agents.runtime import run_workflow, validate_workflow
from configurable_agents.config import parse_config_file, WorkflowConfig

# Run a workflow
result = run_workflow("workflow.yaml", {"topic": "AI Safety"})
print(result["article"])

# Validate without running
validate_workflow("workflow.yaml")

# Load config manually
config_dict = parse_config_file("workflow.yaml")
config = WorkflowConfig(**config_dict)

# Run from config object
from configurable_agents.runtime import run_workflow_from_config
result = run_workflow_from_config(config, {"topic": "AI"})

# Enable verbose logging
result = run_workflow("workflow.yaml", {"topic": "AI"}, verbose=True)
```

### Exception Handling

```python
from configurable_agents.runtime import (
    ExecutionError,
    ConfigLoadError,
    ConfigValidationError,
    StateInitializationError,
    GraphBuildError,
    WorkflowExecutionError,
)

try:
    result = run_workflow("workflow.yaml", {"topic": "AI"})
except ConfigLoadError as e:
    print(f"Config file error: {e}")
except ConfigValidationError as e:
    print(f"Invalid config: {e}")
except StateInitializationError as e:
    print(f"Missing required input: {e}")
except WorkflowExecutionError as e:
    print(f"Execution failed: {e}")
```

---

## Next Steps

- **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step tutorial
- **[examples/](../examples/)** - Working examples to learn from
- **[SPEC.md](SPEC.md)** - Complete technical specification
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues

---

## Version Availability

| Feature | v0.1 | v0.2 | v0.3 |
|---------|------|------|------|
| Linear flows | ✅ | ✅ | ✅ |
| Structured outputs | ✅ | ✅ | ✅ |
| Google Gemini | ✅ | ✅ | ✅ |
| Web search tool | ✅ | ✅ | ✅ |
| Conditional routing | ❌ | ✅ | ✅ |
| Loops | ❌ | ✅ | ✅ |
| Multi-LLM support | ❌ | ✅ | ✅ |
| DSPy optimization | ❌ | ❌ | ✅ |
| Parallel execution | ❌ | ❌ | ✅ |

See [TASKS.md (for detailed progress) or README.md (for version overview)](TASKS.md (for detailed progress) or README.md (for version overview)) for timeline and details.

---

**Questions?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue!
