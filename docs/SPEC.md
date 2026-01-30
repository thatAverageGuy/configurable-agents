# Technical Specification

**Version**: v0.1 (Schema v1.0)
**Last Updated**: 2026-01-24

**Philosophy**: Full Schema Day One (see ADR-009)
- Schema supports all planned features (through v0.3)
- Runtime implements features incrementally
- No breaking changes across versions

---

## Config Schema v1.0

### Top-Level Structure

```yaml
schema_version: string        # Required: Config schema version
flow: FlowMetadata           # Required: Workflow metadata
state: StateSchema           # Required: State definition
nodes: list[NodeConfig]      # Required: Execution nodes
edges: list[EdgeConfig]      # Required: Control flow
optimization: OptimizationConfig  # Optional: DSPy settings (v0.3+)
config: GlobalConfig         # Optional: Infrastructure settings
```

---

## 1. Schema Version

```yaml
schema_version: "1.0"
```

**Type**: `string`
**Required**: Yes
**Purpose**: Identifies config schema version for forward compatibility

**Values**:
- `"1.0"`: Current schema (v0.1, v0.2, v0.3 all use this)
- Future versions will increment (1.1, 2.0, etc.)

**Why required**: Enables graceful schema evolution, migration tools, version-specific parsing if needed.

---

## 2. Flow Metadata

```yaml
flow:
  name: string              # Required
  description: string       # Optional
  version: string           # Optional
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Unique workflow identifier |
| `description` | `string` | No | Human-readable description |
| `version` | `string` | No | Workflow version (semantic versioning recommended) |

### Example

```yaml
flow:
  name: "article_generator"
  description: "Research topics and write articles"
  version: "1.0.0"
```

---

## 3. State Schema

Defines typed state that persists across node executions.

### Structure

```yaml
state:
  fields:
    <field_name>:
      type: <type_string>        # Required
      required: boolean          # Optional, default: false
      default: <value>           # Optional
      description: string        # Optional
```

### Field Properties

#### `type` (required)

**Basic types**:
- `str`: String
- `int`: Integer
- `float`: Float
- `bool`: Boolean

**Collection types**:
- `list`: Generic list
- `list[str]`, `list[int]`, `list[float]`: Typed lists
- `dict`: Generic dict
- `dict[str, int]`, `dict[str, str]`: Typed dicts

**Nested types**:
- `object`: Nested object with schema

#### `required` (optional, default: false)

If `true`, field must be provided in initial inputs.

**Cannot have both `required: true` and `default`.**

#### `default` (optional)

Default value if not provided.

#### `description` (optional)

Human-readable description. Used for:
- Documentation
- Future: AI config generators understanding field purpose

### Examples

#### Simple State

```yaml
state:
  fields:
    topic:
      type: str
      required: true
      description: "The topic to research"

    research:
      type: str
      default: ""
      description: "Research findings"
```

#### Nested State

```yaml
state:
  fields:
    user_profile:
      type: object
      description: "User information"
      schema:
        name: str
        email: str
        preferences: list[str]
```

#### Complex State

```yaml
state:
  fields:
    topic:
      type: str
      required: true

    research_data:
      type: object
      schema:
        summary: str
        sources: list[str]
        word_count: int

    feedback_history:
      type: list[str]
      default: []

    metadata:
      type: dict
      default: {}
```

---

## 4. Nodes

Execution units that call LLMs with optional tools.

### Node Structure

```yaml
nodes:
  - id: string                      # Required: Unique identifier
    description: string             # Optional: Human description
    inputs: dict[str, string]       # Optional: Input mapping
    prompt: string                  # Required: Prompt template
    output_schema: OutputSchema     # Required: Type enforcement
    outputs: list[string]           # Required: State fields to update
    tools: list[string]             # Optional: Tool names
    optimize: OptimizeConfig        # Optional: Node-level optimization (v0.3+)
    llm: LLMConfig                  # Optional: Node-level LLM override
```

### Fields

#### `id` (required)

Unique node identifier. Must be valid Python identifier (alphanumeric + underscore).

#### `description` (optional)

Human-readable description of what this node does.

#### `inputs` (optional)

**Explicit input mapping** from state to local variables.

**Format**: `dict[local_name, state_reference]`

```yaml
inputs:
  query: "{state.topic}"           # Maps state.topic → local var 'query'
  context: "{state.research}"      # Maps state.research → local var 'context'
```

**Purpose**:
- Resolves ambiguity (multiple state fields, same prompt variable name)
- Creates clean namespace for prompt
- Explicit contract

**If omitted**: Prompt can still reference `{state.field}` directly.

#### `prompt` (required)

Prompt template with placeholders.

**Placeholder syntax**: `{variable_name}`

**Variables**:
- Local variables from `inputs`: `{query}`
- State fields (if no inputs): `{state.topic}`

**Example**:
```yaml
inputs:
  topic: "{state.topic}"
  data: "{state.research}"

prompt: |
  Write an article about {topic}.
  Use this research: {data}

  Requirements:
  - 400-600 words
  - Engaging tone
  - Include sources
```

#### `output_schema` (required)

**Defines the structure and types that the LLM MUST return.**

This is the **killer feature**: Type enforcement via Pydantic.

##### Format: Object Output

```yaml
output_schema:
  type: object
  fields:
    - name: string              # Field name
      type: string              # Type
      description: string       # Optional: helps LLM
```

##### Format: Simple Output

```yaml
output_schema:
  type: str                     # For single string output
  description: string           # Optional
```

##### Supported Types

Same as state types: `str`, `int`, `float`, `bool`, `list`, `list[str]`, `dict`, `object`

##### Descriptions

**Highly recommended.** LLM uses these to understand what to return.

```yaml
output_schema:
  type: object
  fields:
    - name: summary
      type: str
      description: "Concise summary (100 words max)"
    - name: word_count
      type: int
      description: "Exact word count of summary"
    - name: sources
      type: list[str]
      description: "URLs of sources used"
```

#### `outputs` (required)

**List of state field names to update.**

Must match field names in `output_schema`.

```yaml
output_schema:
  type: object
  fields:
    - name: research_summary
      type: str
    - name: word_count
      type: int

outputs: [research_summary, word_count]  # Maps to state.research_summary, state.word_count
```

**Validation**: Parser checks that:
1. All `outputs` exist in state schema
2. All `output_schema` field names are in `outputs`
3. Types match (state.research_summary must be `str` if output is `str`)

#### `tools` (optional)

List of tool names from registry.

```yaml
tools:
  - serper_search
  - calculator
```

**v0.1 tools**: `serper_search`

**Validation**: Parser checks all tools exist in registry.

#### `optimize` (optional, v0.3+)

Node-level DSPy optimization config. Overrides global `optimization`.

```yaml
optimize:
  enabled: boolean           # Enable optimization for this node
  metric: string             # Metric name (must be in registry)
  strategy: string           # DSPy strategy
  max_demos: int             # Max few-shot examples
```

**v0.1 behavior**: Validated but ignored (feature gating).

#### `llm` (optional)

Node-level LLM config. Overrides global `config.llm`.

```yaml
llm:
  provider: string           # v0.1: only "google"
  model: string
  temperature: float
  max_tokens: int
```

### Example Node

```yaml
nodes:
  - id: "research_node"
    description: "Gather research using web search"

    inputs:
      query: "{state.topic}"

    prompt: |
      Research this query: {query}

      Provide:
      - A concise summary (100 words)
      - List of source URLs
      - Word count of your summary

    output_schema:
      type: object
      fields:
        - name: summary
          type: str
          description: "Research summary"
        - name: sources
          type: list[str]
          description: "Source URLs"
        - name: word_count
          type: int
          description: "Word count of summary"

    outputs: [summary, sources, word_count]

    tools:
      - serper_search

    llm:
      temperature: 0.3
```

---

## 5. Edges

Defines control flow between nodes.

### Edge Structure

```yaml
edges:
  - from: string                    # Required: Source node (or START)
    to: string                      # Required: Target node (or END) [Linear only in v0.1]
    routes: list[Route]             # Optional: Conditional routing (v0.2+)
```

### Linear Edges (v0.1)

```yaml
edges:
  - from: START
    to: research_node

  - from: research_node
    to: write_node

  - from: write_node
    to: END
```

**Reserved keywords**:
- `START`: Entry point
- `END`: Exit point

**Validation (v0.1)**:
- Exactly one edge from `START`
- Exactly one edge to `END` (or path to END from all nodes)
- All nodes reachable from `START`
- No cycles (linear flows only)
- Each node has at most one outgoing edge

### Conditional Edges (v0.2+)

**Schema supported, runtime in v0.2.**

```yaml
edges:
  - from: validate_node
    routes:
      - condition:
          logic: "{state.score} >= 8"
        to: END

      - condition:
          logic: "default"     # Catch-all
        to: write_node
```

**v0.1 behavior**: Parser accepts, validator checks syntax, runtime rejects with error:
```
Error: Conditional routing not supported in v0.1
Found conditional edge from 'validate_node'

Coming in v0.2 (8 weeks). See docs/ROADMAP.md

To run in v0.1, use linear edge:
  - from: validate_node
    to: END
```

---

## 6. Optimization (v0.3+)

Global DSPy optimization config.

**Schema supported, runtime in v0.3.**

### Structure

```yaml
optimization:
  enabled: boolean               # Default: false
  strategy: string               # Default: "BootstrapFewShot"
  metric: string                 # Default: "semantic_match"
  max_demos: int                 # Default: 4
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `false` | Enable DSPy optimization |
| `strategy` | `string` | `"BootstrapFewShot"` | DSPy optimizer strategy |
| `metric` | `string` | `"semantic_match"` | Metric name (must be in registry) |
| `max_demos` | `int` | `4` | Max few-shot examples |

### Example

```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
  metric: "semantic_match"
  max_demos: 8
```

**v0.1 behavior**: Validated, warning issued if `enabled: true`, but feature ignored.

```
Warning: Optimization enabled but not supported in v0.1
Config validated but optimization will be ignored.
Coming in v0.3 (12 weeks).
```

---

## 7. Global Config

Infrastructure settings.

### Structure

```yaml
config:
  llm: LLMConfig                    # Optional
  execution: ExecutionConfig        # Optional
  observability: ObservabilityConfig  # Optional (v0.2+)
```

### 7.1. LLM Config

```yaml
config:
  llm:
    provider: string               # Default: "google"
    model: string                  # Default: "gemini-2.0-flash-exp"
    temperature: float             # Default: 0.7
    max_tokens: int                # Optional
```

**v0.1 providers**: `google` only

**v0.2+**: `openai`, `anthropic`, `ollama`

### 7.2. Execution Config

```yaml
config:
  execution:
    timeout: int                   # Default: 120 (seconds)
    max_retries: int               # Default: 3
```

### 7.3. Observability Config (v0.2+)

**Schema supported, runtime in v0.2.**

```yaml
config:
  observability:
    mlflow:
      enabled: boolean
      experiment: string
      log_prompts: boolean
    logging:
      level: string                # DEBUG, INFO, WARNING, ERROR
```

**v0.1**: Only console logging (stdlib `logging`).

---

## Complete Example Config

```yaml
# ============================================
# Article Generator Flow
# Schema v1.0 | Runtime v0.1
# ============================================

schema_version: "1.0"

# Metadata
flow:
  name: "article_generator"
  description: "Research topics and write articles"
  version: "1.0.0"

# State Schema
state:
  fields:
    # Input
    topic:
      type: str
      required: true
      description: "Topic to research and write about"

    # Intermediate state
    research_summary:
      type: str
      default: ""

    sources:
      type: list[str]
      default: []

    # Output
    article:
      type: str
      default: ""

    # Metadata
    word_count:
      type: int
      default: 0

# Nodes
nodes:
  - id: "research"
    description: "Research the topic using web search"

    inputs:
      query: "{state.topic}"

    prompt: |
      Research this topic: {query}

      Provide a summary (100 words) and list of sources.

    output_schema:
      type: object
      fields:
        - name: research_summary
          type: str
          description: "Concise research summary"
        - name: sources
          type: list[str]
          description: "Source URLs"

    outputs: [research_summary, sources]

    tools:
      - serper_search

    llm:
      temperature: 0.3

  - id: "write"
    description: "Write article based on research"

    inputs:
      topic: "{state.topic}"
      research: "{state.research_summary}"
      sources: "{state.sources}"

    prompt: |
      Write a high-quality article about {topic}.

      Research: {research}
      Sources: {sources}

      Requirements:
      - 400-600 words
      - Engaging and accurate
      - Reference sources naturally

      Return the article and exact word count.

    output_schema:
      type: object
      fields:
        - name: article
          type: str
          description: "The article text"
        - name: word_count
          type: int
          description: "Exact word count"

    outputs: [article, word_count]

    llm:
      temperature: 0.9

# Edges (Linear in v0.1)
edges:
  - from: START
    to: research

  - from: research
    to: write

  - from: write
    to: END

# Global Config
config:
  llm:
    provider: "google"
    model: "gemini-2.0-flash-exp"
    temperature: 0.7

  execution:
    timeout: 180
    max_retries: 3
```

---

## Validation Rules

### Parse-Time Validation (T-004)

All validation happens before execution:

1. **Schema version**: `schema_version` is present and valid
2. **Required sections**: `flow`, `state`, `nodes`, `edges` present
3. **Flow metadata**: `flow.name` is present
4. **State schema**:
   - At least one state field defined
   - Field names are valid Python identifiers
   - Types are valid
   - Required fields don't have defaults
5. **Nodes**:
   - Node IDs are unique
   - Node IDs are valid identifiers
   - `output_schema` is present
   - `outputs` list matches `output_schema` field names
   - All `outputs` reference valid state fields
   - Output types match state field types
   - All tools referenced exist in registry
   - Prompt placeholders reference valid inputs or state fields
6. **Edges**:
   - All `from` and `to` references point to valid nodes or START/END
   - Exactly one edge from `START`
   - All nodes have path to `END`
   - No orphaned nodes
   - (v0.1) No cycles, no multiple outgoing edges per node
7. **Optimization** (v0.3+):
   - Strategy is valid
   - Metric exists in registry
8. **Config**:
   - LLM provider is valid (v0.1: only "google")
   - Model exists for provider
   - Execution values are positive integers

### Runtime Feature Gating (T-004.5)

After parse-time validation, before execution:

```python
def validate_runtime_support(config: WorkflowConfig) -> None:
    """Check if runtime can execute this config."""

    # Check for conditional edges
    for edge in config.edges:
        if edge.routes:
            raise UnsupportedFeatureError(
                f"Conditional routing not supported in v0.1\n"
                f"Found in edge from '{edge.from_node}'\n\n"
                f"Coming in v0.2 (8 weeks)\n"
                f"See: docs/ROADMAP.md"
            )

    # Check for optimization
    if config.optimization and config.optimization.enabled:
        warnings.warn(
            f"Optimization enabled but not supported in v0.1\n"
            f"Feature will be ignored\n"
            f"Coming in v0.3 (12 weeks)"
        )

    # Check for observability
    if config.config.observability:
        warnings.warn(
            f"Observability config found but not supported in v0.1\n"
            f"Only console logging available\n"
            f"Coming in v0.2 (8 weeks)"
        )
```

---

## Type Enforcement

**How it works**:

1. **Config defines Pydantic model**:
   ```yaml
   output_schema:
     type: object
     fields:
       - name: score
         type: int
   ```

2. **Runtime generates model**:
   ```python
   OutputModel = create_model(
       'OutputModel',
       score=(int, ...)
   )
   ```

3. **LLM call with structured output**:
   ```python
   response = llm.with_structured_output(OutputModel).invoke(prompt)
   # response is validated OutputModel instance
   ```

4. **Validation happens automatically**:
   - LLM returns `{"score": "seven"}` → **Fails** (str vs int)
   - LLM returns `{"score": 7}` → **Passes**

5. **Retry on failure** (configurable):
   ```python
   try:
       response = llm.with_structured_output(OutputModel).invoke(prompt)
   except ValidationError:
       # Retry with clarified prompt
       response = llm.with_structured_output(OutputModel).invoke(
           prompt + "\n\nIMPORTANT: Return 'score' as an integer, not a word."
       )
   ```

---

## JSON Support

**Schema v1.0 is 1:1 in YAML and JSON.**

```json
{
  "schema_version": "1.0",
  "flow": {
    "name": "article_generator",
    "version": "1.0.0"
  },
  "state": {
    "fields": {
      "topic": {
        "type": "str",
        "required": true
      }
    }
  },
  "nodes": [...],
  "edges": [...],
  "config": {...}
}
```

**Implementation**: Pydantic models support both formats natively.

```python
# Load YAML
config = WorkflowConfig(**yaml.safe_load(yaml_string))

# Load JSON
config = WorkflowConfig(**json.loads(json_string))

# Dump YAML
yaml_string = yaml.dump(config.dict())

# Dump JSON
json_string = json.dumps(config.dict())
```

---

## Observability Configuration (v0.1+)

### config.observability

Optional configuration for workflow observability and monitoring.

**Schema**:
```yaml
config:
  observability:
    mlflow:
      enabled: true                          # Enable MLFlow tracking
      tracking_uri: "file://./mlruns"        # Storage backend URI
      experiment_name: "my_workflows"        # Experiment grouping
      run_name: null                         # Run naming template (optional)
      log_artifacts: true                    # Log inputs/outputs as artifacts

      # Enterprise hooks (not enforced in v0.1, reserved for v0.2+)
      retention_days: null                   # Auto-cleanup old runs (future)
      redact_pii: false                      # PII sanitization (future)
```

### Fields

**enabled** (bool, default: `false`):
- Enable MLFlow tracking for workflow execution
- If disabled, workflow runs normally without tracking overhead

**tracking_uri** (str, default: `"file://./mlruns"`):
- Backend storage URI for MLFlow tracking data
- Supported formats:
  - `file://./mlruns` - Local file storage (default, zero setup)
  - `file:///absolute/path` - Absolute path
  - `postgresql://user:pass@host/db` - PostgreSQL (v0.2+, team collaboration)
  - `s3://bucket/path` - AWS S3 (v0.2+, cloud storage)
  - `databricks://workspace` - Databricks Managed MLFlow (v0.2+, enterprise)

**experiment_name** (str, default: `"configurable_agents"`):
- Groups related workflow runs together
- Use meaningful names for organization (e.g., "production_workflows", "testing", "team_data_science")

**run_name** (str, optional):
- Template for naming individual runs
- If not specified, MLFlow generates timestamp-based names
- Example: `"run_{timestamp}"`, `"workflow_{workflow_name}"`

**log_artifacts** (bool, default: `true`):
- Whether to save inputs, outputs, prompts, and responses as artifacts
- Set to `false` for high-throughput scenarios (reduces I/O)
- Artifacts enable debugging but increase storage usage

### Enterprise Hooks (v0.2+)

**retention_days** (int, optional):
- Automatically delete runs older than N days
- Not enforced in v0.1 (reserved for future)
- User responsibility to manage storage in v0.1

**redact_pii** (bool, default: `false`):
- Sanitize personally identifiable information before logging
- Not enforced in v0.1 (reserved for future)
- User responsibility to handle PII in v0.1

### What Gets Tracked

**Workflow-level metrics**:
- `workflow_name`, `workflow_version`, `schema_version`
- `global_model`, `global_temperature`
- `duration_seconds`, `node_count`, `retry_count`
- `total_input_tokens`, `total_output_tokens`, `total_cost_usd`
- `status` (1 = success, 0 = failure)

**Workflow-level artifacts**:
- `inputs.json` - Workflow inputs
- `outputs.json` - Workflow outputs
- `error.txt` - Error details (if failed)

**Node-level metrics** (nested runs):
- `node_id`, `node_model`, `tools`
- `node_duration_ms`, `input_tokens`, `output_tokens`, `retries`

**Node-level artifacts**:
- `prompt.txt` - Resolved prompt template
- `response.txt` - Raw LLM response

### Usage Examples

**Enable observability**:
```yaml
config:
  llm:
    provider: google
    model: gemini-1.5-flash
  observability:
    mlflow:
      enabled: true
```

**View traces**:
```bash
configurable-agents run workflow.yaml --input topic="AI"
mlflow ui  # Open http://localhost:5000
```

**Team collaboration** (v0.2+):
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "postgresql://mlflow:pass@db.example.com/mlflow"
      experiment_name: "team_production"
```

**Enterprise with retention** (v0.2+):
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "s3://company-mlflow/workflows"
      experiment_name: "production"
      retention_days: 90
      redact_pii: true
```

### Cost Tracking

MLFlow automatically tracks token usage and estimated costs:

**Token pricing** (built-in):
- `gemini-1.5-flash`: $0.000035/1K input, $0.00014/1K output
- `gemini-1.5-pro`: $0.00035/1K input, $0.0014/1K output
- More models added as multi-LLM support expands (v0.2+)

**Metrics logged**:
- `cost_usd` - Total estimated cost per run
- `cost_per_node_avg` - Average cost per node

**Query costs**:
```python
import mlflow
client = mlflow.tracking.MlflowClient()
runs = client.search_runs(experiment_ids=["0"])
total_cost = sum(run.data.metrics.get("cost_usd", 0) for run in runs)
print(f"Total spent: ${total_cost:.4f}")
```

### Docker Integration

When workflows are deployed as Docker containers (v0.1+), MLFlow UI runs inside the container:

**Deployment**:
```bash
configurable-agents deploy workflow.yaml
# Container exposes:
# - Port 8000: Workflow API
# - Port 5000: MLFlow UI
```

**Access**:
- Workflow API: `http://localhost:8000`
- MLFlow UI: `http://localhost:5000`
- Traces persist across container restarts (volume mount)

### Validation

**Invalid tracking URI**:
```yaml
config:
  observability:
    mlflow:
      tracking_uri: "invalid://uri"  # ❌ ValidationError
```

**Valid URIs**:
- `file://./mlruns` ✅
- `file:///absolute/path` ✅
- `postgresql://user:pass@host/db` ✅ (v0.2+)
- `s3://bucket/path` ✅ (v0.2+)

### Related ADRs
- ADR-011: MLFlow for LLM Observability
- ADR-014: Three-Tier Observability Strategy

---

## References

- Full Schema Day One: docs/adr/ADR-009
- Pydantic validation: https://docs.pydantic.dev/
- YAML spec: https://yaml.org/spec/1.2/spec.html

---

## Change Log

**v1.0.1 (2026-01-30)**:
- Added observability configuration (MLFlow)
- Added cost tracking specification
- Added Docker deployment integration notes

**v1.0 (2026-01-24)**:
- Initial schema design
- Full feature support (linear flows to DSPy optimization)
- Type enforcement via Pydantic
- Forward-compatible structure
