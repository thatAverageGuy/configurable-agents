# MLflow 3.9 Enhanced Observability Design

> **Purpose**: Design enhanced observability features leveraging MLflow 3.9 capabilities
>
> **Created**: 2026-02-02 (Phase 3 of T-028: MLFlow 3.9 Comprehensive Migration)
>
> **Status**: Design Complete - Ready for Phase 4 (Implementation)

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Enhanced Metrics Schema](#2-enhanced-metrics-schema)
3. [Artifact Strategy](#3-artifact-strategy)
4. [LLM Judge Integration](#4-llm-judge-integration)
5. [Quality Assessment Framework](#5-quality-assessment-framework)
6. [Tool Call Visualization](#6-tool-call-visualization)
7. [Prompt Versioning Strategy](#7-prompt-versioning-strategy)
8. [Cost Analysis Enhancements](#8-cost-analysis-enhancements)
9. [Dashboard Design](#9-dashboard-design)
10. [Implementation Priorities](#10-implementation-priorities)

---

## 1. Design Philosophy

### 1.1 Core Principles

**1. Progressive Disclosure**
- Basic metrics visible by default
- Advanced features opt-in via configuration
- No overwhelming users with too much data

**2. Actionable Insights**
- Every metric should answer a question
- Clear next steps for optimization
- Comparison capabilities (runs, experiments, time periods)

**3. Zero-Overhead by Default**
- Async logging for production
- Sampling strategies for high-volume scenarios
- Configurable detail levels (minimal/standard/full)

**4. Backward Compatible**
- All new features opt-in
- Existing configs work unchanged
- Gradual adoption path

**5. Developer Experience First**
- Easy to understand what's being tracked
- Clear error messages
- Helpful defaults

### 1.2 Observability Goals

**For Development:**
- Understand workflow behavior
- Debug failed runs quickly
- Optimize prompt and model selection
- Compare different configurations

**For Production:**
- Monitor performance trends
- Track costs and token usage
- Assess output quality
- Identify anomalies and errors

**For Business:**
- Cost attribution per workflow/node
- Quality metrics over time
- Usage analytics
- ROI analysis

---

## 2. Enhanced Metrics Schema

### 2.1 Workflow-Level Metrics

#### Automatic Metrics (from MLflow 3.9 autolog)

```yaml
Automatic Capture (mlflow.langchain.autolog):
  trace_id: <uuid>                    # Unique trace identifier
  status: SUCCESS | ERROR | TIMEOUT   # Execution status
  start_time: <timestamp>             # UTC start time
  end_time: <timestamp>               # UTC end time
  duration_ms: <float>                # Total execution time

  # Token usage (automatic from mlflow.trace.tokenUsage)
  total_tokens: <int>
  prompt_tokens: <int>
  completion_tokens: <int>

  # Agent-specific (from GenAI dashboard)
  node_count: <int>                   # Number of nodes executed
  llm_call_count: <int>               # Total LLM calls
  tool_call_count: <int>              # Total tool invocations
  retry_count: <int>                  # Total retries across all nodes
```

#### Custom Metrics (added by our tracker)

```yaml
Custom Metrics (logged via mlflow.log_metrics):
  # Cost metrics
  total_cost_usd: <float>             # Estimated total cost
  cost_per_token: <float>             # Average cost per token
  cost_per_second: <float>            # Cost rate

  # Performance metrics
  tokens_per_second: <float>          # Processing throughput
  mean_node_duration_ms: <float>      # Average node execution time
  max_node_duration_ms: <float>       # Slowest node

  # Quality metrics (if enabled)
  mean_quality_score: <float>         # Average LLM judge score (0-1)
  min_quality_score: <float>          # Lowest quality node
  quality_threshold_pass: <bool>      # Did all nodes meet threshold?

  # Efficiency metrics
  token_efficiency: <float>           # Output tokens / Total tokens
  prompt_efficiency: <float>          # Useful output / Input tokens

  # Workflow metadata
  schema_version: <str>               # Config schema version
  workflow_version: <str>             # Workflow version (from config)
```

### 2.2 Node-Level Metrics (Spans)

#### Automatic Span Attributes (from autolog)

```yaml
Span: node_<node_id>
  span_id: <uuid>
  parent_id: <workflow_trace_id>
  name: node_<node_id>
  span_type: AGENT
  status: SUCCESS | ERROR

  # Automatic attributes
  mlflow.chat.tokenUsage:
    prompt_tokens: <int>
    completion_tokens: <int>
    total_tokens: <int>

  # LLM attributes
  ai.model.name: <str>                # e.g., "gemini-2.0-flash-exp"
  ai.model.provider: <str>            # e.g., "google"
  ai.temperature: <float>             # Temperature setting
  ai.max_tokens: <int>                # Max tokens setting

  # Inputs/outputs (automatic)
  inputs: <json>                      # Node inputs (state + mappings)
  outputs: <json>                     # Node outputs (structured)
```

#### Custom Span Attributes (added by our code)

```yaml
Custom Attributes (via span.set_attributes):
  # Node metadata
  node.id: <str>                      # Node identifier
  node.type: <str>                    # research | write | edit | etc.
  node.description: <str>             # Node description

  # Execution details
  node.duration_ms: <float>           # Node execution time
  node.retry_count: <int>             # Retries for this node
  node.cost_usd: <float>              # Estimated cost for this node

  # Tool usage (if applicable)
  node.tools: [<str>]                 # List of tools available
  node.tool_calls: <int>              # Number of tool invocations

  # Quality assessment (if enabled)
  node.quality_score: <float>         # LLM judge score (0-1)
  node.quality_rationale: <str>       # Judge reasoning (preview)

  # Prompt metadata
  node.prompt_length: <int>           # Prompt character count
  node.prompt_version: <str>          # Prompt version (if using registry)

  # Output metadata
  node.output_schema: <str>           # Output type (str, object, etc.)
  node.output_fields: [<str>]         # Output field names
  node.output_length: <int>           # Output character count
```

### 2.3 Tool Call Metrics (Sub-Spans)

```yaml
Span: tool_<tool_name>
  parent_id: <node_span_id>
  name: tool_<tool_name>
  span_type: TOOL

  # Automatic attributes
  tool.name: <str>                    # e.g., "serper_search"
  tool.input: <json>                  # Tool input parameters
  tool.output: <json>                 # Tool return value
  tool.duration_ms: <float>           # Tool execution time
  tool.status: SUCCESS | ERROR        # Tool execution status

  # Custom attributes
  tool.result_count: <int>            # Number of results (if applicable)
  tool.api_cost_usd: <float>          # API cost (if tracked)
```

### 2.4 Metrics Comparison Table

| Metric Category | Current (2.9+) | MLflow 3.9 Auto | Custom Added | Source |
|----------------|----------------|-----------------|--------------|--------|
| Duration | ✅ Manual | ✅ Automatic | - | Trace |
| Token usage | ✅ Manual | ✅ Automatic | - | Span attribute |
| Cost | ✅ Manual | ❌ | ✅ Calculated | CostEstimator |
| Node count | ✅ Manual | ✅ Automatic | - | Trace |
| Retry count | ✅ Manual | ❌ | ✅ Aggregated | Custom |
| Tool calls | ❌ | ✅ Automatic | - | Tool spans |
| Quality scores | ❌ | ❌ | ✅ LLM judges | Judge API |
| Prompt versions | ❌ | ❌ | ✅ Registry | Prompt registry |
| Performance metrics | ❌ | ❌ | ✅ Calculated | Derived |

---

## 3. Artifact Strategy

### 3.1 Artifact Levels (Preserved from Current)

**Minimal** (Production default):
- Workflow inputs (JSON)
- Workflow outputs (JSON)
- Error details (if failed)
- Cost summary (JSON)

**Standard** (Development default):
- Minimal +
- Node prompts (per node, text)
- Node responses (per node, JSON)
- Tool call logs (if tools used, JSON)
- Quality assessment report (if enabled, JSON)

**Full** (Debug mode):
- Standard +
- Full state snapshots (per node, JSON)
- LLM raw responses (before parsing, JSON)
- Token usage breakdown (CSV)
- Performance timeline (JSON)
- Trace visualization (HTML)

### 3.2 Artifact Schema

#### Workflow Artifacts

**inputs.json** (Minimal+)
```json
{
  "workflow_name": "article_writer",
  "workflow_version": "1.0.0",
  "timestamp": "2026-02-02T10:30:00Z",
  "inputs": {
    "topic": "AI Safety",
    "style": "technical"
  }
}
```

**outputs.json** (Minimal+)
```json
{
  "workflow_name": "article_writer",
  "workflow_version": "1.0.0",
  "timestamp": "2026-02-02T10:32:15Z",
  "status": "success",
  "duration_seconds": 135.4,
  "outputs": {
    "article": "AI Safety is...",
    "references": ["source1", "source2"]
  }
}
```

**cost_summary.json** (Minimal+)
```json
{
  "total_cost_usd": 0.002345,
  "total_tokens": 2450,
  "breakdown": [
    {
      "node_id": "research",
      "model": "gemini-2.0-flash-exp",
      "tokens": {"prompt": 150, "completion": 800},
      "cost_usd": 0.001000
    },
    {
      "node_id": "write",
      "model": "gemini-2.0-flash-exp",
      "tokens": {"prompt": 950, "completion": 550},
      "cost_usd": 0.001345
    }
  ],
  "models_used": ["gemini-2.0-flash-exp"],
  "cost_per_model": {
    "gemini-2.0-flash-exp": 0.002345
  }
}
```

**error.json** (Minimal+, if failed)
```json
{
  "error_type": "NodeExecutionError",
  "error_message": "Node 'research': LLM call failed: Rate limit exceeded",
  "node_id": "research",
  "timestamp": "2026-02-02T10:31:00Z",
  "stack_trace": "...",
  "retry_count": 3,
  "last_known_state": {
    "topic": "AI Safety"
  }
}
```

#### Node Artifacts (Standard+)

**node_<node_id>_prompt.txt** (Standard+)
```
You are a research assistant. Research the following topic: AI Safety

Topic: AI Safety
Style: technical

Provide comprehensive research findings.
```

**node_<node_id>_response.json** (Standard+)
```json
{
  "node_id": "research",
  "model": "gemini-2.0-flash-exp",
  "timestamp": "2026-02-02T10:31:30Z",
  "response": {
    "findings": "AI Safety research focuses on...",
    "sources": ["https://..."]
  },
  "metadata": {
    "tokens": {"prompt": 150, "completion": 800},
    "duration_ms": 2300,
    "retry_count": 0
  }
}
```

**tool_calls.json** (Standard+, if tools used)
```json
{
  "node_id": "research",
  "tool_calls": [
    {
      "tool_name": "serper_search",
      "timestamp": "2026-02-02T10:31:25Z",
      "input": {"query": "AI Safety research papers"},
      "output": {
        "results": [
          {"title": "...", "url": "...", "snippet": "..."}
        ],
        "result_count": 10
      },
      "duration_ms": 450,
      "cost_usd": 0.001
    }
  ],
  "total_tool_calls": 1,
  "total_tool_cost_usd": 0.001
}
```

#### Quality Artifacts (Standard+, if enabled)

**quality_assessment.json** (Standard+)
```json
{
  "workflow_name": "article_writer",
  "assessment_timestamp": "2026-02-02T10:32:20Z",
  "overall_quality": {
    "score": 0.87,
    "threshold": 0.75,
    "passed": true
  },
  "node_assessments": [
    {
      "node_id": "research",
      "judge": "relevance",
      "score": 0.92,
      "rationale": "Research findings are highly relevant to AI Safety topic",
      "passed": true
    },
    {
      "node_id": "write",
      "judge": "coherence",
      "score": 0.82,
      "rationale": "Article is well-structured and logically coherent",
      "passed": true
    }
  ],
  "recommendations": [
    "Consider adding more recent sources (2025+)",
    "Expand section on alignment research"
  ]
}
```

#### Debug Artifacts (Full)

**state_snapshot_<node_id>.json** (Full)
```json
{
  "node_id": "write",
  "timestamp": "2026-02-02T10:31:45Z",
  "state_before": {
    "topic": "AI Safety",
    "research": "AI Safety research focuses on..."
  },
  "state_after": {
    "topic": "AI Safety",
    "research": "AI Safety research focuses on...",
    "article": "AI Safety is a critical field..."
  }
}
```

**performance_timeline.json** (Full)
```json
{
  "workflow_start": "2026-02-02T10:30:00.000Z",
  "events": [
    {"time": 0, "event": "workflow_start"},
    {"time": 100, "event": "node_research_start"},
    {"time": 550, "event": "tool_serper_start"},
    {"time": 1000, "event": "tool_serper_end"},
    {"time": 2400, "event": "node_research_end"},
    {"time": 2500, "event": "node_write_start"},
    {"time": 135400, "event": "workflow_end"}
  ],
  "bottlenecks": [
    {"node": "write", "duration_ms": 132900, "percentage": 98.2}
  ]
}
```

**trace_visualization.html** (Full)
```html
<!-- Interactive HTML visualization of trace -->
<!-- Gantt chart of node execution -->
<!-- Token usage breakdown charts -->
<!-- Cost attribution pie chart -->
```

### 3.3 Artifact Configuration

```yaml
# In observability config
observability:
  mlflow:
    enabled: true

    # Artifact control
    log_artifacts: true
    artifact_level: standard  # minimal | standard | full

    # Per-artifact-type control (optional, overrides level)
    artifacts:
      inputs: true              # Always log inputs
      outputs: true             # Always log outputs
      prompts: true             # Log prompts (standard+)
      responses: true           # Log responses (standard+)
      tool_calls: true          # Log tool calls (standard+)
      quality: true             # Log quality assessments (standard+)
      state_snapshots: false    # Log state (full only)
      performance: false        # Log performance timeline (full only)
      visualizations: false     # Generate HTML viz (full only)
```

---

## 4. LLM Judge Integration

### 4.1 Judge Strategy

**Goals:**
- Assess output quality automatically
- Provide actionable feedback
- Track quality over time
- Enable quality-based optimization

**Approach:**
- Use MLflow 3.9 built-in judges for common cases
- Custom judges for domain-specific quality
- Async evaluation (post-workflow, non-blocking)
- Configurable per-node or per-workflow

### 4.2 Built-In Judges (MLflow 3.9)

**1. Relevance Judge**
- Assesses if output is relevant to the prompt/input
- Score: 0-1 (0 = irrelevant, 1 = highly relevant)
- Use for: Research, Q&A nodes

**2. Coherence Judge**
- Assesses logical consistency and flow
- Score: 0-1 (0 = incoherent, 1 = perfectly coherent)
- Use for: Writing, summarization nodes

**3. Groundedness Judge**
- Assesses if output is grounded in provided context
- Score: 0-1 (0 = not grounded, 1 = fully grounded)
- Use for: RAG, research nodes with sources

**4. Harmfulness Judge**
- Detects potentially harmful content
- Score: 0-1 (0 = harmful, 1 = safe)
- Use for: All user-facing outputs

**5. Answer Correctness Judge**
- Compares output to expected answer (requires ground truth)
- Score: 0-1 (0 = incorrect, 1 = correct)
- Use for: Testing, validation

### 4.3 Custom Judges for Our Use Cases

**1. Technical Accuracy Judge**
```python
# For technical content (articles, documentation)
judge = mlflow.metrics.genai.make_genai_metric(
    name="technical_accuracy",
    definition="Assess technical accuracy of AI/ML content",
    grading_prompt="""
    Evaluate the technical accuracy of the AI/ML content below.

    Content: {output}
    Topic: {topic}

    Score 0-1 based on:
    - Correctness of technical claims
    - Use of appropriate terminology
    - Factual accuracy
    - Absence of common misconceptions

    Return score and brief rationale.
    """,
    model="openai:/gpt-4o-mini",
    parameters={"temperature": 0.0},
    aggregations=["mean", "variance"],
    greater_is_better=True,
)
```

**2. Citation Quality Judge**
```python
# For content with references
judge = mlflow.metrics.genai.make_genai_metric(
    name="citation_quality",
    definition="Assess quality and relevance of citations",
    grading_prompt="""
    Evaluate the quality of citations in the content below.

    Content: {output}

    Score 0-1 based on:
    - Citations are from authoritative sources
    - Citations are recent (prefer 2023+)
    - Citations are relevant to claims
    - Proper attribution format

    Return score and brief rationale.
    """,
    model="openai:/gpt-4o-mini",
    parameters={"temperature": 0.0},
)
```

**3. Completeness Judge**
```python
# Assess if output addresses all requirements
judge = mlflow.metrics.genai.make_genai_metric(
    name="completeness",
    definition="Assess if output addresses all prompt requirements",
    grading_prompt="""
    Evaluate if the output addresses all requirements from the prompt.

    Prompt: {prompt}
    Output: {output}

    Score 0-1 based on:
    - All requested information provided
    - No major omissions
    - Sufficient detail level

    Return score and brief rationale.
    """,
    model="openai:/gpt-4o-mini",
    parameters={"temperature": 0.0},
)
```

### 4.4 Judge Configuration

```yaml
# In observability config
observability:
  mlflow:
    enabled: true
    enable_judges: true        # Enable LLM judge evaluation

    judges:
      # Workflow-level default judges
      workflow_defaults:
        - name: harmfulness      # Safety check (all outputs)
          threshold: 0.8         # Minimum acceptable score
          model: "openai:/gpt-4o-mini"

        - name: coherence        # Logical consistency
          threshold: 0.75
          model: "openai:/gpt-4o-mini"

      # Per-node judge overrides
      node_overrides:
        research:
          - name: relevance      # Research relevance
            threshold: 0.8
          - name: groundedness   # Grounded in sources
            threshold: 0.85
          - name: citation_quality  # Custom judge
            threshold: 0.75

        write:
          - name: coherence
            threshold: 0.85
          - name: technical_accuracy  # Custom judge
            threshold: 0.80
          - name: completeness    # Custom judge
            threshold: 0.80

      # Judge execution settings
      execution:
        mode: async              # async | sync | disabled
        timeout_seconds: 30      # Judge timeout per node
        retry_on_failure: true   # Retry failed judges
        log_rationale: true      # Log judge reasoning
```

### 4.5 Judge Execution Flow

```
Workflow Execution
     │
     ├─ Node 1 executes
     │    └─ Output captured in span
     │
     ├─ Node 2 executes
     │    └─ Output captured in span
     │
     └─ Workflow completes
          │
          ▼
     [ASYNC] Judge Evaluation
          │
          ├─ For each node:
          │    ├─ Run configured judges
          │    ├─ Calculate scores
          │    └─ Log to span attributes
          │
          └─ Aggregate workflow quality
               └─ Log to trace metadata
```

**Key Features:**
- Non-blocking (async by default)
- Runs after workflow completes
- Results logged back to trace
- Queryable for analysis

### 4.6 Judge Output Schema

```json
{
  "node_id": "write",
  "judges": [
    {
      "name": "coherence",
      "score": 0.87,
      "threshold": 0.75,
      "passed": true,
      "rationale": "Content flows logically from introduction to conclusion",
      "model": "openai:/gpt-4o-mini",
      "duration_ms": 1200,
      "timestamp": "2026-02-02T10:32:30Z"
    },
    {
      "name": "technical_accuracy",
      "score": 0.92,
      "threshold": 0.80,
      "passed": true,
      "rationale": "Technical claims are accurate, terminology is appropriate",
      "model": "openai:/gpt-4o-mini",
      "duration_ms": 1500,
      "timestamp": "2026-02-02T10:32:32Z"
    }
  ],
  "aggregate": {
    "mean_score": 0.895,
    "min_score": 0.87,
    "all_passed": true
  }
}
```

---

## 5. Quality Assessment Framework

### 5.1 Quality Dimensions

**1. Correctness**
- Technical accuracy
- Factual correctness
- No hallucinations

**2. Relevance**
- On-topic
- Addresses prompt requirements
- Appropriate scope

**3. Coherence**
- Logical flow
- Consistent narrative
- Clear structure

**4. Completeness**
- All requirements addressed
- Sufficient detail
- No major omissions

**5. Safety**
- No harmful content
- Appropriate tone
- Ethical considerations

### 5.2 Quality Scoring System

**Score Range:** 0.0 - 1.0

**Interpretation:**
- `0.9 - 1.0`: Excellent
- `0.8 - 0.9`: Good
- `0.7 - 0.8`: Acceptable
- `0.6 - 0.7`: Needs improvement
- `< 0.6`: Unacceptable

**Thresholds:**
- Production: 0.80 minimum
- Development: 0.70 minimum
- Experimental: 0.60 minimum

### 5.3 Quality Monitoring

**Dashboards:**

1. **Quality Trends Dashboard**
   - Mean quality score over time (line chart)
   - Quality by node (bar chart)
   - Quality distribution (histogram)
   - Failure rate (% below threshold)

2. **Quality Breakdown Dashboard**
   - Quality by dimension (radar chart)
   - Top/bottom performing runs
   - Quality correlation with cost/latency

3. **Improvement Opportunities Dashboard**
   - Nodes frequently below threshold
   - Common quality issues (from rationales)
   - Suggested optimizations

**Alerts:**
- Quality drops below threshold
- Quality variance increases significantly
- New types of quality failures detected

### 5.4 Quality-Based Workflows

**1. Quality Gating**
```yaml
# Block deployment if quality below threshold
quality_gate:
  enabled: true
  threshold: 0.80
  action: block  # block | warn | ignore
  judges: [coherence, technical_accuracy, harmfulness]
```

**2. Automatic Retry on Low Quality**
```yaml
# Retry node if quality too low
quality_retry:
  enabled: true
  threshold: 0.70
  max_retries: 2
  judges: [relevance, completeness]
```

**3. Quality-Based Prompt Optimization**
```yaml
# Use DSPy to optimize prompts based on quality scores
optimization:
  enabled: true
  metric: quality_score
  target: maximize
  strategy: BootstrapFewShot
```

---

## 6. Tool Call Visualization

### 6.1 Tool Call Tracking (Automatic in MLflow 3.9)

**What's Tracked:**
- Tool name
- Input arguments
- Output/return value
- Duration
- Success/failure status
- Parent node

**Span Hierarchy:**
```
Trace: workflow_execution
├─ Span: node_research
│  ├─ Span: tool_serper_search
│  │  ├─ input: {query: "AI Safety"}
│  │  └─ output: {results: [...]}
│  └─ Span: llm_call
└─ Span: node_write
   └─ Span: llm_call
```

### 6.2 Tool Call Metrics

**Aggregate Metrics:**
```yaml
# Workflow-level
total_tool_calls: <int>
unique_tools_used: <int>
tool_success_rate: <float>        # 0-1
tool_total_duration_ms: <float>
tool_avg_duration_ms: <float>

# Per-tool breakdown
tool_usage_breakdown:
  serper_search:
    calls: 3
    success: 3
    failure: 0
    total_duration_ms: 1350
    avg_duration_ms: 450
    total_cost_usd: 0.003
```

**Per-Call Metrics:**
```yaml
# In tool span attributes
tool.name: "serper_search"
tool.call_number: 1                # 1st, 2nd, 3rd call
tool.input_size: 45                # Characters in input
tool.output_size: 2340             # Characters in output
tool.result_count: 10              # Number of results (if applicable)
tool.cache_hit: false              # If tool supports caching
tool.api_cost_usd: 0.001
```

### 6.3 Tool Call Visualizations

**1. Tool Usage Frequency**
```
Bar chart: Tool name vs. Call count
Shows which tools are used most frequently
```

**2. Tool Performance**
```
Scatter plot: Duration vs. Success rate
Identify slow or unreliable tools
```

**3. Tool Call Timeline**
```
Gantt chart: Node execution with tool calls
See when tools are invoked during workflow
```

**4. Tool Cost Attribution**
```
Pie chart: Cost breakdown by tool
Understand tool API costs
```

**5. Tool Call Sequence**
```
Sankey diagram: Node → Tool → Result flow
Visualize tool usage patterns
```

### 6.4 Tool Call Analysis

**Questions Answered:**
1. Which tools are used most?
2. Which tools are slowest?
3. Which tools fail most often?
4. Are tools used efficiently? (redundant calls?)
5. What's the cost of each tool?
6. How do tool calls affect overall workflow time?

**Optimization Insights:**
- Identify redundant tool calls
- Suggest caching opportunities
- Recommend tool replacements (if alternative faster/cheaper)
- Detect missing batching opportunities

---

## 7. Prompt Versioning Strategy

### 7.1 Prompt Registry Integration

**Goal:** Track prompt evolution alongside workflow versions

**MLflow Prompt Registry Features:**
- Immutable versioning (Git-style)
- Side-by-side comparison
- Lineage tracking (prompts → experiments → models)
- Search and filtering

### 7.2 Prompt Versioning Workflow

**1. Register Prompts**
```python
from mlflow.prompts import create_prompt

# Register prompt template
prompt = mlflow.prompts.create_prompt(
    name="research_node_prompt",
    template="You are a research assistant. Research: {topic}\n\nStyle: {style}",
    parameters=["topic", "style"],
    tags={
        "node": "research",
        "workflow": "article_writer",
        "version": "1.0.0"
    }
)
# Returns: prompt_id = "research_node_prompt:v1"
```

**2. Use Versioned Prompts**
```python
# In node execution
prompt_template = mlflow.prompts.get_prompt(
    name="research_node_prompt",
    version=3  # Use specific version
)
filled_prompt = prompt_template.format(topic="AI Safety", style="technical")
```

**3. Track Lineage**
```python
# MLflow automatically links:
# - Prompt version → Trace/Run
# - Trace/Run → Workflow config
# - Complete lineage for reproducibility
```

### 7.3 Prompt Evolution Tracking

**Comparison Features:**
- Diff view (template changes)
- Performance comparison (metrics per version)
- Quality comparison (judge scores per version)
- Cost comparison (tokens/cost per version)

**Metrics Per Prompt Version:**
```json
{
  "prompt_name": "research_node_prompt",
  "versions": [
    {
      "version": 1,
      "template": "Research: {topic}",
      "usage_count": 150,
      "avg_quality_score": 0.75,
      "avg_tokens": 850,
      "avg_cost_usd": 0.0012
    },
    {
      "version": 2,
      "template": "You are a research assistant. Research: {topic}\n\nStyle: {style}",
      "usage_count": 300,
      "avg_quality_score": 0.87,  // Improved!
      "avg_tokens": 920,           // Slightly more
      "avg_cost_usd": 0.0013       // Slightly higher
    }
  ],
  "recommendation": "v2 provides 16% quality improvement for 8% cost increase"
}
```

### 7.4 Configuration Integration

```yaml
# Option 1: Embed prompts in config (current approach)
nodes:
  - id: research
    prompt: "Research the following topic: {topic}"  # Inline

# Option 2: Reference prompt registry (new, opt-in)
nodes:
  - id: research
    prompt_ref:
      name: research_node_prompt
      version: 2  # Or "latest"
    # prompt field ignored if prompt_ref present

# Option 3: Hybrid (fallback)
nodes:
  - id: research
    prompt: "Research: {topic}"        # Fallback if registry unavailable
    prompt_ref:
      name: research_node_prompt
      version: 2
```

### 7.5 Prompt Registry Benefits

**For Development:**
- A/B test prompt variations
- Track which prompts perform best
- Rollback to previous prompts easily
- Share prompts across workflows

**For Production:**
- Reproducibility (exact prompt version logged)
- Auditability (who changed what, when)
- Gradual rollout (test new prompts on subset)
- Performance monitoring per prompt version

---

## 8. Cost Analysis Enhancements

### 8.1 Current Cost Tracking (Preserved)

**CostEstimator class:**
- Pricing database for models
- Token-based cost calculation
- Per-node cost attribution

**Current Metrics:**
- `total_cost_usd`
- `node_cost_usd` (per node)
- `total_input_tokens`, `total_output_tokens`

### 8.2 Enhanced Cost Metrics

**New Workflow-Level Metrics:**
```yaml
# Cost efficiency
cost_per_token: <float>              # Total cost / Total tokens
cost_per_second: <float>             # Total cost / Duration
tokens_per_dollar: <float>           # Inverse of cost_per_token

# Cost attribution
cost_by_phase:
  research: 0.001000
  write: 0.001345
cost_percentage_by_phase:
  research: 42.6%
  write: 57.4%

# Model cost breakdown
cost_by_model:
  gemini-2.0-flash-exp: 0.002345
  gemini-1.5-pro: 0.000000  # Not used this run

# Relative cost
cost_vs_median: 0.95               # This run vs. median cost
cost_vs_p95: 0.70                  # This run vs. 95th percentile
```

**New Node-Level Metrics:**
```yaml
# Per-node efficiency
node.cost_per_output_token: <float>  # Cost / Output tokens
node.value_efficiency: <float>       # Quality score / Cost

# Optimization potential
node.estimated_savings_gemini_1_5_flash: 0.0005  # If switched model
node.estimated_savings_cache: 0.0002             # If cached similar prompts
```

### 8.3 Cost Visualizations

**1. Cost Breakdown Pie Chart**
- Show cost % per node
- Identify expensive nodes

**2. Cost Over Time (Line Chart)**
- Track cost trends
- Detect cost anomalies

**3. Cost vs. Quality Scatter Plot**
- Show cost-quality tradeoff
- Identify sweet spots

**4. Cost Heatmap (Node × Run)**
- See cost patterns across runs
- Identify consistently expensive nodes

**5. Cost Attribution Sunburst**
- Hierarchical cost breakdown
- Workflow → Node → Tool → Model

### 8.4 Cost Optimization Recommendations

**Automatic Suggestions:**

```json
{
  "workflow": "article_writer",
  "current_cost_per_run": 0.002345,
  "recommendations": [
    {
      "type": "model_switch",
      "node": "research",
      "current_model": "gemini-2.0-flash-exp",
      "suggested_model": "gemini-1.5-flash",
      "estimated_savings": 0.0005,
      "savings_percentage": 21.3,
      "quality_impact": "minimal (0.87 → 0.85)",
      "confidence": "high"
    },
    {
      "type": "prompt_optimization",
      "node": "write",
      "issue": "Prompt tokens high (950)",
      "suggestion": "Reduce prompt length by removing examples",
      "estimated_savings": 0.0003,
      "savings_percentage": 12.8,
      "quality_impact": "unknown",
      "confidence": "medium"
    },
    {
      "type": "caching",
      "node": "research",
      "suggestion": "Enable prompt caching for repeated queries",
      "estimated_savings": 0.0002,
      "savings_percentage": 8.5,
      "applicability": "30% of runs",
      "confidence": "medium"
    }
  ],
  "total_potential_savings": 0.0010,
  "total_potential_savings_percentage": 42.6
}
```

### 8.5 Budget Management

**Configuration:**
```yaml
observability:
  mlflow:
    cost_management:
      # Budget alerts
      budget_alerts:
        daily_limit_usd: 1.00
        monthly_limit_usd: 25.00
        alert_threshold: 0.80        # Alert at 80% of limit
        action: warn                 # warn | block

      # Cost thresholds per run
      run_thresholds:
        warn_above_usd: 0.01         # Warn if run > $0.01
        error_above_usd: 0.10        # Error if run > $0.10
        expensive_percentile: 0.95   # Flag top 5% expensive runs

      # Tracking
      track_daily_spend: true
      track_monthly_spend: true
      log_cost_reports: true
```

---

## 9. Dashboard Design

### 9.1 Dashboard Hierarchy

**Level 1: Workflow Overview Dashboard** (Default view)
- Recent runs (table)
- Success/failure rate (pie chart)
- Average cost per run (line chart over time)
- Average duration per run (line chart over time)
- Quality trends (line chart over time)

**Level 2: Run Detail Dashboard** (Click on run)
- Run metadata (status, duration, cost, quality)
- Trace visualization (span hierarchy)
- Node breakdown (table with metrics)
- Cost attribution (pie chart)
- Quality scores (bar chart per node)

**Level 3: Node Detail Dashboard** (Click on node)
- Node execution details
- Prompt preview
- Response preview
- Token usage
- Tool calls (if any)
- Quality assessment (judge scores + rationales)

**Level 4: Analysis Dashboards** (Separate tabs)
- Cost analysis dashboard
- Quality analysis dashboard
- Performance analysis dashboard
- Tool usage dashboard
- Prompt performance dashboard

### 9.2 Workflow Overview Dashboard

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Workflow: article_writer                    [Last 7 days ▼] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │   Success    │ │ Avg Duration │ │   Avg Cost   │         │
│ │     95%      │ │   2.3 min    │ │   $0.0023    │         │
│ │   ↑ 2% vs    │ │   ↓ 15% vs   │ │   ↓ 8% vs    │         │
│ │   last week  │ │   last week  │ │   last week  │         │
│ └──────────────┘ └──────────────┘ └──────────────┘         │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Recent Runs                                             │ │
│ ├──────────┬──────────┬──────────┬──────────┬───────────┤ │
│ │ Run      │ Status   │ Duration │ Cost     │ Quality   │ │
│ ├──────────┼──────────┼──────────┼──────────┼───────────┤ │
│ │ run_123  │ ✅ Success│ 2.1 min  │ $0.0021  │ 0.87 ⭐   │ │
│ │ run_122  │ ✅ Success│ 2.5 min  │ $0.0025  │ 0.82      │ │
│ │ run_121  │ ❌ Failed │ 0.3 min  │ $0.0003  │ N/A       │ │
│ └──────────┴──────────┴──────────┴──────────┴───────────┘ │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Cost Trend (7 days)                                     │ │
│ │                                                         │ │
│ │   $0.003 │                                             │ │
│ │          │       ●                                     │ │
│ │   $0.002 │   ●       ●   ●       ●   ●   ●          │ │
│ │          │                   ●                         │ │
│ │   $0.001 │                                             │ │
│ │          └─────────────────────────────────────────── │ │
│ │           Mon  Tue  Wed  Thu  Fri  Sat  Sun          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌───────────────────────┐ ┌───────────────────────────────┐ │
│ │ Quality Distribution  │ │ Node Performance              │ │
│ │                       │ │                               │ │
│ │  Excellent  ████ 60%  │ │ research  ██ 30% of time     │ │
│ │  Good       ██ 30%    │ │ write     ████████ 70%       │ │
│ │  Acceptable █ 10%     │ │                               │ │
│ └───────────────────────┘ └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Run Detail Dashboard

**Key Sections:**
1. **Run Summary Card** (top)
   - Status, duration, cost, quality, timestamp
   - Quick actions (rerun, export, share)

2. **Trace Visualization** (interactive tree)
   - Expand/collapse spans
   - Hover for details
   - Color-coded by status (success/error)
   - Width proportional to duration

3. **Node Metrics Table**
   - Node ID, duration, tokens, cost, quality
   - Sortable columns
   - Click for node details

4. **Cost Breakdown Chart**
   - Pie chart of cost by node
   - Table with exact values

5. **Quality Assessment Card**
   - Overall quality score
   - Per-node quality scores
   - Judge rationales (expandable)

### 9.4 Interactive Features

**Filters:**
- Date range picker
- Status filter (success/failed)
- Cost range filter
- Quality range filter
- Node ID filter
- Model filter

**Comparisons:**
- Compare 2+ runs side-by-side
- Highlight differences
- Show deltas (cost, quality, duration)

**Exports:**
- Export run data (JSON/CSV)
- Export cost report (CSV)
- Export quality report (PDF)
- Export trace visualization (HTML)

**Search:**
- Full-text search in prompts/responses
- Search by trace ID
- Search by node ID
- Search by error message

---

## 10. Implementation Priorities

### 10.1 Priority Matrix

**Priority 1 (Must Have for v0.1):**
- ✅ Enhanced metrics (automatic + custom)
- ✅ Artifact strategy (minimal/standard/full)
- ✅ Cost summary enhancements
- ✅ Basic trace visualization in MLflow UI

**Priority 2 (Should Have for v0.1):**
- ✅ Tool call tracking and visualization
- ✅ Quality assessment framework (basic)
- ⏸️ LLM judges (built-in judges only)
- ⏸️ Cost optimization recommendations

**Priority 3 (Nice to Have for v0.2):**
- ⏸️ Custom LLM judges
- ⏸️ Prompt registry integration
- ⏸️ Advanced dashboards
- ⏸️ Quality-based workflows (gating, retry)
- ⏸️ Budget management

**Priority 4 (Future, v0.3+):**
- ⏸️ A/B testing framework
- ⏸️ Automatic prompt optimization
- ⏸️ Anomaly detection
- ⏸️ Multi-workflow analytics

### 10.2 Implementation Sequence

**Phase 4.1: Core Migration** (Week 1)
1. Update dependencies (mlflow>=3.9.0)
2. Rewrite MLFlowTracker with autolog
3. Update executor.py integration
4. Basic metrics and artifacts
5. Test suite updates

**Phase 4.2: Enhanced Observability** (Week 2)
6. Enhanced metrics (custom attributes)
7. Artifact level implementation
8. Cost summary enhancements
9. Tool call tracking

**Phase 4.3: Quality Framework** (Week 3, Optional)
10. LLM judge integration (built-in only)
11. Quality assessment framework
12. Quality metrics and artifacts
13. Basic quality dashboards

**Phase 4.4: Documentation & Polish** (Week 4)
14. Update all documentation
15. Create migration guide
16. Performance benchmarking
17. User acceptance testing

### 10.3 Feature Flags for Gradual Rollout

```yaml
observability:
  mlflow:
    # Core features (always on after migration)
    enabled: true
    use_mlflow_39_tracing: true       # MLflow 3.9 vs. legacy
    async_logging: true                # Async trace logging

    # Enhanced features (opt-in)
    enhanced_metrics: true             # Custom span attributes
    tool_call_tracking: true           # Tool usage metrics
    cost_optimization_suggestions: false  # Cost recommendations

    # Quality features (opt-in, v0.2+)
    enable_judges: false               # LLM judge evaluation
    enable_prompt_registry: false      # Prompt versioning

    # Advanced features (opt-in, v0.3+)
    quality_based_workflows: false     # Gating, retry on low quality
    budget_management: false           # Budget alerts and limits
```

---

## Summary & Next Steps

### Phase 3 Complete ✅

This enhanced observability design covers:
- ✅ Enhanced metrics schema (automatic + custom)
- ✅ Artifact strategy (3 levels, detailed schema)
- ✅ LLM judge integration (built-in + custom)
- ✅ Quality assessment framework (scoring, monitoring, workflows)
- ✅ Tool call visualization (metrics, charts, analysis)
- ✅ Prompt versioning strategy (registry integration)
- ✅ Cost analysis enhancements (breakdowns, recommendations)
- ✅ Dashboard design (4-level hierarchy)
- ✅ Implementation priorities (phased approach)

### Key Design Decisions

**1. Progressive Disclosure:**
- Basic features by default
- Advanced features opt-in
- Clear upgrade path

**2. Zero Breaking Changes:**
- All new features additive
- Existing configs work unchanged
- Feature flags for gradual adoption

**3. Practical Priorities:**
- Focus on high-value features first (cost, quality)
- LLM judges optional (v0.2+)
- Prompt registry optional (v0.2+)

**4. Production-Ready:**
- Async logging by default
- Configurable detail levels
- Budget management (optional)

### Ready for Phase 4: Implementation

**Implementation Plan:**
1. **Week 1**: Core migration (MLFlowTracker rewrite, integration)
2. **Week 2**: Enhanced observability (metrics, artifacts, cost)
3. **Week 3**: Quality framework (judges, optional)
4. **Week 4**: Documentation, testing, benchmarking

**Success Criteria:**
- 60% code reduction (484 → 200 lines)
- Zero breaking changes for users
- All tests passing
- Performance overhead < 5%
- Enhanced observability features working

---

*Last Updated: 2026-02-02*
*Phase 3 of T-028: MLFlow 3.9 Comprehensive Migration*
*Status: Design Complete → Ready for Phase 4 (Implementation)*
