# 🤖 Configurable Agents

> **Local-first, config-driven multi-agent orchestration platform with full observability and zero cloud lock-in**

Build production-grade LLM agent workflows through YAML configs or conversational chat. Deploy from laptop to enterprise Kubernetes with complete observability, multi-LLM support, and advanced control flow.

[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)]()
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![Requirements](https://img.shields.io/badge/requirements-27%2F27%20complete-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-1000%2B%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 🎯 What & Why

**A local-first, config-driven agent orchestration platform built for:**

- **Developers** prototyping multi-agent systems in minutes, not days
- **Researchers** experimenting with agent architectures without infrastructure overhead
- **Teams** validating LLM use cases with production-grade observability
- **Enterprises** deploying agent workflows anywhere (laptop → Docker → K8s)

**Why this exists:**

Building multi-agent systems today requires stitching together LLM providers, orchestration frameworks, state management, observability, and deployment infrastructure. This platform delivers all of that through YAML configs and conversational interfaces, with zero cloud lock-in.

**v1.0 Shipped** (2026-02-04):

Production-ready local-first agent orchestration platform with **multi-LLM support, advanced control flow, complete observability, and 27/27 requirements satisfied** across 4 phases, 19 plans, and 1,000+ tests.

```yaml
# research_agent.yaml - Multi-step workflow with control flow
schema_version: "1.0"

flow:
  name: research_agent

config:
  llm:
    provider: "openai"  # or anthropic, google, ollama
    model: "gpt-4"
    api_key_env: "OPENAI_API_KEY"

state:
  fields:
    topic: {type: str, required: true}
    research: {type: str, default: ""}
    quality_score: {type: int, default: 0}

nodes:
  - id: search
    prompt: "Search for information about {state.topic}"
    tools: [serper_search]
    outputs: [research]

  - id: evaluate
    prompt: "Evaluate research quality on scale 1-10"
    inputs: [research]
    outputs: [quality_score]
    output_schema:
      type: object
      fields:
        - name: quality_score
          type: int

edges:
  - {from: START, to: search}
  - {from: search, to: evaluate}
  - from: evaluate
    routes:
      - condition: "{state.quality_score} >= 7"
        to: END
      - condition: "{state.quality_score} < 7"
        to: search  # Retry with better search

config:
  memory:
    enabled: true
    default_scope: agent  # Persists across runs (agent|workflow|node)

  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"
```

```bash
configurable-agents run research_agent.yaml --input topic="AI Safety"

# Or use Chat UI to generate configs
configurable-agents chat
```

---

## ✨ Key Features

### 🎨 Config-First & Chat-First
- **YAML as code**: Declarative workflow definitions
- **Chat UI**: Generate configs through conversation (Gradio-based)
- **No programming required**: Accessible to non-developers
- **Version control friendly**: Track workflow evolution in git
- **Shareable**: Exchange configs like recipes

### 🧠 Advanced Control Flow
- **Conditional routing**: Branch based on agent outputs
- **Loops and retry**: Iterate until conditions met
- **Parallel execution**: Fan-out/fan-in patterns
- **Sandboxed code**: Execute agent-generated code safely

### 🔌 Multi-LLM Support
- **4 providers**: OpenAI, Anthropic, Google, Ollama
- **Local-first**: Run entirely on Ollama (zero cloud cost)
- **Unified cost tracking**: Compare provider costs
- **Per-node configuration**: Mix providers in one workflow

### 🧠 Persistent Memory
- **Scoped storage**: Agent (cross-run), workflow (intra-run), or node (isolated)
- **Auto-extraction**: Key facts automatically extracted from LLM responses
- **Automatic persistence**: SQLite-backed, survives crashes and restarts
- **Context injection**: Previous memories injected into prompts with configurable limits

### 🔍 Complete Observability
- **MLFlow 3.9 integration**: Automatic tracing and metrics
- **Multi-provider cost tracking**: Unified cost reporting
- **Performance profiling**: Bottleneck detection
- **Execution traces**: Per-node latency, tokens, cost
- **Quality gates**: Automated deployment safety checks

### 🎛️ User Interfaces
- **Chat UI** (Gradio): Config generation through conversation
- **Orchestration Dashboard** (FastAPI + HTMX): Runtime management
- **Deployment Registry**: Service discovery and health monitoring
- **MLFlow UI**: Embedded observability dashboard
- **Real-time updates**: SSE streaming for live monitoring

### 🌐 External Integrations
- **WhatsApp**: Trigger workflows from messages
- **Telegram**: Bot integration for workflow execution
- **Generic webhooks**: Any external system integration
- **HMAC verification**: Secure webhook endpoints

### 🛡️ Production-Grade
- **Parse-time validation**: Catch errors before spending money
- **Type safety**: Full Pydantic schema validation
- **Structured outputs**: Guaranteed response formats
- **Error handling**: Graceful degradation and retries
- **Security**: Sandboxed execution, secret management

### 🐳 Deployment Flexibility
- **Local development**: Run on laptop with SQLite
- **Docker Compose**: Multi-container deployments
- **Kubernetes**: Enterprise-scale with auto-scaling (v1.1+)
- **Storage abstraction**: Swap backends without code changes

---

## 🗺️ Roadmap & Status

| Version | Status | Shipped | Focus |
|---------|--------|---------|-------|
| **v1.0** | ✅ Complete | 2026-02-04 | Multi-LLM, Control Flow, Observability, UIs |
| **v1.1** | 🔮 Planning | TBD | Next milestone goals TBD |

**📋 v1.0 Details**: See [TASKS.md](docs/development/TASKS.md) for complete breakdown

---

### v1.0 Foundation - Shipped ✅

**Status**: 27/27 requirements complete | 4 phases, 19 plans | 1,000+ tests (98%+ pass rate)

#### Phase 1: Core Engine
- ✅ Multi-LLM support (OpenAI, Anthropic, Google, Ollama via LiteLLM)
- ✅ Advanced control flow (conditional routing, loops, parallel execution)
- ✅ Storage abstraction (SQLite → PostgreSQL → Cloud)
- ✅ Cost tracking across all providers

#### Phase 2: Agent Infrastructure
- ✅ Agent registry with heartbeat/TTL
- ✅ Minimal agent containers (~50-100MB)
- ✅ Lifecycle management (registration, health checks, deregistration)
- ✅ Enhanced observability (performance profiling, bottleneck detection)

#### Phase 3: Interfaces & Triggers
- ✅ Gradio Chat UI for config generation
- ✅ FastAPI + HTMX orchestration dashboard
- ✅ Agent discovery and registration interface
- ✅ MLFlow UI iframe integration
- ✅ Real-time monitoring (SSE streaming)
- ✅ Webhook integrations (WhatsApp, Telegram, generic API)

#### Phase 4: Advanced Capabilities
- ✅ Code execution sandboxes (RestrictedPython + Docker)
- ✅ Persistent memory (namespaced, per-agent)
- ✅ 15 pre-built tools (web, file, data, system)
- ✅ Quality gates for deployment safety

**Current capabilities:**
```bash
# Run workflows with advanced control flow
configurable-agents run workflow.yaml --input topic="AI"

# Generate configs through chat
configurable-agents chat

# Manage executions through dashboard
configurable-agents dashboard
# → http://localhost:7861 (Dashboard)

# Trigger via webhooks
curl -X POST http://localhost:8000/webhooks/generic \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "research", "inputs": {"topic": "AI"}}'

# View costs and performance
configurable-agents report costs --period last_7_days
configurable-agents report profile --workflow research

# List deployments
configurable-agents deployments list

# Deploy workflows
configurable-agents deploy workflow.yaml
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/thatAverageGuy/configurable-agents.git
cd configurable-agents

# Install
pip install -e ".[dev]"

# Set up API keys (for providers you'll use)
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY (for OpenAI)
# - ANTHROPIC_API_KEY (for Anthropic)
# - GOOGLE_API_KEY (for Google Gemini)
# - No key needed for Ollama (local models)
```

### Your First Workflow

Create `hello.yaml`:
```yaml
schema_version: "1.0"

flow:
  name: hello_world

config:
  llm:
    provider: "openai"  # or anthropic, google, ollama
    model: "gpt-4"
    api_key_env: "OPENAI_API_KEY"

state:
  fields:
    name: {type: str, required: true}
    greeting: {type: str, default: ""}

nodes:
  - id: greet
    prompt: "Generate a friendly greeting for {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str

edges:
  - {from: START, to: greet}
  - {from: greet, to: END}
```

Run it:
```bash
configurable-agents run hello.yaml --input name="Alice"
```

**Learn more:**
- [QUICKSTART.md](docs/user/QUICKSTART.md) - Complete tutorial with v1.0 features
- [examples/](examples/) - More working examples
- [CONFIG_REFERENCE.md](docs/user/CONFIG_REFERENCE.md) - Full config schema reference

---

## 🎛️ User Interfaces

### Chat UI (Config Generation)

```bash
configurable-agents chat
# → http://localhost:7860
```

Describe your workflow in natural language, get a valid YAML config instantly. Session persistence keeps your conversation history.

### Orchestration Dashboard

```bash
configurable-agents dashboard
# → http://localhost:7861 (Dashboard)
```

- View running executions
- Inspect state and logs
- Trigger new executions
- Monitor deployment registry
- Real-time updates via SSE

---

## 🏗️ Architecture

**Stack:**
- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Graph execution engine
- **[LiteLLM](https://github.com/BerriAI/litellm)**: Multi-LLM abstraction
- **[Pydantic](https://github.com/pydantic/pydantic)**: Type validation
- **[MLFlow](https://mlflow.org/)**: Observability (v3.9+)
- **[FastAPI](https://fastapi.tiangolo.com/)**: API servers
- **[Gradio](https://gradio.app/)**: Chat UI
- **[HTMX](https://htmx.org/)**: Dashboard interactivity
- **[SQLite/PostgreSQL](https://www.postgresql.org/)**: Storage backends

**Design philosophy**: Local-first, config-driven, pluggable, observable.

See [ARCHITECTURE.md](docs/development/ARCHITECTURE.md) for detailed system design.

---

## 📊 v1.0 Delivery

**4 Phases, 19 Plans, 27 Requirements, 1,000+ Tests**

### Phase 1: Core Engine (4 plans)
- Multi-LLM abstraction via LiteLLM
- Advanced control flow (conditionals, loops, parallel)
- Storage abstraction (SQLite/PostgreSQL)
- Unified cost tracking

### Phase 2: Agent Infrastructure (6 plans)
- Agent registry with heartbeat/TTL
- Minimal container design (~50-100MB)
- Performance profiling
- Bottleneck detection

### Phase 3: Interfaces & Triggers (6 plans)
- Gradio Chat UI
- FastAPI + HTMX dashboard
- Agent discovery interface
- Webhook integrations (WhatsApp, Telegram, generic)

### Phase 4: Advanced Capabilities (3 plans)
- Code execution sandboxes (RestrictedPython + Docker)
- Persistent memory backend
- 15 pre-built tools
- Quality gates

**Full details**: [TASKS.md](docs/development/TASKS.md)

---

## 📚 Documentation

> **Complete Documentation Index**: See [docs/README.md](docs/README.md) for a comprehensive index of all documentation.

### User Guides

- **[QUICKSTART.md](docs/user/QUICKSTART.md)** - Get started in 5 minutes
- **[CONFIG_REFERENCE.md](docs/user/CONFIG_REFERENCE.md)** - Config schema guide
- **[OBSERVABILITY.md](docs/user/OBSERVABILITY.md)** - Monitoring and tracking
- **[DEPLOYMENT.md](docs/user/DEPLOYMENT.md)** - Docker deployment guide
- **[TROUBLESHOOTING.md](docs/user/TROUBLESHOOTING.md)** - Common issues and solutions
- **[SECURITY_GUIDE.md](docs/user/SECURITY_GUIDE.md)** - Security best practices
- **[TOOL_DEVELOPMENT.md](docs/user/TOOL_DEVELOPMENT.md)** - Custom tool creation
- **[PERFORMANCE_OPTIMIZATION.md](docs/user/PERFORMANCE_OPTIMIZATION.md)** - Profiling, cost optimization, and bottleneck detection
- **[PRODUCTION_DEPLOYMENT.md](docs/user/PRODUCTION_DEPLOYMENT.md)** - Production patterns
- **[ADVANCED_TOPICS.md](docs/user/ADVANCED_TOPICS.md)** - Advanced features overview

### Core Documentation

- **[ARCHITECTURE.md](docs/development/ARCHITECTURE.md)** - System design overview
- **[SPEC.md](docs/development/SPEC.md)** - Complete config schema specification
- **[PROJECT_VISION.md](docs/development/PROJECT_VISION.md)** - Long-term vision and philosophy
- **[CONTEXT.md](CONTEXT.md)** - Development context (living document)

### Architecture Decisions

- **[Architecture Decision Records](docs/development/adr/)** - Design decisions and rationale
  - 25 ADRs covering all major decisions
  - Immutable history (append-only)
  - Alternatives considered with tradeoffs

### Developer Guides

- **[SETUP.md](SETUP.md)** - Development setup guide

### API Documentation

- **[API Reference](docs/api/)** - Complete API documentation (auto-generated)

---

## 🤝 Contributing

This is an active open-source project (v1.0 shipped).

We welcome contributions:
- ⭐ Star the repo to follow progress
- 📝 Open issues for bugs or feature requests
- 💬 Join discussions
- 🔧 Submit pull requests

---

## 🎯 Use Cases

### Research & Analysis
```yaml
# Multi-step research with quality gates
nodes:
  - id: search
    tools: [serper_search]
  - id: evaluate_quality
  - id: summarize
    routes:
      - condition: "{state.quality} >= 7"
        to: END
      - to: search  # Retry if low quality
```

### Content Generation
```yaml
# Blog post pipeline with review loop
nodes:
  - id: outline
  - id: draft
  - id: review
    routes:
      - condition: "{state.approved}"
        to: END
      - to: draft  # Revise if not approved
  - id: polish
```

### Data Processing
```yaml
# ETL workflow with parallel processing
nodes:
  - id: extract
  - id: transform_parallel
    parallel: true  # Run in parallel
  - id: validate
  - id: load
```

### Automation
```yaml
# Email triage with webhook trigger
webhooks:
  - trigger: generic
    workflow: email_triage

nodes:
  - id: classify
  - id: prioritize
  - id: draft_response
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with inspiration from:
- LangGraph (graph-based agent execution)
- LiteLLM (multi-LLM abstraction)
- MLFlow (LLM observability)
- Infrastructure as Code (Terraform, Docker Compose)

---

## 📬 Contact

Questions? Ideas? Feedback?

- 📧 Email: [yogesh.singh893@gmail.com](mailto:yogesh.singh893@gmail.com)
- 🐛 Issues: [GitHub Issues](https://github.com/thatAverageGuy/configurable-agents/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/thatAverageGuy/configurable-agents/discussions)

---

<div align="center">

**Made with ❤️ for the agent builder community**

*Star ⭐ this repo to follow our progress!*

</div>
