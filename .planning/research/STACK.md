# Stack Research: Agent Orchestration Platform

**Domain:** Local-first, config-driven agent orchestration with multi-LLM support
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

This research focuses on the **incremental stack additions** needed to evolve from v0.1 (basic LangGraph + MLFlow + Google Gemini) to advanced agent orchestration capabilities. The recommended stack prioritizes **Python-only**, **local-first**, and **lightweight** technologies that align with the project's core constraints.

**Key Finding:** The existing foundation (LangGraph, Pydantic, MLFlow 3.9+, FastAPI, Docker) is solid and current. The primary additions needed are: (1) multi-LLM abstraction layer, (2) conversational UI framework, (3) orchestration management UI, (4) enhanced observability, and (5) optional sandboxing.

## Core Technologies (Already in v0.1)

| Technology | Version | Purpose | Status | Confidence |
|------------|---------|---------|--------|------------|
| **LangGraph** | >=0.0.20 | Stateful graph-based agent execution | ✅ Deployed | HIGH |
| **Pydantic** | >=2.0 | Config validation, structured outputs | ✅ Deployed | HIGH |
| **MLFlow** | >=3.9.0 | LLM observability, experiment tracking | ✅ Deployed | HIGH |
| **FastAPI** | Latest | Async API server for deployments | ✅ Deployed | HIGH |
| **Docker** | Latest | Container-based deployment | ✅ Deployed | HIGH |
| **Google Gemini** | via langchain-google-genai | Single LLM provider (v0.1) | ✅ Deployed | HIGH |

**Rationale:** These are already battle-tested in v0.1 and represent current best practices for 2025-2026.

---

## Multi-LLM Integration Layer

### Primary Recommendation: LiteLLM

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| **LiteLLM** | Latest (active as of Jan 2026) | Unified interface for 100+ LLM providers | Industry standard for multi-provider abstraction |

**Why LiteLLM:**
- Supports 100+ providers (OpenAI, Anthropic, Google, Ollama, Azure, AWS Bedrock, etc.) in OpenAI-compatible format
- 8ms P95 latency at 1k RPS (production-grade performance)
- Built-in cost tracking, retry/fallback logic, and load balancing
- Exception handling with OpenAI-compatible errors
- Works as both Python library and AI Gateway/Proxy
- Active development (latest update: Jan 26, 2026)

**Installation:**
```bash
pip install 'litellm[proxy]'
```

**Integration Pattern:**
```python
# Wrap existing provider logic with LiteLLM
from litellm import completion

response = completion(
    model="gpt-4",  # or "claude-3-5-sonnet", "gemini/gemini-2.0-flash", "ollama/llama3"
    messages=[{"role": "user", "content": "Hello"}]
)
```

**Confidence:** HIGH (verified via official docs, active in 2026)

**Sources:**
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [LiteLLM Docs](https://docs.litellm.ai/docs/)
- [2026 Review](https://www.truefoundry.com/blog/a-detailed-litellm-review-features-pricing-pros-and-cons-2026)

### Alternative: Direct Provider SDKs

For projects requiring maximum control or minimal dependencies:

| Provider | Library | Version | When to Use |
|----------|---------|---------|-------------|
| OpenAI | langchain-openai | Latest | Direct OpenAI integration |
| Anthropic | langchain-anthropic | Latest | Direct Anthropic integration |
| Ollama | langchain-ollama | Latest | Local-first LLM deployments |

**Why consider alternatives:**
- LiteLLM adds abstraction overhead (~8ms)
- Direct SDKs offer provider-specific features (e.g., Anthropic's extended thinking)
- Useful if you only need 2-3 providers

**Recommendation:** Start with LiteLLM for flexibility, fall back to direct SDKs only if specific provider features are needed.

**Confidence:** MEDIUM (depends on specific requirements)

---

## Local LLM Support

### Primary Recommendation: Ollama

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Ollama** | Latest (active 2026) | Local LLM runtime | De facto standard for local LLM deployment |

**Why Ollama:**
- Run LLMs locally with zero cloud dependencies
- Supports Llama 3, Gemma, DeepSeek, Qwen, Mistral, and 50+ other models
- Python SDK + REST API + CLI
- Multi-modal support (text + images)
- JSON mode for structured outputs (essential for agents)
- "Thinking" mode for reasoning-heavy tasks
- Zero recurring API costs, full privacy control

**Installation:**
```bash
# Install Ollama binary (Windows/macOS/Linux)
# Download from https://ollama.ai

# Python integration
pip install ollama
```

**Integration with LiteLLM:**
```python
# LiteLLM works seamlessly with Ollama
response = completion(
    model="ollama/llama3",
    api_base="http://localhost:11434"
)
```

**Confidence:** HIGH (verified via official docs, community standard)

**Sources:**
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Complete Ollama Tutorial 2026](https://dev.to/proflead/complete-ollama-tutorial-2026-llms-via-cli-cloud-python-3m97)
- [Ollama Python Integration](https://realpython.com/ollama-python/)

---

## Conversational UI Framework

### Primary Recommendation: Gradio

| Framework | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| **Gradio** | 6.5.1 (latest: Jan 29, 2026) | Conversational agent UI | Best for rapid AI demos, Hugging Face ecosystem |

**Why Gradio:**
- `gr.ChatInterface` specifically designed for chatbot UIs
- Minimal code to deploy conversational interfaces
- Built-in sharing via public URLs (great for demos)
- Free hosting on Hugging Face Spaces
- Streaming support (essential for LLM responses)
- No JavaScript/CSS required (Python-only constraint)
- 41,000+ GitHub stars, 84,000+ dependent projects

**Use Cases:**
- Config generation chatbot (user describes workflow, agent generates YAML)
- Agent testing interface (send inputs, view outputs)
- Workflow prototyping

**Installation:**
```bash
pip install gradio==6.5.1
```

**Example:**
```python
import gradio as gr

def chat_fn(message, history):
    # Your agent logic
    return response

gr.ChatInterface(chat_fn).launch()
```

**Confidence:** HIGH (verified via official GitHub, current version)

**Sources:**
- [Gradio GitHub](https://github.com/gradio-app/gradio)
- [Gradio vs Streamlit 2025](https://www.squadbase.dev/en/blog/streamlit-vs-gradio-in-2025-a-framework-comparison-for-ai-apps)

### Alternative: Streamlit

| Framework | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| **Streamlit** | Latest | Data apps + dashboards | When you need rich dashboards alongside chat |

**Why Streamlit:**
- `st.chat_message` for streaming chat updates
- Better for complex data visualizations
- More customization options than Gradio
- Production-ready for full web apps

**When to prefer Streamlit over Gradio:**
- You need advanced customization
- You want dashboards + chat in one UI
- You're building a production app (not a demo)

**Confidence:** HIGH (verified via official docs)

**Sources:**
- [Streamlit vs Gradio Comparison](https://www.squadbase.dev/en/blog/streamlit-vs-gradio-in-2025-a-framework-comparison-for-ai-apps)

**Recommendation:** Use **Gradio** for conversational config generation UI, **Streamlit** for orchestration management dashboard (if needed).

---

## Orchestration Management UI

### Primary Recommendation: FastAPI + HTMX + DaisyUI

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **FastAPI** | Latest | Backend API | Already in stack, async-first |
| **HTMX** | 2.x | Dynamic HTML updates | No JavaScript framework needed |
| **Jinja2** | 3.1.6 | Template engine | Python-native, FastAPI-compatible |
| **TailwindCSS** | Latest | CSS framework | Utility-first styling |
| **DaisyUI** | Latest | UI components | Pre-built components for HTMX |

**Why This Stack:**
- **Python-only** (no React/Vue/Angular JavaScript frameworks)
- **Lightweight** (HTMX is 14KB, no build step)
- **Server-side** (HTML fragments returned from FastAPI)
- **Production-ready** (Used by Netflix, Uber, Microsoft)
- **Perfect for orchestration UIs** (lists, tables, forms, real-time updates)

**Use Cases:**
- Workflow management (list, start, stop workflows)
- Real-time execution monitoring (progress bars, logs)
- MLFlow integration (link to experiment tracking)
- Configuration editor (YAML/JSON forms)

**Architecture:**
```
User Browser (HTMX) ←→ FastAPI (Jinja2 templates) ←→ Backend Logic
                                                    ↓
                                                  MLFlow
```

**Installation:**
```bash
# Python dependencies (already have FastAPI)
pip install jinja2==3.1.6

# Frontend dependencies (via npm or CDN)
npm install tailwindcss@latest daisyui@latest
```

**Why HTMX over React:**
- No build step (simpler development)
- Server-side rendering (better for Python teams)
- Smaller bundle size (faster page loads)
- "It's 2025 — we don't need to overcomplicate things anymore" (from search results)

**Confidence:** HIGH (verified via recent examples, active in 2026)

**Sources:**
- [FastAPI + HTMX + DaisyUI Guide](https://sunscrapers.com/blog/modern-web-dev-fastapi-htmx-daisyui/)
- [FastAPI HTMX Example](https://github.com/volfpeter/fastapi-htmx-tailwind-example)
- [DaisyUI with HTMX](https://daisyui.com/docs/install/htmx/)

### Alternative: Streamlit (All-in-One)

If you prefer a single framework for both conversational UI and orchestration:

| Framework | When to Use |
|-----------|-------------|
| **Streamlit** | You want one framework for everything, less customization needed |

**Tradeoff:** Less flexibility, but faster to build.

---

## Enhanced Observability

### Primary Recommendation: MLFlow 3.9.0+ with OpenTelemetry

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **MLFlow** | >=3.9.0 (released Jan 30, 2026) | LLM observability | Already in stack, v3.9+ has major enhancements |
| **OpenTelemetry** | Latest Python SDK | Distributed tracing | Industry standard, MLFlow 3.6+ native support |

**MLFlow 3.9.0 New Features (2026):**
- **AI Assistant:** Claude Code-powered assistant for LLMOps best practices
- **Performance Dashboards:** Pre-built charts for latency, request counts, quality scores
- **Judge Optimization:** MemAlign algorithm for learning evaluation guidelines
- **Visual Judge Configuration:** Create LLM judge prompts without code
- **Continuous Quality Monitoring:** Auto-execute LLM judges on traces
- **Distributed Tracing:** Context propagation across multiple services (via OpenTelemetry)

**OpenTelemetry Integration (MLFlow 3.6+):**
- Unified traces combining MLFlow SDK + OpenTelemetry auto-instrumentation
- Ingest OpenTelemetry spans directly into MLFlow tracking server
- OTLP endpoint at `/v1/traces`
- Export traces to any observability platform (Datadog, Grafana, Prometheus)
- Multi-language support (Java, Go, Rust, etc.)

**Why This Matters for Agent Orchestration:**
- **Multi-agent tracing:** Track interactions across multiple LLM calls
- **Cost tracking:** Detailed token usage and cost per agent/node
- **Quality monitoring:** Auto-evaluate agent outputs with LLM judges
- **Distributed systems:** Trace requests across FastAPI → LangGraph → Multiple LLMs

**Installation:**
```bash
# MLFlow (already in stack)
pip install mlflow>=3.9.0

# OpenTelemetry
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

**Integration:**
```python
# MLFlow auto-integrates with OpenTelemetry
import mlflow

mlflow.autolog()  # Auto-logs LangChain, OpenAI, Anthropic, etc.

# OpenTelemetry spans automatically combine with MLFlow traces
```

**Confidence:** HIGH (verified via official MLFlow releases, Jan 30 2026)

**Sources:**
- [MLFlow 3.9.0 Release](https://mlflow.github.io/mlflow-website/releases/)
- [MLFlow OpenTelemetry Integration](https://mlflow.org/blog/opentelemetry-tracing-support)
- [MLFlow 3.6 OpenTelemetry Support](https://awadrahman.medium.com/mlflow-3-6-fully-supports-opentelemetry-bccba8d3e4fb)

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **LangSmith** | Latest | LangChain-specific tracing | Alternative to MLFlow for LangChain projects |
| **Langfuse** | Latest | Open-source LLM observability | If you need more granular prompt versioning |

**Recommendation:** Stick with **MLFlow 3.9+** as it's already in the stack and now has best-in-class LLM observability.

---

## Storage Backends

### Primary Recommendation: SQLite (Default) with DuckDB (Analytics)

| Database | Version | Purpose | Why Recommended |
|----------|---------|---------|-----------------|
| **SQLite** | Latest | Transactional storage | Local-first, zero-config, embedded |
| **DuckDB** | Latest | Analytical queries | Embedded analytics, 10-100x faster for OLAP |

**Architecture:**
```
Application State (transactional) → SQLite
  - Workflow metadata
  - Execution history
  - User configurations

Analytics (OLAP queries) → DuckDB
  - Aggregations across thousands of runs
  - Complex analytical queries
  - Feature engineering for ML pipelines
```

**Why SQLite:**
- Zero configuration (file-based)
- Built into Python standard library
- Perfect for transactional workloads (CRUD operations)
- Local-first (no cloud dependency)

**Why DuckDB:**
- 10-100x faster than SQLite for analytical queries
- Columnar storage optimized for OLAP
- Integrates seamlessly with Pandas, Polars
- Still embedded (no separate server)

**When to Use Each:**
- **SQLite:** Application database (workflow configs, execution logs)
- **DuckDB:** Analytics engine (aggregate metrics, dashboard queries)

**Complementary Architecture:**
```python
# Store in SQLite
with sqlite3.connect("workflows.db") as conn:
    conn.execute("INSERT INTO runs ...")

# Analyze with DuckDB
import duckdb
duckdb.execute("SELECT AVG(duration) FROM 'workflows.db'.runs GROUP BY workflow_id")
```

**Installation:**
```bash
# SQLite (built-in)
# No installation needed

# DuckDB
pip install duckdb
```

**Confidence:** HIGH (verified via recent 2026 comparisons)

**Sources:**
- [SQLite vs DuckDB Comparison](https://betterstack.com/community/guides/scaling-python/duckdb-vs-sqlite/)
- [DuckDB for Embedded Analytics](https://medium.com/@Quaxel/from-sqlite-to-duckdb-embedded-analytics-is-here-da79263a7fea)

### Enterprise Upgrade Path

| Database | When to Upgrade |
|----------|-----------------|
| **PostgreSQL** | Multi-user deployments, need ACID at scale |
| **Redis** | Need shared state across distributed workers |
| **S3/MinIO** | Large artifact storage (videos, documents) |

**Recommendation:** Start with SQLite+DuckDB, upgrade only when deployment scale demands it.

---

## Advanced Control Flow (LangGraph Enhancements)

### Already Supported in LangGraph 1.0+

| Feature | Status | Implementation |
|---------|--------|----------------|
| **Branching** | ✅ Available | `conditional_edges` + fan-out/fan-in |
| **Loops** | ✅ Available | Cyclic graphs with termination conditions |
| **Parallel Execution** | ✅ Available | `Send` API with `max_concurrency` config |
| **Checkpoints** | ✅ Available | Persistent state across executions |
| **Retries** | ✅ Available | Built-in retry logic per node |

**No New Dependencies Needed:** LangGraph already supports these features natively.

**Key Enhancements for v0.2+:**
1. **Conditional Routing:** Use `conditional_edges` to route based on state
2. **Parallel Task Execution:** Use `Send` for scatter-gather patterns
3. **Defer Pattern:** Handle async completion with `defer` for asymmetric branches
4. **State Machines:** Use checkpoints for long-running workflows

**Configuration Example:**
```yaml
# Conditional routing
edges:
  - from: analyze
    to_conditional:
      condition: "state.confidence > 0.8"
      if_true: approve
      if_false: human_review

# Parallel execution
nodes:
  - id: parallel_research
    max_concurrency: 3
    subtasks: [task1, task2, task3]
```

**Confidence:** HIGH (verified via LangGraph 1.0 docs, active 2026)

**Sources:**
- [LangGraph 2026 Edition](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3)
- [LangGraph Multi-Agent Orchestration](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [Parallel Nodes in LangGraph](https://medium.com/@gmurro/parallel-nodes-in-langgraph-managing-concurrent-branches-with-the-deferred-execution-d7e94d03ef78)

---

## Code Sandboxing (Optional)

### Primary Recommendation: Docker Containers (Already in Stack)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Docker** | Latest | Process isolation | Already in deployment stack, battle-tested |

**Why Docker for Sandboxing:**
- **Process isolation:** Run untrusted code in separate containers
- **Resource limits:** CPU, memory, network constraints
- **Network sandboxing:** Restrict internet access
- **Already deployed:** No new technology to learn

**Alternative for Lightweight Sandboxing:**

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| **RestrictedPython** | 8.2 (supports Python 3.9-3.13) | AST-based code restriction | Lightweight, Python-only sandboxing |

**Why RestrictedPython:**
- Restrict Python language features (no `import os`, `eval`, etc.)
- AST manipulation for compile-time safety
- Used by Plone, Zope (production-tested)

**Why NOT RestrictedPython:**
- ⚠️ **Security Warning:** "Glass sandbox" - can be bypassed via Python's object system
- Recent CVEs (CVE-2024-47532: information leakage)
- Not a true sandbox, just a restriction layer
- Should be combined with process isolation (Docker)

**Recommendation:**
- **v0.2:** Use Docker containers for sandboxing (already in stack)
- **Future:** Consider Firecracker (AWS Lambda's microVM) for ultra-fast isolation
- **Do NOT rely on RestrictedPython alone** for security-critical sandboxing

**Confidence:** MEDIUM (RestrictedPython has known limitations)

**Sources:**
- [RestrictedPython GitHub](https://github.com/zopefoundation/RestrictedPython)
- [Glass Sandbox Security Analysis](https://checkmarx.com/zero-post/glass-sandbox-complexity-of-python-sandboxing/)

---

## Docker Best Practices (2026)

### Lightweight Container Optimization

| Practice | Why | Implementation |
|----------|-----|----------------|
| **Use `python:3.11-slim`** | 121MB vs 875MB (7x smaller) | `FROM python:3.11-slim` |
| **Multi-stage builds** | Separate build tools from runtime | Build stage + runtime stage |
| **Non-root user** | Security (don't run as root) | `USER appuser` |
| **Layer caching** | Faster builds | Copy `requirements.txt` before code |
| **Combine RUN commands** | Fewer layers = smaller image | `RUN apt-get update && apt-get install` |

**Example Dockerfile:**
```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
USER appuser
CMD ["python", "main.py"]
```

**Confidence:** HIGH (verified via 2026 Docker best practices)

**Sources:**
- [Docker Best Practices 2026](https://medium.com/devops-ai-decoded/docker-in-2026-top-10-must-see-innovations-and-best-practices-for-production-success-30a5e090e5d6)
- [Python Docker Best Practices](https://testdriven.io/blog/docker-best-practices/)

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **LangChain (base)** | Deprecated for agent orchestration | LangGraph (stateful, graph-based) |
| **CrewAI** | Framework lock-in, built on LangChain | LangGraph (more flexible) |
| **AutoGen** | Microsoft-specific, less flexible | LangGraph (config-driven) |
| **React/Vue/Angular** | JavaScript frameworks (violates Python-only) | HTMX + FastAPI |
| **RestrictedPython alone** | Insecure "glass sandbox" | Docker containers |
| **Python <3.10** | Missing modern type hints, async features | Python 3.11+ |
| **MLFlow <3.6** | No OpenTelemetry support | MLFlow 3.9+ |

**Rationale:**
- **LangChain:** Superseded by LangGraph for agent workflows (LangGraph is purpose-built for stateful agents)
- **CrewAI/AutoGen:** Framework lock-in, less control over execution graph
- **JavaScript frameworks:** Violates Python-only constraint, adds build complexity
- **RestrictedPython:** Security theater without process isolation

**Confidence:** HIGH (based on ecosystem trends, security analysis)

---

## Installation Summary

### Core Stack (v0.1 → v0.2)

```bash
# Multi-LLM support
pip install 'litellm[proxy]'

# Local LLM support
pip install ollama

# Conversational UI
pip install gradio==6.5.1

# Orchestration UI
pip install jinja2==3.1.6

# Enhanced observability (upgrade)
pip install mlflow>=3.9.0 opentelemetry-api opentelemetry-sdk

# Analytics database
pip install duckdb
```

### Optional Dependencies

```bash
# Alternative UI framework
pip install streamlit

# Direct provider SDKs (if not using LiteLLM)
pip install langchain-openai langchain-anthropic langchain-ollama

# Alternative observability
pip install langsmith langfuse
```

---

## Version Compatibility Matrix

| Package A | Compatible Version | Notes |
|-----------|-------------------|-------|
| LangGraph | >=0.0.20 | Works with LangChain >=0.1.0 |
| MLFlow | >=3.9.0 | Requires Python >=3.10 |
| Pydantic | >=2.0 | Breaking changes from v1 (but we're already on v2) |
| LiteLLM | Latest | Works with all provider SDKs |
| Gradio | 6.5.1 | Works with FastAPI for hybrid UIs |
| OpenTelemetry | Latest | MLFlow 3.6+ has native support |

---

## Stack Patterns by Use Case

### Use Case 1: Conversational Config Generator

**Stack:**
- Gradio (conversational UI)
- LiteLLM (multi-LLM support for Anthropic Claude)
- LangGraph (workflow execution)
- MLFlow 3.9+ (conversation tracking)

**Why:** Rapid prototyping, minimal code, free Hugging Face hosting.

### Use Case 2: Production Orchestration Dashboard

**Stack:**
- FastAPI + HTMX + DaisyUI (orchestration UI)
- LiteLLM (multi-provider support)
- LangGraph (workflow engine)
- MLFlow 3.9+ + OpenTelemetry (distributed tracing)
- SQLite + DuckDB (storage + analytics)
- Docker (deployment)

**Why:** Full control, production-grade, Python-only, local-first.

### Use Case 3: Local-First Agent Runner (No Cloud)

**Stack:**
- Ollama (local LLMs)
- LangGraph (orchestration)
- SQLite (storage)
- Docker (sandboxing)
- Gradio or FastAPI+HTMX (UI)

**Why:** Zero cloud dependencies, privacy-first, no API costs.

---

## Migration Path (v0.1 → v0.2+)

### Phase 1: Multi-LLM Support
1. Add LiteLLM as abstraction layer
2. Migrate Google Gemini to LiteLLM
3. Add OpenAI, Anthropic, Ollama providers
4. Update config schema to support provider selection

### Phase 2: Conversational UI
1. Add Gradio dependency
2. Build config generation chatbot
3. Deploy to Hugging Face Spaces (optional)

### Phase 3: Orchestration UI
1. Add HTMX + Jinja2 + DaisyUI
2. Build workflow management dashboard
3. Integrate with MLFlow for real-time monitoring

### Phase 4: Enhanced Observability
1. Upgrade MLFlow to 3.9+
2. Add OpenTelemetry instrumentation
3. Configure distributed tracing

### Phase 5: Advanced Control Flow
1. Enable conditional routing in config schema
2. Add parallel execution support
3. Implement checkpoint/resume logic

---

## Sources

### Multi-LLM & Orchestration
- [LLM Orchestration 2026](https://research.aimultiple.com/llm-orchestration/)
- [Top AI Agent Frameworks 2025](https://www.kubiya.ai/blog/ai-agent-orchestration-frameworks)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [LiteLLM Review 2026](https://www.truefoundry.com/blog/a-detailed-litellm-review-features-pricing-pros-and-cons-2026)

### Conversational UI
- [Gradio GitHub](https://github.com/gradio-app/gradio)
- [Streamlit vs Gradio 2025](https://www.squadbase.dev/en/blog/streamlit-vs-gradio-in-2025-a-framework-comparison-for-ai-apps)
- [Gradio vs Streamlit Comparison](https://evidence.dev/learn/gradio-vs-streamlit)

### Observability
- [MLFlow 3.9.0 Release](https://mlflow.github.io/mlflow-website/releases/)
- [MLFlow OpenTelemetry Support](https://mlflow.org/blog/opentelemetry-tracing-support)
- [MLFlow 3.6 OpenTelemetry](https://awadrahman.medium.com/mlflow-3-6-fully-supports-opentelemetry-bccba8d3e4fb)

### Orchestration UI
- [FastAPI + HTMX + DaisyUI Guide](https://sunscrapers.com/blog/modern-web-dev-fastapi-htmx-daisyui/)
- [FastAPI HTMX Example](https://github.com/volfpeter/fastapi-htmx-tailwind-example)
- [DaisyUI with HTMX](https://daisyui.com/docs/install/htmx/)

### LangGraph Control Flow
- [LangGraph Explained 2026](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3)
- [LangGraph Multi-Agent Orchestration](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [Parallel Nodes in LangGraph](https://medium.com/@gmurro/parallel-nodes-in-langgraph-managing-concurrent-branches-with-the-deferred-execution-d7e94d03ef78)

### Local LLMs
- [Ollama Tutorial 2026](https://dev.to/proflead/complete-ollama-tutorial-2026-llms-via-cli-cloud-python-3m97)
- [Ollama Python Integration](https://realpython.com/ollama-python/)
- [Ollama GitHub](https://github.com/ollama/ollama)

### Storage
- [SQLite vs DuckDB](https://betterstack.com/community/guides/scaling-python/duckdb-vs-sqlite/)
- [DuckDB Embedded Analytics](https://medium.com/@Quaxel/from-sqlite-to-duckdb-embedded-analytics-is-here-da79263a7fea)

### Sandboxing
- [RestrictedPython GitHub](https://github.com/zopefoundation/RestrictedPython)
- [Python Sandboxing Security](https://checkmarx.com/zero-post/glass-sandbox-complexity-of-python-sandboxing/)

### Docker
- [Docker Best Practices 2026](https://medium.com/devops-ai-decoded/docker-in-2026-top-10-must-see-innovations-and-best-practices-for-production-success-30a5e090e5d6)
- [Python Docker Best Practices](https://testdriven.io/blog/docker-best-practices/)

---

**Research Complete:** 2026-02-02
**Next Step:** Use this stack research to inform roadmap creation for v0.2-v0.4
