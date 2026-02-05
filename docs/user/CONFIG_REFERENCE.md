# Configuration Reference

**User-friendly guide to writing workflow configs for v1.0**

This guide explains how to write configuration files for Configurable Agents v1.0. For complete technical specification, see [SPEC.md](SPEC.md).

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Structure](#basic-structure)
3. [State Definition](#state-definition)
4. [Nodes](#nodes)
5. [Edges (Flow Control)](#edges-flow-control)
6. [Global Configuration](#global-configuration)
7. [v1.0 Feature Examples](#v10-feature-examples)
8. [Complete Example](#complete-example)
9. [Python API](#python-api)

---

## Overview

A workflow config has 4 main sections:

```yaml
schema_version: "1.0"   # Always "1.0" for v1.0

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

Always use `"1.0"` for v1.0:

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
3. Optionally uses tools (web search, APIs, code execution)
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

### Multi-LLM Provider Configuration (v1.0)

Configure different LLM providers per node:

```yaml
nodes:
  - id: research
    llm:
      provider: openai
      model: "gpt-4"
      temperature: 0.7
      max_tokens: 2000
    prompt: "Research {state.topic}"
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str

  - id: summarize
    llm:
      provider: anthropic
      model: "claude-3-sonnet-20240229"
      temperature: 0.5
    prompt: "Summarize: {state.research}"
    outputs: [summary]
    output_schema:
      type: object
      fields:
        - name: summary
          type: str

  - id: local_check
    llm:
      provider: ollama
      model: "ollama_chat/llama2"  # ollama_chat prefix for Ollama
      temperature: 0.0
    prompt: "Verify: {state.summary}"
    outputs: [verification]
    output_schema:
      type: object
      fields:
        - name: verification
          type: str
```

**Supported providers in v1.0:**
- `google` - Google Gemini (default)
- `openai` - OpenAI (GPT-3.5, GPT-4)
- `anthropic` - Anthropic (Claude 3)
- `ollama` - Local models via Ollama

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

### Using Tools (v1.0)

Add tools for web search, file operations, code execution, etc:

```yaml
nodes:
  - id: research
    tools: [serper_search]  # Web search tool
    prompt: "Research {state.topic} using web search"
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str
```

**Available tools in v1.0:**

#### Search Tools
- `serper_search` - Web search (requires `SERPER_API_KEY`)

#### File Operations
- `read_file` - Read from local files
- `write_file` - Write to local files
- `list_directory` - List directory contents

#### Code Execution
- `python_repl` - Execute Python code
- `shell` - Run shell commands

#### Data Processing
- `sql_query` - Execute SQL queries (SELECT only)
- `json_read` - Parse JSON data
- `json_write` - Format JSON data

#### API Integration
- `http_get` - Make HTTP GET requests
- `http_post` - Make HTTP POST requests

**Tool configuration:**
```yaml
nodes:
  - id: file_processor
    tools:
      - read_file
      - write_file
    tool_config:
      allowed_paths:
        - ./data
        - ./output
    prompt: "Process data files"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
```

### Sandbox Code Execution (v1.0)

Run agent-generated Python code in a sandboxed environment:

```yaml
nodes:
  - id: execute_code
    sandbox:
      enabled: true
      timeout_seconds: 10
      resource_preset: "medium"  # low | medium | high | max
      network_enabled: false  # Disable network access
    inputs:
      user_code: "{state.code}"
    prompt: "Execute the provided code"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
          description: "Output from code execution"
```

**Resource presets:**
- `low` - CPU: 0.5, Memory: 256MB, Timeout: 5s
- `medium` - CPU: 1.0, Memory: 512MB, Timeout: 10s
- `high` - CPU: 2.0, Memory: 1GB, Timeout: 30s
- `max` - CPU: 4.0, Memory: 2GB, Timeout: 60s

### Persistent Memory (v1.0)

Use memory that persists across workflow runs:

```yaml
nodes:
  - id: load_memory
    memory:
      action: load  # load | save | delete
      namespace: "chat_history"
      key: "{state.user_id}"
    prompt: "Load previous conversation history"
    outputs: [context]
    output_schema:
      type: object
      fields:
        - name: context
          type: str

  - id: save_memory
    memory:
      action: save
      namespace: "chat_history"
      key: "{state.user_id}"
      value: "User: {state.message}\nAssistant: {state.response}"
    prompt: "Save conversation to memory"
    outputs: []
    output_schema:
      type: object
      fields: []
```

**Memory namespace pattern:**
```
{agent_id}:{workflow_id or "*"}:{node_id or "*"}:{key}
```

**Examples:**
- `agent:workflow:*:user_context` - User context for all nodes
- `agent:*:node1:cache` - Node-specific cache across workflows
- `*:*:*:global_config` - Global configuration

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

**Edges** define the execution order. In v1.0, **conditional routing, loops, and parallel execution** are supported.

### Linear Flow

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

### Conditional Routing (v1.0)

Route based on LLM outputs:

```yaml
edges:
  - from: START
    to: analyze

  # Conditional branches
  - from: analyze
    to: positive_response
    condition: "{state.sentiment} == 'positive'"

  - from: analyze
    to: negative_response
    condition: "{state.sentiment} == 'negative'"

  - from: analyze
    to: neutral_response
    condition: "{state.sentiment} == 'neutral'"

  # All paths converge to END
  - from: positive_response
    to: END
  - from: negative_response
    to: END
  - from: neutral_response
    to: END
```

**Condition syntax:**
- Use `{state.field}` to reference state values
- Supports Python comparison operators: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Supports logical operators: `and`, `or`, `not`
- Supports membership: `in`, `not in`

**Examples:**
```yaml
# Numeric comparison
condition: "{state.score} >= 90"

# String matching
condition: "{state.category} == 'urgent'"

# Logical AND
condition: "{state.score} >= 90 and {state.category} == 'urgent'"

# List membership
condition: "{state.status} in ['approved', 'pending']"

# Negation
condition: "not {state.is_error}"
```

### Loop Execution (v1.0)

Retry nodes with iteration tracking:

```yaml
edges:
  - from: START
    to: draft

  - from: draft
    to: evaluate

  # Loop back if quality < 7, max 3 iterations
  - from: evaluate
    to: refine
    condition: "{state.quality_score} < 7 and {state._loop_iteration_refine} < 3"

  - from: refine
    to: evaluate

  # Exit when quality >= 7 or max iterations reached
  - from: evaluate
    to: END
    condition: "{state.quality_score} >= 7 or {state._loop_iteration_refine} >= 3"
```

**Loop iteration tracking:**
- System automatically creates `_loop_iteration_{node_id}` state field
- Starts at 0, increments each time the node executes
- Use in conditions to enforce maximum iterations

**Example:**
```yaml
# First iteration: _loop_iteration_refine = 0
# Second iteration: _loop_iteration_refine = 1
# Third iteration: _loop_iteration_refine = 2
```

### Parallel Execution (v1.0)

Run multiple nodes concurrently:

```yaml
edges:
  - from: START
    to: [technical, business, ethical]  # Parallel execution

  # All three must complete before summarize
  - from: technical
    to: summarize
  - from: business
    to: summarize
  - from: ethical
    to: summarize

  - from: summarize
    to: END
```

**Parallel execution rules:**
- Multiple nodes can start from the same source
- All parallel nodes must complete before the next node
- Results from all nodes are available in the next node's state

**Parallel with conditional joins:**
```yaml
edges:
  - from: START
    to: [task1, task2, task3]

  # Exit when any 2 of 3 complete
  - from: task1
    to: finalize
  - from: task2
    to: finalize
  - from: task3
    to: finalize

  - from: finalize
    to: END
```

### Edge Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `from` | str or list | Yes | Source node ID (or list for parallel) |
| `to` | str | Yes | Target node ID |
| `condition` | str | No | Conditional expression for routing |

---

## Global Configuration

Optional settings that apply to all nodes.

### LLM Settings

```yaml
config:
  llm:
    provider: google  # Default provider
    model: "gemini-1.5-flash"
    temperature: 0.7
    max_tokens: 2048
```

**Fields:**
- `provider` - LLM provider (google, openai, anthropic, ollama)
- `model` - Model name (provider-specific)
- `temperature` - Creativity (0.0-1.0, default: 0.7)
- `max_tokens` - Max output length (default: 2048)

**Multi-provider defaults:**
```yaml
config:
  llm:
    # Default provider
    provider: google
    model: "gemini-1.5-flash"

    # Provider-specific defaults
    providers:
      openai:
        model: "gpt-4"
        temperature: 0.5
      anthropic:
        model: "claude-3-sonnet-20240229"
        temperature: 0.7
      ollama:
        model: "ollama_chat/llama2"
        temperature: 0.0
```

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

### Storage Backend (v1.0)

Configure storage for traces and metrics:

```yaml
config:
  storage:
    backend: sqlite  # sqlite | postgresql | redis
    connection_string: "sqlite:///configurable_agents.db"
```

**Storage backends:**
- `sqlite` - Default, file-based database
- `postgresql` - Remote database for production
- `redis` - In-memory cache (v1.1+)

### MLFlow 3.9 Observability (v1.0)

Track workflow costs, tokens, and performance with MLFlow 3.9:

```yaml
config:
  observability:
    mlflow:
      # Core settings
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"
      experiment_name: "my_workflows"

      # MLflow 3.9 features
      async_logging: true  # Async trace logging (default: true)

      # Artifact control
      log_artifacts: true
      artifact_level: "standard"  # minimal | standard | full

      # Optional
      run_name: null  # Custom run naming (optional)
```

**See [OBSERVABILITY.md](OBSERVABILITY.md) for full details.**

### Memory Configuration (v1.0)

Configure persistent memory backend:

```yaml
config:
  memory:
    backend: sqlite  # sqlite | postgresql | redis
    connection_string: "sqlite:///memory.db"
    default_ttl: 604800  # 7 days in seconds
```

### Performance Profiling (v1.0)

Enable performance profiling to identify bottlenecks:

```yaml
config:
  profiling:
    enabled: true
    bottleneck_threshold: 0.5  # Alert if node > 50% of total time
```

**Profile via CLI:**
```bash
export CONFIGURABLE_AGENTS_PROFILING=true
configurable-agents run workflow.yaml --input topic="AI"

# View profile report
configurable-agents observability profile-report
```

### Sandbox Configuration (v1.0)

Global sandbox settings:

```yaml
config:
  sandbox:
    enabled: false  # Opt-in per-node
    default_preset: "medium"
    network_enabled: false
    allowed_paths:
      - ./data
      - ./output
```

---

## v1.0 Feature Examples

### Multi-LLM Setup

```yaml
schema_version: "1.0"

flow:
  name: multi_llm_pipeline
  description: "Uses different LLMs for different tasks"

state:
  fields:
    topic: {type: str, required: true}
    research: {type: str, default: ""}
    critique: {type: str, default: ""}
    final_draft: {type: str, default: ""}

nodes:
  - id: research
    llm:
      provider: openai
      model: "gpt-4"
    prompt: "Research {state.topic} thoroughly"
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str

  - id: critique
    llm:
      provider: anthropic
      model: "claude-3-sonnet-20240229"
    prompt: "Critique this research:\n{state.research}"
    outputs: [critique]
    output_schema:
      type: object
      fields:
        - name: critique
          type: str

  - id: final_draft
    llm:
      provider: google
      model: "gemini-1.5-pro"
    prompt: |
      Research: {state.research}

      Critique: {state.critique}

      Write a final draft addressing the critique.
    outputs: [final_draft]
    output_schema:
      type: object
      fields:
        - name: final_draft
          type: str

edges:
  - from: START
    to: research
  - from: research
    to: critique
  - from: critique
    to: final_draft
  - from: final_draft
    to: END
```

### Conditional Routing

```yaml
schema_version: "1.0"

flow:
  name: content_filter
  description: "Routes content based on safety checks"

state:
  fields:
    content: {type: str, required: true}
    safety_rating: {type: str, default: ""}
    approved_content: {type: str, default: ""}
    rejection_reason: {type: str, default: ""}

nodes:
  - id: check_safety
    prompt: |
      Rate the safety of this content as: safe, sensitive, or unsafe
      Content: {state.content}

      Return ONLY one word.
    outputs: [safety_rating]
    output_schema:
      type: object
      fields:
        - name: safety_rating
          type: str

  - id: approve
    prompt: "Content approved: {state.content}"
    outputs: [approved_content]
    output_schema:
      type: object
      fields:
        - name: approved_content
          type: str

  - id: flag_sensitive
    prompt: "Flag sensitive content and explain why"
    outputs: [rejection_reason]
    output_schema:
      type: object
      fields:
        - name: rejection_reason
          type: str

  - id: block_unsafe
    prompt: "Block unsafe content and explain why"
    outputs: [rejection_reason]
    output_schema:
      type: object
      fields:
        - name: rejection_reason
          type: str

edges:
  - from: START
    to: check_safety

  - from: check_safety
    to: approve
    condition: "{state.safety_rating} == 'safe'"

  - from: check_safety
    to: flag_sensitive
    condition: "{state.safety_rating} == 'sensitive'"

  - from: check_safety
    to: block_unsafe
    condition: "{state.safety_rating} == 'unsafe'"

  - from: approve
    to: END
  - from: flag_sensitive
    to: END
  - from: block_unsafe
    to: END
```

### Loop Execution

```yaml
schema_version: "1.0"

flow:
  name: iterative_refinement
  description: "Refines output until quality threshold met"

state:
  fields:
    prompt: {type: str, required: true}
    draft: {type: str, default: ""}
    quality_score: {type: int, default: 0}

nodes:
  - id: generate
    prompt: "{state.prompt}"
    outputs: [draft]
    output_schema:
      type: object
      fields:
        - name: draft
          type: str

  - id: evaluate
    prompt: |
      Rate quality 1-10:
      {state.draft}

      Return ONLY a number.
    outputs: [quality_score]
    output_schema:
      type: object
      fields:
        - name: quality_score
          type: int

  - id: refine
    prompt: |
      Improve this draft (iteration {state._loop_iteration_refine}):
      {state.draft}

      Make it better.
    outputs: [draft]
    output_schema:
      type: object
      fields:
        - name: draft
          type: str

edges:
  - from: START
    to: generate
  - from: generate
    to: evaluate

  # Loop back if quality < 8, max 5 iterations
  - from: evaluate
    to: refine
    condition: "{state.quality_score} < 8 and {state._loop_iteration_refine} < 5"

  - from: refine
    to: evaluate

  # Exit when quality >= 8 or max iterations
  - from: evaluate
    to: END
    condition: "{state.quality_score} >= 8 or {state._loop_iteration_refine} >= 5"
```

### Parallel Execution

```yaml
schema_version: "1.0"

flow:
  name: parallel_analysis
  description: "Analyzes from multiple perspectives in parallel"

state:
  fields:
    topic: {type: str, required: true}
    technical: {type: str, default: ""}
    business: {type: str, default: ""}
    ethical: {type: str, default: ""}
    synthesis: {type: str, default: ""}

nodes:
  - id: technical_analysis
    prompt: "Technical analysis of {state.topic}"
    outputs: [technical]
    output_schema:
      type: object
      fields:
        - name: technical
          type: str

  - id: business_analysis
    prompt: "Business analysis of {state.topic}"
    outputs: [business]
    output_schema:
      type: object
      fields:
        - name: business
          type: str

  - id: ethical_analysis
    prompt: "Ethical analysis of {state.topic}"
    outputs: [ethical]
    output_schema:
      type: object
      fields:
        - name: ethical
          type: str

  - id: synthesize
    prompt: |
      Synthesize these analyses:
      Technical: {state.technical}
      Business: {state.business}
      Ethical: {state.ethical}
    outputs: [synthesis]
    output_schema:
      type: object
      fields:
        - name: synthesis
          type: str

edges:
  - from: START
    to: [technical_analysis, business_analysis, ethical_analysis]

  - from: technical_analysis
    to: synthesize
  - from: business_analysis
    to: synthesize
  - from: ethical_analysis
    to: synthesize

  - from: synthesize
    to: END
```

### Sandbox Code Execution

```yaml
schema_version: "1.0"

flow:
  name: safe_code_executor
  description: "Generates and executes code safely"

state:
  fields:
    task: {type: str, required: true}
    code: {type: str, default: ""}
    result: {type: str, default: ""}

nodes:
  - id: generate_code
    prompt: |
      Write Python code to: {state.task}
      Use print() for output.
      Return ONLY the code.
    outputs: [code]
    output_schema:
      type: object
      fields:
        - name: code
          type: str

  - id: execute_code
    sandbox:
      enabled: true
      timeout_seconds: 10
      resource_preset: "medium"
      network_enabled: false
    inputs:
      user_code: "{state.code}"
    prompt: "Execute the code"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str

edges:
  - from: START
    to: generate_code
  - from: generate_code
    to: execute_code
  - from: execute_code
    to: END
```

### Persistent Memory

```yaml
schema_version: "1.0"

flow:
  name: chatbot_with_memory
  description: "Remembers conversations across sessions"

state:
  fields:
    user_id: {type: str, required: true}
    message: {type: str, required: true}
    history: {type: str, default: ""}
    response: {type: str, default: ""}

nodes:
  - id: load_history
    memory:
      action: load
      namespace: "chat_history"
      key: "{state.user_id}"
    prompt: "Load conversation history"
    outputs: [history]
    output_schema:
      type: object
      fields:
        - name: history
          type: str

  - id: respond
    prompt: |
      History:
      {state.history}

      New message: {state.message}

      Respond helpfully.
    outputs: [response]
    output_schema:
      type: object
      fields:
        - name: response
          type: str

  - id: save_history
    memory:
      action: save
      namespace: "chat_history"
      key: "{state.user_id}"
      value: "User: {state.message}\nAssistant: {state.response}"
    prompt: "Save conversation"
    outputs: []
    output_schema:
      type: object
      fields: []

edges:
  - from: START
    to: load_history
  - from: load_history
    to: respond
  - from: respond
    to: save_history
  - from: save_history
    to: END
```

---

## Complete Example

Here's a full workflow demonstrating multiple v1.0 features:

```yaml
schema_version: "1.0"

flow:
  name: advanced_research_workflow
  description: "Multi-step research with parallel analysis and quality control"
  version: "1.0.0"

config:
  llm:
    provider: google
    model: "gemini-1.5-flash"
    temperature: 0.7

  execution:
    timeout_seconds: 120
    max_retries: 3

  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"

  memory:
    backend: sqlite
    connection_string: "sqlite:///memory.db"

state:
  fields:
    topic:
      type: str
      required: true
      description: "Research topic"

    initial_research:
      type: str
      default: ""
      description: "Initial research findings"

    technical_feasibility:
      type: str
      default: ""
      description: "Technical feasibility analysis"

    market_potential:
      type: str
      default: ""
      description: "Market potential analysis"

    risk_assessment:
      type: str
      default: ""
      description: "Risk assessment"

    quality_score:
      type: int
      default: 0
      description: "Quality score (1-10)"

    final_report:
      type: str
      default: ""
      description: "Final synthesized report"

nodes:
  - id: initial_research
    tools: [serper_search]
    prompt: |
      Conduct comprehensive research on: {state.topic}

      Use web search to find:
      - Recent developments
      - Key players
      - Market trends
      - Technical challenges

      Provide detailed findings.
    outputs: [initial_research]
    output_schema:
      type: object
      fields:
        - name: initial_research
          type: str
          description: "Research findings with sources"

  # These three nodes run in parallel
  - id: technical_analysis
    llm:
      provider: openai
      model: "gpt-4"
      temperature: 0.5
    prompt: |
      Based on this research:
      {state.initial_research}

      Analyze technical feasibility:
      - Current technology readiness
      - Implementation challenges
      - Required expertise
      - Timeline estimates
    outputs: [technical_feasibility]
    output_schema:
      type: object
      fields:
        - name: technical_feasibility
          type: str

  - id: market_analysis
    llm:
      provider: anthropic
      model: "claude-3-sonnet-20240229"
      temperature: 0.5
    prompt: |
      Based on this research:
      {state.initial_research}

      Analyze market potential:
      - Target market size
      - Growth projections
      - Competitive landscape
      - Revenue potential
    outputs: [market_potential]
    output_schema:
      type: object
      fields:
        - name: market_potential
          type: str

  - id: risk_analysis
    llm:
      provider: google
      model: "gemini-1.5-pro"
      temperature: 0.5
    prompt: |
      Based on this research:
      {state.initial_research}

      Assess risks:
      - Technical risks
      - Market risks
      - Regulatory risks
      - Mitigation strategies
    outputs: [risk_assessment]
    output_schema:
      type: object
      fields:
        - name: risk_assessment
          type: str

  - id: synthesize
    prompt: |
      Synthesize a comprehensive report:

      Research Base:
      {state.initial_research}

      Technical Analysis:
      {state.technical_feasibility}

      Market Analysis:
      {state.market_potential}

      Risk Assessment:
      {state.risk_assessment}

      Create an executive summary with actionable recommendations.
    outputs: [final_report]
    output_schema:
      type: object
      fields:
        - name: final_report
          type: str

  - id: quality_check
    prompt: |
      Rate the quality of this report (1-10):
      {state.final_report}

      Evaluate:
      - Depth of analysis
      - Clarity of recommendations
      - Completeness of research

      Return ONLY a number.
    outputs: [quality_score]
    output_schema:
      type: object
      fields:
        - name: quality_score
          type: int

  - id: refine_report
    prompt: |
      Improve this report (iteration {state._loop_iteration_refine}):
      {state.final_report}

      Address any gaps or weaknesses.
    outputs: [final_report]
    output_schema:
      type: object
      fields:
        - name: final_report
          type: str

edges:
  - from: START
    to: initial_research

  # Parallel execution of three analyses
  - from: initial_research
    to: [technical_analysis, market_analysis, risk_analysis]

  # All analyses must complete before synthesis
  - from: technical_analysis
    to: synthesize
  - from: market_analysis
    to: synthesize
  - from: risk_analysis
    to: synthesize

  - from: synthesize
    to: quality_check

  # Loop back if quality < 8, max 3 iterations
  - from: quality_check
    to: refine_report
    condition: "{state.quality_score} < 8 and {state._loop_iteration_refine} < 3"

  - from: refine_report
    to: quality_check

  # Exit when quality >= 8 or max iterations
  - from: quality_check
    to: END
    condition: "{state.quality_score} >= 8 or {state._loop_iteration_refine} >= 3"
```

**Run it:**
```bash
configurable-agents run advanced_research.yaml --input topic="Quantum Computing in Drug Discovery"
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

# Enable profiling
import os
os.environ["CONFIGURABLE_AGENTS_PROFILING"] = "true"
result = run_workflow("workflow.yaml", {"topic": "AI"})
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

| Feature | v0.1 | v1.0 |
|---------|------|------|
| Linear flows | ✅ | ✅ |
| Structured outputs | ✅ | ✅ |
| Google Gemini | ✅ | ✅ |
| Web search tool | ✅ | ✅ |
| Multi-LLM support | ❌ | ✅ |
| Conditional routing | ❌ | ✅ |
| Loops | ❌ | ✅ |
| Parallel execution | ❌ | ✅ |
| Code sandboxing | ❌ | ✅ |
| Persistent memory | ❌ | ✅ |
| Pre-built tools (15+) | ❌ | ✅ |
| Chat UI | ❌ | ✅ |
| Orchestration dashboard | ❌ | ✅ |
| Webhook integrations | ❌ | ✅ |

**All v1.0 features are production-ready.**

---

**Questions?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue!
