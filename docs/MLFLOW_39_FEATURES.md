# MLflow 3.9 Comprehensive Feature Documentation

> **Purpose**: Complete reference for MLflow 3.9 features, capabilities, and best practices
>
> **Created**: 2026-02-02 (Phase 1 of T-028: MLFlow 3.9 Comprehensive Migration)
>
> **Status**: Research Complete - Ready for Migration Planning (Phase 2)

---

## Table of Contents

1. [Overview & Release Highlights](#1-overview--release-highlights)
2. [Core Tracing Features](#2-core-tracing-features)
3. [GenAI Dashboard & Observability](#3-genai-dashboard--observability)
4. [Auto-Instrumentation & Integration](#4-auto-instrumentation--integration)
5. [LLM Judges & Quality Assessment](#5-llm-judges--quality-assessment)
6. [Tool Call Tracking & Visualization](#6-tool-call-tracking--visualization)
7. [OpenTelemetry & Distributed Tracing](#7-opentelemetry--distributed-tracing)
8. [Streaming & Async Support](#8-streaming--async-support)
9. [Prompt Registry & Version Tracking](#9-prompt-registry--version-tracking)
10. [Cost & Token Tracking](#10-cost--token-tracking)
11. [Artifacts & Visualization](#11-artifacts--visualization)
12. [Configuration & Deployment](#12-configuration--deployment)
13. [Performance & Scalability](#13-performance--scalability)
14. [LangGraph-Specific Integration](#14-langgraph-specific-integration)
15. [Error Handling & Debugging](#15-error-handling--debugging)
16. [Python API & Programmatic Usage](#16-python-api--programmatic-usage)
17. [Migration Considerations](#17-migration-considerations)

---

## 1. Overview & Release Highlights

### MLflow 3.9.0 Release (January 15, 2026)

MLflow 3.9 introduces major capabilities for GenAI applications, particularly for evaluation and observation. The release focuses on production-ready observability, automated quality assessment, and enhanced developer experience.

#### Major New Features

**🔮 MLflow Assistant**
- In-product chatbot backed by Claude Code
- Helps identify, diagnose, and fix issues directly from the MLflow UI
- Direct context passing from UI to Claude for intelligent assistance

**📈 Trace Overview Dashboard**
- New "Overview" tab in GenAI experiments
- Pre-built statistics out of the box:
  - Performance metrics (latency, request count)
  - Quality metrics (based on assessments)
  - Tool call summaries
- At-a-glance insights into agent performance

**✨ AI Gateway Revamp**
- Gateway server now integrated directly in tracking server (no separate process)
- Unified interface for LLM API requests
- Route queries to multiple LLM providers
- Additional features:
  - Passthrough endpoints
  - Traffic splits
  - Fallback models

**🔎 Online Monitoring with LLM Judges**
- Configure LLM judges to run automatically on traces
- No code required for basic usage
- Pre-defined judges available
- Custom prompts and instructions for custom metrics

**🤖 Judge Builder UI**
- Define and iterate on custom LLM judge prompts directly from the UI
- Visual prompt engineering for evaluation metrics

**Sources:**
- [MLflow Releases](https://mlflow.org/releases)
- [MLflow 3.8.0 Release Announcement](https://x.com/MLflow/status/2003136230091784683)

---

## 2. Core Tracing Features

### 2.1 The `@mlflow.trace` Decorator

The `mlflow.trace()` decorator provides a simple way to add tracing to any function with minimal effort. It automatically logs function name, inputs, outputs, and execution time.

#### Key Capabilities

- **Automatic parent-child relationship detection** between functions
- **Compatible with auto-tracing** integrations (e.g., `mlflow.openai.autolog`)
- **Exception capture** during function execution
- **Hierarchical trace visualization** in MLflow UI

#### Supported Function Types

| Function Type | Support | Version |
|--------------|---------|---------|
| Sync functions | ✅ | 2.14.0+ |
| Async functions | ✅ | 2.16.0+ |
| Generator functions | ✅ | 2.20.2+ |
| Async generators | ✅ | 2.20.2+ |
| Class methods | ✅ | 3.0.0+ |
| Static methods | ✅ | 3.0.0+ |

#### Customization Parameters

```python
@mlflow.trace(
    name="custom_span_name",           # Override default function name
    span_type="LLM",                   # Set span type (LLM, CHAIN, AGENT, TOOL, etc.)
    attributes={"key": "value"},       # Custom attributes dictionary
    output_reducer=lambda x: x[:10],   # Reduce generator outputs
    trace_destination="experiment_id"  # Destination for trace logging
)
def my_function(input_data):
    # Your function logic
    pass
```

#### Dynamic Attribute Addition

```python
import mlflow

@mlflow.trace
def process_data(data):
    span = mlflow.get_current_active_span()
    span.set_attributes({
        "ai.model.name": "gemini-2.0-flash",
        "ai.model.temperature": 0.7,
        "custom.processing_version": "2.0"
    })
    # Process data...
```

### 2.2 Trace Data Model

MLflow traces are built on OpenTelemetry specs with additional GenAI-specific metadata.

#### Span Structure

Each span contains:
- `span_id`: Unique identifier
- `name`: Human-readable name
- `start_time`: UTC timestamp
- `end_time`: UTC timestamp
- `parent_id`: Parent span ID (if nested)
- `status`: SUCCESS, ERROR, or IN_PROGRESS
- `inputs`: Function inputs (automatically captured)
- `outputs`: Function outputs (automatically captured)
- `attributes`: Custom key-value metadata
- `events`: Notable occurrences during execution (e.g., exceptions)

#### Trace Metadata Fields

- `mlflow.trace.tokenUsage`: Total token usage across entire trace
- `mlflow.chat.tokenUsage`: Token usage for individual LLM calls
- Standard OpenTelemetry fields for compatibility

### 2.3 Manual Tracing API

For fine-grained control beyond the decorator:

```python
import mlflow
from mlflow.tracing import start_span

# Start a trace
with mlflow.start_span(name="my_workflow") as span:
    span.set_attributes({"workflow_type": "data_processing"})

    # Nested span
    with mlflow.start_span(name="preprocessing") as child_span:
        # Your logic
        child_span.set_attribute("records_processed", 1000)
```

**Version Requirements:** MLflow 2.14.0+ for full tracing support

**Sources:**
- [MLflow Tracing Documentation](https://mlflow.org/docs/latest/genai/tracing/)
- [Manual Tracing Guide](https://mlflow.org/docs/3.3.1/genai/tracing/app-instrumentation/manual-tracing/)
- [Introducing MLflow Tracing](https://mlflow.org/blog/mlflow-tracing)
- [Span Concepts](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/span-concepts)

---

## 3. GenAI Dashboard & Observability

### 3.1 Overview Tab (New in 3.9)

The new Overview tab provides comprehensive insights into agent performance at a glance.

#### Pre-Built Metrics

**Performance Metrics:**
- Latency (p50, p95, p99)
- Request count over time
- Success/failure rates
- Throughput (requests per minute)

**Quality Metrics:**
- Assessment scores from LLM judges
- Accuracy metrics
- User feedback aggregation
- Custom metric visualization

**Tool Call Analytics:**
- Tool usage frequency
- Tool call success rates
- Average tool execution time
- Tool call sequences and patterns

### 3.2 Real-Time Trace Viewing

**Auto-Polling Feature:**
- Displays spans from in-progress traces
- Real-time debugging for long-running applications
- No need to wait for trace completion
- Visual progress indicators

### 3.3 Trace Search & Filtering

**Filter Options:**
- User ID
- Time range
- Error status
- Custom tags and metadata
- Prompt/response content search

**Use Cases:**
- Find specific user interactions
- Debug production errors
- Analyze performance patterns
- Compare successful vs failed traces

### 3.4 Production Monitoring

**Real-Time Capabilities:**
- Traces logged automatically to MLflow experiments
- Immediate visibility in MLflow UI
- Async logging for zero-latency impact
- Optional long-term storage in Delta tables

**Sources:**
- [MLflow GenAI](https://mlflow.org/docs/latest/genai/)
- [MLflow Tracing Overview](https://mlflow.org/docs/latest/genai/tracing/)
- [Observe & Analyze Traces](https://mlflow.org/docs/3.1.3/genai/tracing/observe-with-traces/)

---

## 4. Auto-Instrumentation & Integration

### 4.1 LangChain Auto-Instrumentation

**One-Line Activation:**
```python
import mlflow

# Enable automatic tracing for all LangChain components
mlflow.langchain.autolog()

# Now all LangChain executions are automatically traced
from langchain import chains
result = chains.LLMChain(...).invoke(input_data)
# Trace automatically logged to active MLflow experiment
```

#### What Gets Traced Automatically

- **Chains**: All chain executions and intermediate steps
- **LLMs**: All LLM calls with inputs/outputs
- **Agents**: Agent reasoning and action sequences
- **Tools**: Tool invocations and results
- **Prompts**: Prompt templates and filled prompts
- **Retrievers**: Document retrieval operations

#### Token Usage Tracking

**MLflow 3.1.0+:**
- Automatic token usage tracking for LangGraph
- Token usage per LLM call: `mlflow.chat.tokenUsage` span attribute
- Total trace token usage: `mlflow.trace.tokenUsage` metadata field

### 4.2 Supported Auto-Instrumentation Libraries

MLflow provides fully automated integrations that can be activated with a single line:

```python
# OpenAI
mlflow.openai.autolog()

# LangChain
mlflow.langchain.autolog()

# LlamaIndex
mlflow.llamaindex.autolog()

# DSPy
mlflow.dspy.autolog()

# AutoGen
mlflow.autogen.autolog()

# Anthropic
mlflow.anthropic.autolog()
```

### 4.3 Disabling Auto-Instrumentation

```python
# Disable specific library
mlflow.langchain.autolog(disable=True)

# Disable all auto-logging
mlflow.autolog(disable=True)
```

**Sources:**
- [Tracing LangChain](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langchain/)
- [MLflow LangChain Integration](https://python.langchain.com/docs/integrations/providers/mlflow_tracking/)
- [Automatic Tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/)
- [MLflow Langchain Autologging](https://mlflow.org/docs/latest/genai/flavors/langchain/autologging/)

---

## 5. LLM Judges & Quality Assessment

### 5.1 Overview

LLM-as-a-Judge is an evaluation approach that uses Large Language Models to assess the quality of AI-generated responses. This is more scalable and cost-effective than human evaluation while capturing subjective qualities like helpfulness and safety.

### 5.2 Scorers Framework

Scorers provide a unified interface to define evaluation criteria for models, agents, and applications. The same scorer can be used for:
- **Development evaluation** (pre-deployment)
- **Production monitoring** (post-deployment)

This ensures consistency throughout the application lifecycle.

### 5.3 Types of Scorers

#### 1. Built-In LLM Judges

MLflow provides research-validated judges for common use cases:
- **Helpfulness**: Is the response helpful to the user?
- **Harmfulness**: Does the response contain harmful content?
- **Relevance**: Is the response relevant to the query?
- **Coherence**: Is the response logically consistent?
- **Groundedness**: Is the response grounded in provided context?

#### 2. Guidelines-Based Judges

Define plain-language rules that refer to specific inputs or outputs:

```python
from mlflow.metrics.genai import guidelines_based_judge

# Define guidelines
guidelines = [
    "The response must be polite and professional",
    "The response must directly answer the user's question",
    "The response must be under 200 words"
]

# Create judge
judge = guidelines_based_judge(
    guidelines=guidelines,
    model="openai:/gpt-4o-mini",
    name="politeness_check"
)
```

The LLM determines if guidelines pass/fail and provides a rationale.

#### 3. Custom Code-Based Scorers

Ultimate flexibility for business-specific metrics:

```python
def custom_scorer(prediction, context):
    """Custom business logic for evaluation"""
    # Implement your custom logic
    score = calculate_business_metric(prediction, context)
    return {
        "score": score,
        "justification": "Rationale for the score"
    }
```

### 5.4 Online Monitoring (New in 3.9)

**Zero-Code Configuration:**
- Configure LLM judges to run automatically on traces
- No code changes required
- Access through "Judges" tab in GenAI Experiment UI

**Options:**
- Use pre-defined judges
- Provide custom prompts and instructions
- Set up automated quality assessment pipelines

### 5.5 Judge Builder UI (New in 3.9)

- Define custom LLM judge prompts directly from the UI
- Iterate on prompts visually
- Test prompts against sample data
- Deploy judges without writing code

### 5.6 Model Selection

**Default Judge Model:**
- OpenAI GPT-4o-mini (default)

**Custom Judge Models:**
```python
judge = guidelines_based_judge(
    guidelines=guidelines,
    model="anthropic:/claude-3-sonnet",  # Format: <provider>:/<model-name>
    name="custom_judge"
)
```

**Sources:**
- [Evaluating LLMs/Agents with MLflow](https://mlflow.org/docs/latest/genai/eval-monitor/)
- [LLM as Judge](https://mlflow.org/blog/llm-as-judge)
- [Scorers and LLM Judges](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)
- [LLM-based Scorers](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/)

---

## 6. Tool Call Tracking & Visualization

### 6.1 Capabilities

MLflow captures and visualizes function calls in agent-based systems:

- **Function Availability**: What functions are available to the agent
- **Function Invocations**: Which functions are called
- **Inputs & Outputs**: Arguments and return values for each call
- **Call Sequences**: Order and relationships between tool calls

### 6.2 Tool Call Analytics (New in 3.9)

**Overview Tab Metrics:**
- Tool usage frequency distribution
- Tool call success rates
- Tool call summaries and patterns

**Built-In Scorer:**
- Evaluates tool call efficiency in multi-turn interactions
- Detects redundant calls
- Identifies missing batching opportunities
- Flags poor tool selections

### 6.3 Supported Platforms

**Automatic Tool Tracking:**

**OpenAI Agents SDK:**
- Captures agent-to-agent interactions
- Logs OpenAI API calls
- Visualizes multi-agent communication

**Anthropic:**
- Automatic tracing via `mlflow.anthropic.autolog()`
- Tool use tracking for Claude models

**LangChain/LangGraph:**
- Comprehensive tool tracking
- Captures chains, agents, tools, prompts
- Full execution trace visualization

### 6.4 Implementation Example

```python
import mlflow

# Enable auto-tracing
mlflow.langchain.autolog()

# Define tools
from langchain.tools import Tool

def search_tool(query):
    # Tool implementation
    return results

# Agent automatically logs tool calls
agent = create_agent(tools=[search_tool])
agent.invoke({"input": "Search for AI trends"})
# Tool calls automatically tracked and visualized
```

**Sources:**
- [Tracing OpenAI Agent](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai-agent/)
- [Tracing OpenAI](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai/)
- [Tracing Anthropic](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/anthropic/)
- [MLflow Tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/)

---

## 7. OpenTelemetry & Distributed Tracing

### 7.1 Full OpenTelemetry Integration (MLflow 3.6.0+)

MLflow Tracing is built on OpenTelemetry SDK and designed for minimal instrumentation effort.

#### Key Features

**OTLP Endpoint:**
- MLflow Server exposes OTLP endpoint at `/v1/traces`
- Accepts traces from any OpenTelemetry-instrumented application
- Supports applications in any language (Java, Go, Rust, Python, etc.)

**Automatic Integration:**
- Integrates with OpenTelemetry's default tracer provider
- Spans from different instrumentation sources combine into cohesive traces
- No manual correlation required

### 7.2 Distributed Tracing

**Trace Context Propagation:**
- Propagate trace context across different services and processes
- Track request lifecycles end-to-end
- Unified view of distributed systems

**Cross-Service Tracing:**
```python
import mlflow
from opentelemetry import trace

# Service A creates trace
with mlflow.start_span(name="service_a") as span:
    context = span.get_context()
    # Pass context to Service B (e.g., via HTTP headers)

# Service B continues trace
with mlflow.start_span(name="service_b", parent=context):
    # Processing in Service B
    pass
```

### 7.3 Dual Export Mode

Send traces to multiple destinations simultaneously:

```python
import mlflow

# Configure dual export
mlflow.tracing.set_destination(
    destinations=[
        "mlflow",  # MLflow Tracking Server
        "otel://collector:4317"  # OpenTelemetry Collector
    ]
)
```

**Benefits:**
- Leverage MLflow's GenAI-specific features
- Maintain existing observability infrastructure
- No need to choose between platforms

### 7.4 Span-Level Metrics Export

**MLflow 2025-2026 Enhancement:**
- Exports span-level statistics as OpenTelemetry metrics
- Enhanced observability and monitoring
- Compatible with existing OTEL metric pipelines

### 7.5 Compatibility

**Span Object:**
- Compatible with OpenTelemetry Span spec
- Additional convenience accessors for GenAI use cases
- Dataclass structure similar to OTEL Span

**Sources:**
- [Full OpenTelemetry Support](https://mlflow.org/blog/opentelemetry-tracing-support)
- [OpenTelemetry Integration](https://mlflow.org/docs/latest/genai/tracing/opentelemetry/)
- [Tracing with OpenTelemetry](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/opentelemetry/)
- [Tracing Data Model](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/data-model)

---

## 8. Streaming & Async Support

### 8.1 Real-Time Streaming Traces

**In-Progress Trace Display:**
- Traces UI supports displaying spans from in-progress traces
- Auto-polling for real-time updates
- Monitor long-running LLM applications without waiting for completion
- Real-time debugging capabilities

### 8.2 Async Trace Logging

**Zero-Latency Production Logging:**

```python
import os

# Configure async logging
os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "true"
os.environ["MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS"] = "20"
os.environ["MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE"] = "2000"
os.environ["MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT"] = "600"

import mlflow

# Tracing now happens in background
@mlflow.trace
def my_llm_function(input):
    # Application logic
    pass
```

**Benefits:**
- Trace logging doesn't block application execution
- Critical for production performance
- Configurable queue size and worker pools

### 8.3 Async Function Support

**The `@mlflow.trace` decorator works seamlessly with async functions:**

```python
import mlflow
import asyncio

@mlflow.trace
async def async_llm_call(prompt):
    # Async operations traced normally
    response = await llm.agenerate(prompt)
    return response

# Works with async generators too
@mlflow.trace
async def async_generator():
    for i in range(10):
        yield await process_item(i)
```

### 8.4 Concurrent Traces & Multi-Threading

**Thread-Safe Tracing:**

```python
import mlflow
from concurrent.futures import ThreadPoolExecutor
import contextvars

@mlflow.trace
def worker_function(data):
    # Process data
    return result

# Use context copying for proper trace combination
def run_concurrent():
    with ThreadPoolExecutor() as executor:
        context = contextvars.copy_context()
        futures = [
            executor.submit(context.run, worker_function, item)
            for item in data_items
        ]
        results = [f.result() for f in futures]
```

**Context-Local Destinations:**

```python
# Set destination per async task or thread
mlflow.tracing.set_destination(
    destination="mlflow",
    context_local=True  # Enables per-task/thread isolation
)
```

### 8.5 Batch Span Export

**MLflow 3.6.0+ Feature:**
- Batch span export to Unity Catalog tables
- Efficient for high-volume applications
- Reduces network overhead

### 8.6 Job Execution Backend (New in 3.5.0+)

**Asynchronous Task Management:**
- Individual execution pools for different job types
- Job search capabilities
- Transient error handling and retry logic
- Better resource management for async operations

**Sources:**
- [MLflow Tracing FAQ](https://mlflow.org/docs/latest/genai/tracing/faq/)
- [Production Monitoring](https://mlflow.org/docs/latest/genai/tracing/prod-tracing/)
- [Lightweight Tracing SDK](https://mlflow.org/docs/latest/genai/tracing/lightweight-sdk/)

---

## 9. Prompt Registry & Version Tracking

### 9.1 MLflow Prompt Registry

A powerful tool that streamlines prompt engineering and management in GenAI applications.

**Key Benefits:**
- Version and track prompts across organization
- Maintain consistency in prompt usage
- Improve collaboration in prompt development
- Enable reproducibility across experiments

### 9.2 Immutable Versioning

**Git-Inspired Version Control:**
- Commit-based versioning
- Track prompt evolution over time
- Side-by-side comparison with diff highlighting
- **Prompt versions are immutable** → strong reproducibility guarantees

### 9.3 Integration with Experiments

**Automatic Lineage Tracking:**

```python
import mlflow

# Set active model with prompt from registry
mlflow.set_active_model(
    model_uri="models:/my-model/1",
    prompt_uri="prompts:/my-prompt/3"
)

# MLflow automatically creates lineage between:
# - Prompt version 3
# - Model version 1
# - Current experiment run
```

**Track Together:**
- Prompt changes
- Application configurations
- Model versions
- Experiment parameters

### 9.4 Recent Updates (MLflow 3.7.0)

**New Prompts Functionality in Experiment UI:**
- Manage prompts directly within experiments
- Search prompts with filter strings
- Prompt version search in traces
- Unified workflow for prompts and experiments

### 9.5 Prompt Management Workflow

```python
from mlflow.prompts import create_prompt, get_prompt

# Create new prompt
prompt = create_prompt(
    name="article_writer_system_prompt",
    template="You are a helpful AI assistant. Write an article about {topic}.",
    parameters=["topic"]
)

# Retrieve prompt by version
prompt_v2 = get_prompt(name="article_writer_system_prompt", version=2)

# Use in application
filled_prompt = prompt_v2.format(topic="AI Safety")
```

**Sources:**
- [Version Tracking Quickstart](https://mlflow.org/docs/latest/genai/version-tracking/quickstart/)
- [Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/)
- [Version Tracking for GenAI](https://mlflow.org/docs/latest/genai/version-tracking/)
- [Track Prompt Versions](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/track-prompts-app-versions)

---

## 10. Cost & Token Tracking

### 10.1 Token Usage Tracking

**Automatic Token Capture:**
- MLflow Tracing captures token usage at each step
- Per-call metrics: `mlflow.chat.tokenUsage` span attribute
- Total trace metrics: `mlflow.trace.tokenUsage` metadata field

**Supported Frameworks (MLflow 3.4.0+):**
- LangGraph
- LangChain
- OpenAI
- Anthropic
- Other agent SDKs

### 10.2 Cost Management Features

**Token Consumption Analysis:**
- Understand token usage patterns
- Identify optimization opportunities
- Track costs across different models
- Compare efficiency of different approaches

**Latency + Cost Correlation:**
- Combined view of performance and cost
- Identify expensive operations
- Optimize for cost-effectiveness

### 10.3 Cost Economics Considerations

**Key Factors:**
- Token usage varies by user behavior
- Model selection impacts costs significantly
- Multiple LLM calls can accumulate quickly
- Trace data enables pattern identification

### 10.4 Implementation Example

```python
import mlflow

mlflow.langchain.autolog()  # Enables automatic token tracking

# Run workflow
result = agent.invoke(input_data)

# Token usage automatically logged
# Access via trace metadata:
trace = mlflow.get_trace(trace_id)
total_tokens = trace.info.token_usage
# Returns: {"prompt_tokens": 150, "completion_tokens": 500, "total_tokens": 650}
```

### 10.5 Cost Tracking Benefits

- **Free & Open Source**: MLflow is 100% free, no SaaS costs
- **Real-Time Monitoring**: Track costs as they occur
- **Historical Analysis**: Compare costs across experiments
- **Budget Management**: Set alerts and thresholds

**Sources:**
- [MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing/)
- [MLflow Tracing - GenAI Observability](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/)
- [Understanding Cost Economics of GenAI Systems](https://medium.com/@AI-on-Databricks/understanding-the-cost-economics-of-genai-systems-a-comprehensive-guide-24e3d4f22e4f)

---

## 11. Artifacts & Visualization

### 11.1 MLflow Artifact System

**Artifact Types:**
- Trained model weights
- Visualizations (charts, graphs, plots)
- Evaluation reports
- Processed data subsets
- Configuration files
- Custom output files

### 11.2 Logging Visualizations

**Seamless Integration:**
```python
import mlflow
import matplotlib.pyplot as plt

# Create visualization
fig, ax = plt.subplots()
ax.plot(metrics_over_time)

# Log to MLflow
mlflow.log_figure(fig, "metrics_plot.png")
```

**Supported Formats:**
- Images: `.jpg`, `.png`, `.svg`
- Interactive: `.html`, `.geojson`
- Text: `.txt`, `.log`, `.py`, etc.

### 11.3 Artifact Viewer

**Built-In Rendering:**
- Text files displayed with syntax highlighting
- Images rendered inline
- HTML files rendered interactively
- Embedded dashboards via HTML

**Quick Access:**
- Figures displayable in Runs view pane
- No need to download files
- Fast analysis and review workflow

### 11.4 Dashboard Building

**MLflow Python Client for Dashboards:**
```python
from mlflow import MlflowClient

client = MlflowClient()

# Query runs for dashboard data
runs = client.search_runs(
    experiment_ids=["1"],
    filter_string="metrics.accuracy > 0.9"
)

# Build dashboard visualizations
# - Metric changes over time
# - Run count by user
# - Performance comparisons
```

**Integration Options:**
- Custom dashboards with MLflow Python API
- Third-party tools (Metabase, etc.)
- Databricks workspace dashboards
- HTML embedded dashboards

### 11.5 Dashboard Use Cases

- Visualize metric changes over time
- Track number of runs by user
- Compare model performance
- Monitor production metrics
- Analyze experiment results

**Sources:**
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)
- [Logging Visualizations](https://mlflow.org/docs/latest/ml/traditional-ml/tutorials/hyperparameter-tuning/notebooks/logging-plots-in-mlflow)
- [Build Dashboards](https://docs.databricks.com/aws/en/mlflow/build-dashboards)
- [Logging Artifacts](https://apxml.com/courses/data-versioning-experiment-tracking/chapter-3-tracking-experiments-mlflow/logging-artifacts-mlflow)

---

## 12. Configuration & Deployment

### 12.1 Core Environment Variables

**Tracking Configuration:**
```bash
# Tracking server URI (required for most commands)
export MLFLOW_TRACKING_URI="http://localhost:5000"

# Or use SQLite backend
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
```

**Deployment Configuration:**
```bash
# AI Gateway config file path
export MLFLOW_DEPLOYMENTS_CONFIG="/path/to/config.yaml"

# AI Gateway instance URI
export MLFLOW_DEPLOYMENTS_TARGET="http://gateway:5000"

# Deployment flavor
export MLFLOW_DEPLOYMENT_FLAVOR_NAME="python_function"

# Timeouts
export MLFLOW_DEPLOYMENT_PREDICT_TIMEOUT="30"
export MLFLOW_DEPLOYMENT_PREDICT_TOTAL_TIMEOUT="300"
```

**Tracing Configuration:**
```bash
# Async logging
export MLFLOW_ENABLE_ASYNC_TRACE_LOGGING="true"
export MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS="20"
export MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE="2000"
export MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT="600"

# Trace timeout
export MLFLOW_TRACE_TIMEOUT_SECONDS="300"
```

### 12.2 SQLite Backend (Now Default)

**Automatic SQLite Usage:**
- SQLite is now the default backend store
- Automatically creates `sqlite:///mlflow.db` if not specified
- No configuration needed for local development

**Filesystem Backend Deprecation:**
```bash
# OLD (deprecated): File store
export MLFLOW_TRACKING_URI="./mlruns"

# NEW (recommended): SQLite
export MLFLOW_TRACKING_URI="sqlite:///mlruns.db"
```

**Automatic Fallback:**
- Existing users: If `./mlruns` exists with data, MLflow continues using file store
- New users: Automatically uses SQLite backend
- Graceful migration path for existing projects

**Why SQLite?**
- Better performance and reliability
- Receives new feature updates
- File system backend in Keep-the-Light-On (KTLO) mode

### 12.3 Deployment Best Practices

**Security:**
- Avoid hardcoding sensitive information
- Use environment variables for secrets
- Leverage secret management services (Azure Key Vault, AWS Secrets Manager)

**Azure ML Integration:**
```bash
# Certificate-based authentication
export AZURE_CLIENT_CERTIFICATE_PATH="/path/to/cert.pem"
export AZURE_CLIENT_CERTIFICATE_PASSWORD="password"
```

**Container Configuration:**
- MLflow propagates environment variables to Docker containers
- Variables appended to container environment in Kubernetes
- Consistent configuration across deployment targets

**Sources:**
- [MLflow Environment Variables](https://mlflow.org/docs/latest/python_api/mlflow.environment_variables.html)
- [MLflow CLI](https://mlflow.org/docs/latest/cli.html)
- [Configure MLflow for Azure](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-use-mlflow-configure-tracking)
- [Backend Stores](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/)

---

## 13. Performance & Scalability

### 13.1 Storage Optimization

**Parquet vs CSV:**
- Switching to Parquet saves ~10x storage
- Columnar format provides performance benefits
- Recommended for large-scale deployments

### 13.2 Distributed Training

**Large-Scale Model Training:**
- MLflow supports distributed training workflows
- Critical for deep learning workloads
- Integrates with Apache Spark for scalability

**Framework Support:**
- TensorFlow
- PyTorch
- Spark MLlib
- Other popular ML libraries

### 13.3 Hyperparameter Tuning

**Best Practices:**
- Tune entire ML pipeline, not isolated modules
- Leverage different hyperparameter combinations
- Track and analyze via MLflow Tracking API
- Use centralized storage for experiments

**MLflow Projects:**
- Use for reusability and modularity
- Streamlines model development
- Enables reproducible experiments

### 13.4 Scalability Architecture

**Databricks MLflow:**
- Combines open-source MLflow with enterprise infrastructure
- Built on Apache Spark's distributed computing
- Excels for data-heavy organizations
- Unified analytics and ML across massive datasets

**Key Capabilities:**
- Comprehensive experiment tracking
- Model registry for sharing and management
- Deployment capabilities
- Support for teams and organizations

### 13.5 CI/CD Integration

**Automation Tools:**
- GitHub Actions
- Jenkins
- MLflow native support

**CI/CD Benefits:**
- Automated workflows from code to production
- Model retraining pipelines
- Testing changes automatically
- Minimal downtime deployments

### 13.6 2026 Trends & Market

**MLOps Growth:**
- Market reached $1.7B in 2024
- Projected to reach $129B by 2034
- Urgent need for scalable AI infrastructure

**Infrastructure Focus:**
- Automated pipelines for retraining
- Continuous testing and deployment
- Performance monitoring at scale

### 13.7 Performance Tips

**For High-Volume Applications:**
1. Enable async trace logging
2. Use batch span export (3.6.0+)
3. Configure appropriate worker pool sizes
4. Set reasonable queue sizes
5. Use Parquet for artifact storage
6. Leverage distributed computing (Spark)

**Model Registry Optimization:**
- Link only performant models to production stage
- Use metadata for filtering
- Implement model versioning strategy
- Automate model promotion workflows

**Sources:**
- [Machine Learning Tech Stack 2026](https://www.spaceo.ai/blog/machine-learning-tech-stack/)
- [MLflow Best Practices](https://cast.ai/blog/7-infra-best-practices-for-running-mlflow-cost-effectively-for-cloud-based-ai-models/)
- [MLflow Mastery Guide](https://www.kdnuggets.com/mlflow-mastery-a-complete-guide-to-experiment-tracking-and-model-management)
- [MLOps Best Practices](https://cloud.folio3.com/blog/mlops-best-practices/)

---

## 14. LangGraph-Specific Integration

### 14.1 Overview

LangGraph is an open-source library for building stateful, multi-actor applications with LLMs. MLflow provides automatic tracing as an extension of its LangChain integration.

### 14.2 Automatic Tracing Setup

```python
import mlflow

# Enable auto-tracing for LangChain (includes LangGraph)
mlflow.langchain.autolog()

# Now all LangGraph executions are automatically traced
from langgraph.graph import StateGraph

# Build and execute graph
graph = StateGraph(state_schema)
# ... configure nodes and edges ...
compiled_graph = graph.compile()

# Execution automatically traced
result = compiled_graph.invoke(initial_state)
# Trace logged to active MLflow experiment
```

### 14.3 State Management Tracking

**Manual Spans for State Transitions:**

```python
import mlflow
from langgraph.graph import StateGraph

def my_node(state):
    # Create manual span to track state details
    with mlflow.start_span(name="process_node") as span:
        span.set_attributes({
            "state.messages": len(state["messages"]),
            "state.iteration": state["iterations"],
            "state.generation": state.get("generation", "N/A")
        })

        # Process state
        new_state = process(state)
        return new_state

# Configure graph with traced node
graph = StateGraph(GraphState)
graph.add_node("process", my_node)
```

### 14.4 Token Usage Tracking

**MLflow 3.1.0+ for LangGraph:**
- Token usage for each LLM call: `mlflow.chat.tokenUsage` span attribute
- Total usage for entire graph execution: `mlflow.trace.tokenUsage` metadata
- Automatic tracking, no manual instrumentation needed

### 14.5 Installation Requirements

```bash
# Install MLflow with LangGraph support
pip install mlflow>=3.0.0
pip install langgraph
pip install langchain_core
pip install langchain_openai  # or other LangChain integrations
```

**Recommendation:** MLflow 3+ highly recommended for best tracing experience

### 14.6 What Gets Traced

**Automatic Capture:**
- Graph execution start and completion
- Node executions (entry and exit)
- State transitions between nodes
- LLM calls within nodes
- Tool calls within nodes
- Errors and exceptions
- Execution timing and latency

**Visualization:**
- Graph structure in MLflow UI
- Node-by-node execution flow
- State changes over time
- LLM interactions per node

### 14.7 Use Cases

**Development:**
- Debug complex graph workflows
- Understand state propagation
- Identify performance bottlenecks
- Validate graph logic

**Production:**
- Monitor graph execution in real-time
- Track token usage and costs
- Analyze failure patterns
- Assess quality of graph outputs

### 14.8 Best Practices

1. **Enable autolog early:** Call `mlflow.langchain.autolog()` before graph creation
2. **Use manual spans for state:** Add custom spans to track important state transitions
3. **Log artifacts:** Save graph diagrams and state snapshots as artifacts
4. **Tag experiments:** Use tags to identify different graph configurations
5. **Monitor token usage:** Track costs across graph iterations

**Sources:**
- [Tracing LangGraph](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langgraph/)
- [LangGraph Model From Code](https://mlflow.org/blog/langgraph-model-from-code)
- [Tracing and Evaluating LangGraph Agents](https://www.advancinganalytics.co.uk/blog/tracing-and-evaluating-langgraph-ai-agents-with-mlflow)
- [MLflow LangChain Integration](https://python.langchain.com/docs/integrations/providers/mlflow_tracking/)

---

## 15. Error Handling & Debugging

### 15.1 MLflow Assistant (New in 3.9)

**AI-Powered Debugging:**
- In-product chatbot backed by Claude Code
- Identifies, diagnoses, and fixes issues
- Direct context passing from MLflow UI to Claude
- Intelligent assistance based on trace data

### 15.2 Exception Capture

**Automatic Exception Tracking:**
- Exceptions raised during traced operations are automatically captured
- Indication shown in MLflow UI
- Partial data capture available for debugging
- Exception details in span `events` attribute

**Example:**
```python
@mlflow.trace
def risky_function(data):
    try:
        result = process(data)
        return result
    except ValueError as e:
        # Exception automatically captured by MLflow
        # Available in trace for debugging
        raise
```

### 15.3 Trace Timeout

**Preventing Hung Traces:**
```bash
# Set timeout for traces
export MLFLOW_TRACE_TIMEOUT_SECONDS="300"  # 5 minutes
```

**Behavior:**
- If timeout exceeded, MLflow automatically halts trace
- Trace exported with ERROR status
- Available for analysis (not lost)
- Helps identify hung operations

### 15.4 Real-Time Debugging (New in 3.9)

**In-Progress Trace Display:**
- Traces UI displays spans from in-progress traces
- Auto-polling for real-time updates
- Debug long-running applications without waiting
- Visual progress indicators

**Use Cases:**
- Monitor LLM calls as they happen
- Identify slow operations in real-time
- Debug production issues without reproduction
- Understand user experience as it occurs

### 15.5 Search & Filter for Debugging

**Quick Issue Location:**
```python
from mlflow import MlflowClient

client = MlflowClient()

# Find traces with errors
error_traces = client.search_traces(
    experiment_ids=["1"],
    filter_string="status = 'ERROR'"
)

# Filter by user ID
user_traces = client.search_traces(
    experiment_ids=["1"],
    filter_string="tags.user_id = 'user123'"
)

# Search by content
prompt_traces = client.search_traces(
    experiment_ids=["1"],
    filter_string="input LIKE '%specific prompt%'"
)
```

**Filter Dimensions:**
- User ID
- Time range
- Error status
- Custom tags
- Prompt/response content
- Specific metadata values

### 15.6 Job Execution Backend (3.5.0+)

**Transient Error Handling:**
- Individual execution pools for different job types
- Automatic retry logic for transient errors
- Job search capabilities for debugging
- Better resource management

### 15.7 Debugging Best Practices

1. **Rich Context:** Add tags and metadata to all traces
2. **Custom Attributes:** Set meaningful span attributes for debugging
3. **Structured Logging:** Use consistent naming conventions
4. **Error Context:** Include relevant state in error messages
5. **Timeout Configuration:** Set appropriate timeouts for operations
6. **Async Logging:** Use async logging for high-volume apps (doesn't impact debugging)

**Sources:**
- [MLflow Releases](https://mlflow.org/releases)
- [Tracing FAQ](https://mlflow.org/docs/latest/genai/tracing/faq/)
- [Observe & Analyze Traces](https://mlflow.org/docs/3.1.3/genai/tracing/observe-with-traces/)
- [Production Monitoring](https://mlflow.org/docs/latest/genai/tracing/prod-tracing/)

---

## 16. Python API & Programmatic Usage

### 16.1 API Structure

MLflow provides two complementary API levels:

#### Fluent API (High-Level)
- Top-level `mlflow` module
- Easy to use for common tasks
- Context-based (active run concept)
- Now thread-safe and multi-process safe (recent improvement)

#### Client API (Lower-Level)
- `mlflow.client` module
- Python CRUD interface to MLflow
- Direct translation to MLflow REST API
- Fine-grained control

**Use Together:**
- Imperative APIs work in conjunction with fluent APIs
- Choose based on use case complexity

### 16.2 Thread Safety Improvements

**Historical Limitation:**
> The fluent tracking API is not currently threadsafe. Any concurrent callers to the tracking API must implement mutual exclusion manually.

**Recent Enhancement:**
- Fluent APIs overhauled for thread and multi-process safety
- No longer need Client APIs for concurrent applications
- Can use fluent API in multiprocessing and threaded applications

### 16.3 Fluent API Examples

```python
import mlflow

# Start experiment
mlflow.set_experiment("my_experiment")

# Start run (context manager)
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("learning_rate", 0.01)

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)

    # Log artifacts
    mlflow.log_artifact("model.pkl")

    # Log model
    mlflow.sklearn.log_model(model, "model")

# Tracing
@mlflow.trace
def my_function(input_data):
    return process(input_data)
```

### 16.4 Client API Examples

```python
from mlflow import MlflowClient

client = MlflowClient()

# Create experiment
experiment_id = client.create_experiment("my_experiment")

# Create run
run = client.create_run(experiment_id)

# Log to run
client.log_param(run.info.run_id, "learning_rate", 0.01)
client.log_metric(run.info.run_id, "accuracy", 0.95)

# Search runs
runs = client.search_runs(
    experiment_ids=[experiment_id],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.accuracy DESC"]
)

# Get traces
traces = client.search_traces(
    experiment_ids=[experiment_id],
    filter_string="status = 'SUCCESS'"
)

# Model registry operations
client.create_registered_model("my_model")
client.create_model_version(
    name="my_model",
    source="runs:/<run_id>/model",
    run_id=run.info.run_id
)
```

### 16.5 Tracing API

```python
import mlflow
from mlflow.tracing import start_span, get_current_active_span

# Manual span creation
with mlflow.start_span(name="my_operation") as span:
    span.set_attributes({
        "operation_type": "data_processing",
        "records_count": 1000
    })

    # Nested span
    with mlflow.start_span(name="preprocessing"):
        preprocess_data()

    # Get current span
    current = get_current_active_span()
    current.set_attribute("status", "completed")

# Decorator-based tracing
@mlflow.trace(
    name="custom_name",
    span_type="LLM",
    attributes={"model": "gemini-2.0"}
)
def llm_call(prompt):
    return model.generate(prompt)
```

### 16.6 Registry Client

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Register model
client.create_registered_model(
    name="article_writer_v1",
    description="Article writing agent"
)

# Create version
version = client.create_model_version(
    name="article_writer_v1",
    source="runs:/abc123/model",
    run_id="abc123"
)

# Transition stage
client.transition_model_version_stage(
    name="article_writer_v1",
    version=version.version,
    stage="Production"
)

# Search models
models = client.search_registered_models(
    filter_string="name LIKE 'article_%'"
)
```

### 16.7 Context Management

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Set experiment
mlflow.set_experiment("my_experiment")

# Set tags
mlflow.set_tags({
    "team": "ml_platform",
    "environment": "production"
})

# Nested runs
with mlflow.start_run(run_name="parent"):
    mlflow.log_param("experiment_type", "hyperparameter_tuning")

    # Child runs
    for i in range(5):
        with mlflow.start_run(run_name=f"child_{i}", nested=True):
            mlflow.log_param("iteration", i)
            mlflow.log_metric("score", train_iteration(i))
```

**Sources:**
- [MLflow Python API](https://mlflow.org/docs/latest/python_api/mlflow.html)
- [MLflow Client API](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.client.html)
- [Python API Index](https://mlflow.org/docs/latest/python_api/index.html)
- [MLflow Fluent Module](https://github.com/mlflow/mlflow/blob/master/mlflow/tracking/fluent.py)

---

## 17. Migration Considerations

### 17.1 MLflow 2.x to 3.0+ Migration

**Good News:**
> Migration from MLflow 2.x to 3.0 is very straightforward and should require minimal code changes in most cases.

**Core Concepts Remain:**
- Experiments and runs unchanged
- Metadata (parameters, tags, metrics) unchanged
- Backward compatible in most areas

### 17.2 Database Schema Updates

**Required Before Upgrading:**

```bash
# Upgrade database schema
mlflow db upgrade

# Then restart MLflow server with new version
```

**Rolling Upgrades:**
- Upgrade servers gradually
- Use load balancer to route traffic
- Old servers → New servers gradually
- Minimizes downtime

### 17.3 Major Changes in MLflow 3

#### 1. Models as First-Class Citizens

**Before (MLflow 2.x):**
```python
with mlflow.start_run():
    mlflow.sklearn.log_model(model, "model")  # Required active run
```

**After (MLflow 3.0+):**
```python
# No active run required
mlflow.sklearn.log_model(
    model,
    "model",
    registered_model_name="my_model"
)
```

#### 2. Model Registry Webhooks

- Support for webhooks on model registry events
- Enables automated workflows
- Trigger actions on model transitions

#### 3. Evaluation API Changes

**Removed:**
- `baseline_model` parameter
- `custom_metrics` parameter

**Migration:**
- Use new evaluation patterns
- Check documentation for new API

#### 4. MLflow Recipes Removed

**Alternative:**
- Use standard MLflow tracking directly
- Consider MLflow Projects for workflow management
- More flexibility with direct API usage

#### 5. AI Gateway Configuration Changes

**Removed:**
- `routes` config key
- `route_type` config key

**New Structure:**
- Simplified configuration format
- Gateway integrated into tracking server (3.9.0)

### 17.4 Version Compatibility

**Server-Client Compatibility:**
- Tracking server works with older SDK versions
- Up to one major version difference supported
- Example: MLflow 2.x client works with 3.x server

**Recommendation:**
- Keep server and clients reasonably synchronized
- Test compatibility in staging environment

### 17.5 Filesystem to SQLite Migration

**Automatic Migration:**
- Existing `./mlruns` data continues to work
- MLflow detects existing data automatically
- No manual migration needed for file store users

**New Projects:**
- Automatically use SQLite backend
- Better performance and features
- File store in maintenance mode

**Manual Migration (Optional):**
```python
from mlflow.store.tracking.file_store import FileStore
from mlflow.store.tracking.sqlalchemy_store import SqlAlchemyStore

# Export from file store
file_store = FileStore("./mlruns")
experiments = file_store.list_experiments()

# Import to SQLite
sql_store = SqlAlchemyStore("sqlite:///mlflow.db")
for exp in experiments:
    sql_store.create_experiment(exp.name, exp.artifact_location)
    # Migrate runs, metrics, params, etc.
```

### 17.6 GenAI Features (MLflow 3+)

**New in MLflow 3:**
- GenAI primitives for experiment tracking
- Tracing infrastructure (2.14.0+, enhanced in 3.x)
- Prompt registry
- LLM judges and evaluation
- Token-cost management

**Adoption Strategy:**
- Incremental adoption possible
- Core tracking unchanged
- Add tracing when ready
- Enable auto-logging for GenAI libs

### 17.7 Breaking Changes Checklist

Before upgrading, review:
- [ ] Database schema upgrade command run
- [ ] Evaluation API usage (if using baselines or custom metrics)
- [ ] MLflow Recipes usage (migrate to Projects or direct API)
- [ ] AI Gateway configuration format
- [ ] Model logging patterns (can now skip active run)
- [ ] Client version compatibility
- [ ] Test in staging environment

### 17.8 Migration Resources

**Official Guides:**
- [MLflow 3 Migration Guide](https://mlflow.org/docs/latest/ml/mlflow-3/)
- [Breaking Changes in MLflow 3](https://mlflow.org/docs/latest/genai/mlflow-3/breaking-changes/)
- [Upgrade Documentation](https://mlflow.org/docs/latest/self-hosting/migration/)

**Community Support:**
- [GitHub Discussions](https://github.com/mlflow/mlflow/discussions)
- [GitHub Issues](https://github.com/mlflow/mlflow/issues)

**Sources:**
- [MLflow 3 Migration Guide](https://mlflow.org/docs/latest/ml/mlflow-3/)
- [Breaking Changes](https://mlflow.org/docs/latest/genai/mlflow-3/breaking-changes/)
- [Upgrade Documentation](https://mlflow.org/docs/latest/self-hosting/migration/)
- [Database Migrations README](https://github.com/mlflow/mlflow/blob/master/mlflow/store/db_migrations/README.md)

---

## Summary & Next Steps

### Feature Documentation Complete ✅

This comprehensive feature documentation covers all major MLflow 3.9 capabilities:
- Core tracing with `@mlflow.trace` decorator
- GenAI dashboard and observability
- Auto-instrumentation for popular libraries
- LLM judges and quality assessment
- Tool call tracking and visualization
- OpenTelemetry and distributed tracing
- Streaming and async support
- Prompt registry and version tracking
- Cost and token tracking
- Configuration and deployment options
- Performance and scalability best practices
- LangGraph-specific integration
- Error handling and debugging features
- Python API and programmatic usage
- Migration considerations from MLflow 2.x

### Ready for Phase 2: Migration Planning

With this comprehensive understanding of MLflow 3.9 features, we can now proceed to:

1. **Analyze Current Implementation**: Map our existing `MLFlowTracker` to MLflow 3.9 equivalents
2. **Design New Architecture**: Plan comprehensive migration strategy
3. **Identify Opportunities**: Determine which new features to adopt
4. **Create Migration Plan**: Detailed step-by-step implementation plan

### Key Features to Consider for Our Migration

**High Priority:**
- `@mlflow.trace` decorator for node-level tracing
- Auto-instrumentation via `mlflow.langchain.autolog()`
- Token usage tracking (automatic)
- GenAI dashboard for observability
- Async trace logging for production

**Medium Priority:**
- LLM judges for quality assessment
- Prompt registry for version tracking
- Tool call tracking and visualization
- Enhanced cost tracking with trace-level metrics

**Nice to Have:**
- MLflow Assistant for debugging
- Custom span attributes for richer context
- OpenTelemetry export for external systems

---

*Last Updated: 2026-02-02*
*Phase 1 of T-028: MLFlow 3.9 Comprehensive Migration*
*Status: Documentation Complete → Ready for Phase 2 (Migration Planning)*
