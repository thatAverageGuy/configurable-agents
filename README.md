# 🤖 Configurable Agents

> **Transform YAML into production-grade AI agent workflows**

Config-driven LLM agent runtime that turns your ideas into executable workflows in minutes, not days.

[![Status](https://img.shields.io/badge/status-alpha-orange)]()
[![Version](https://img.shields.io/badge/version-0.1.0--dev%20(70%25)-blue)]()
[![Progress](https://img.shields.io/badge/tasks-19%2F27%20complete-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 🎯 Vision

**From idea to production in minutes.**

No code. No frameworks to learn. Just describe your workflow in YAML and run it.

```yaml
# article_writer.yaml
flow:
  name: article_writer

state:
  fields:
    topic: {type: str, required: true}
    article: {type: str, default: ""}

nodes:
  - id: write
    prompt: "Write a comprehensive article about {state.topic}"
    outputs: [article]
    output_schema:
      type: object
      fields:
        - name: article
          type: str

edges:
  - {from: START, to: write}
  - {from: write, to: END}
```

```bash
configurable-agents run article_writer.yaml --input topic="AI Safety"
```

**That's it.** No Python code. No imports. No boilerplate.

---

## ✨ Key Features

### 🎨 Config-First Design
- **YAML as code**: Your config IS your application
- **No programming required**: Accessible to non-developers
- **Version control friendly**: Track workflow evolution in git
- **Shareable**: Exchange configs like recipes

### 🛡️ Production-Grade
- **Parse-time validation**: Catch errors before spending money on LLM calls
- **Type safety**: Full Pydantic schema validation
- **Structured outputs**: Guaranteed response formats
- **Tool integration**: Web search, APIs, databases

### 🚀 Built for Speed
- **Fast iteration**: Edit config → run → see results (seconds, not minutes)
- **LangGraph powered**: Battle-tested execution engine
- **DSPy ready**: Optimize prompts automatically (v0.3)
- **Future-proof**: Full schema from day one, no breaking changes

### 🎓 Learn as You Grow
- **Start simple**: Linear workflows in v0.1
- **Add complexity**: Conditionals and loops in v0.2
- **Scale up**: Parallel execution, optimization in v0.3
- **Same config works everywhere**: Local → Docker → Cloud

### 🔍 Observability (v0.1)
- **MLFlow integration**: Track every workflow run
- **Cost monitoring**: Token usage and $ per execution
- **Prompt inspection**: View resolved prompts and LLM responses
- **Built-in dashboard**: MLFlow UI at http://localhost:5000

```yaml
config:
  observability:
    mlflow:
      enabled: true
```

### 🐳 Docker Deployment (v0.1)
- **One-command deploy**: `configurable-agents deploy workflow.yaml`
- **Instant microservices**: FastAPI server + MLFlow UI in container
- **Sync/async execution**: Fast workflows return immediately, slow ones async
- **Production-ready**: Health checks, OpenAPI docs, optimized images

```bash
configurable-agents deploy workflow.yaml
# → http://localhost:8000 (API)
# → http://localhost:5000 (MLFlow UI)

curl -X POST http://localhost:8000/run \
  -d '{"topic": "AI Safety"}'
```

---

## 🗺️ Roadmap & Status

| Version | Status | Target | Theme | Focus |
|---------|--------|--------|-------|-------|
| **v0.1** | 🔄 70% (19/27) | March 2026 | Production Ready | Linear flows + Observability + Docker |
| **v0.2** | 📋 Planned | Q2 2026 | Intelligence | Conditionals, loops, multi-LLM |
| **v0.3** | 🔮 Future | Q3 2026 | Optimization | DSPy, parallel execution |
| **v0.4** | 🌟 Vision | Q4 2026 | Ecosystem | Visual tools, cloud deploy |

**📋 Detailed Progress**: See [TASKS.md](docs/TASKS.md) for complete task breakdown

---

### v0.1 - Production Ready (Current)

**Status**: 70% complete (19/27 tasks) | **Target**: March 2026

#### ✅ Working Now

```bash
# Install and run
pip install -e .
configurable-agents run workflow.yaml --input topic="AI Safety"

# Validate before running
configurable-agents validate workflow.yaml

# Python API
from configurable_agents.runtime import run_workflow
result = run_workflow("workflow.yaml", {"topic": "AI"})
```

**Core Features**:
- ✅ Config-driven workflows (YAML/JSON)
- ✅ Linear node execution (sequential)
- ✅ Structured LLM outputs (Pydantic validation)
- ✅ Tool integration (Serper web search)
- ✅ Parse-time validation (fail fast, save money)
- ✅ CLI interface (run, validate, verbose)
- ✅ 514 tests (28 integration + 486 unit)
- ✅ Google Gemini integration

#### ⏳ In Progress (Completing v0.1)

**Observability** (T-018 to T-021):
```bash
# MLFlow tracking (coming soon)
configurable-agents run workflow.yaml --input topic="AI"
mlflow ui  # View costs, traces, prompts at http://localhost:5000
```

**Docker Deployment** (T-022 to T-024):
```bash
# One-command deployment (coming soon)
configurable-agents deploy workflow.yaml
# → API: http://localhost:8000
# → MLFlow UI: http://localhost:5000
```

#### Current Limitations (v0.1)

- Linear flows only (no if/else, loops)
- Single LLM provider (Gemini)
- In-memory state (no persistence)

---

### v0.2 - Intelligence 🔮

**Target**: Q2 2026 (+8-12 weeks) | **Theme**: Advanced Control Flow

**Key Features**:
- Conditional routing (if/else based on state)
- Loops and retry logic
- Multi-LLM support (OpenAI, Anthropic, Ollama)
- State persistence and workflow resume
- Config composition (import/extend)
- Enhanced error messages

**Example - Conditional Routing**:
```yaml
edges:
  - from: review
    routes:
      - condition: "{state.score} >= 7"
        to: END
      - condition: "{state.score} < 7"
        to: write  # Retry
```

---

### v0.3 - Optimization 🎯

**Target**: Q3 2026 (+12-16 weeks) | **Theme**: DSPy & Performance

**Key Features**:
- DSPy prompt optimization (automatic)
- Quality metrics and evaluation
- Parallel node execution
- OpenTelemetry integration
- AI config generator

**Example - DSPy Optimization**:
```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
  metric: "semantic_match"
```

---

### v0.4 - Ecosystem 🌍

**Target**: Q4 2026 (+16-24 weeks) | **Theme**: Tools & Scale

**Key Features**:
- Visual workflow editor
- One-click cloud deployments
- Prometheus + Grafana monitoring
- Plugin system
- Config marketplace

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd configurable-agents

# Install
pip install -e ".[dev]"

# Set up API keys
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Your First Workflow

Create `hello.yaml`:
```yaml
schema_version: "1.0"

flow:
  name: hello_world

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
- [QUICKSTART.md](docs/QUICKSTART.md) - Complete tutorial
- [examples/](examples/) - More working examples
- [CONFIG_REFERENCE.md](docs/CONFIG_REFERENCE.md) - Full config guide

---

## 🏗️ Architecture

Built on proven technologies:

- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Execution engine (doesn't interfere with DSPy)
- **[Pydantic](https://github.com/pydantic/pydantic)**: Type validation and schemas
- **[Google Gemini](https://ai.google.dev/)**: LLM provider (v0.1)
- **[DSPy](https://github.com/stanfordnlp/dspy)**: Prompt optimization (v0.3)

**Design philosophy**: Config-first, fail-fast, future-proof.

See [Architecture Decision Records](docs/adr/) for detailed design choices.

---

## 📊 Current Progress

### Phase 1: Foundation (8/8 complete) ✅ COMPLETE
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System (already complete in T-003)
- ✅ T-006: State Schema Builder
- ✅ T-007: Output Schema Builder

### Phase 2: Core Execution (6/6 complete) ✅ COMPLETE
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ✅ T-011: Node Executor
- ✅ T-012: Graph Builder
- ✅ T-013: Runtime Executor

### Phase 3: Polish & UX (4/4 complete) ✅ COMPLETE
- ✅ T-014: CLI Interface
- ✅ T-015: Example Configs
- ✅ T-016: Documentation
- ✅ T-017: Integration Tests

### Phase 3: Observability (0/4 complete)
- ⏳ T-018: MLFlow Integration Foundation
- ⏳ T-019: MLFlow Instrumentation
- ⏳ T-020: Cost Tracking & Reporting
- ⏳ T-021: Observability Documentation

### Phase 3: Docker Deployment (0/3 complete)
- ⏳ T-022: Docker Artifact Generator & Templates
- ⏳ T-023: FastAPI Server with Sync/Async
- ⏳ T-024: CLI Deploy Command & Streamlit Integration

### Deferred to v0.2+ (3 tasks)
- ⏳ T-025: Error Message Improvements
- ⏳ T-026: DSPy Integration Test
- ⏳ T-027: Structured Output + DSPy

**Overall Progress**: 19/27 tasks complete (70%)

**Next up**: T-019 (MLFlow Instrumentation)

Full task breakdown: [docs/TASKS.md](docs/TASKS.md)

---

## 📚 Documentation

### Core Documentation

- **[PROJECT_VISION.md](docs/PROJECT_VISION.md)** - Long-term vision and philosophy
  - *What we're building and why*
  - Success metrics and non-goals
  - 3-year roadmap and phases
  - Core design principles

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design overview
  - *How the system works (target v0.1)*
  - Component architecture and data flow
  - Technology stack decisions
  - File paths reference future implementation

- **[SPEC.md](docs/SPEC.md)** - Complete config schema specification
  - *The contract: Schema v1.0*
  - Every field documented with examples
  - Type system reference
  - Validation rules

- **[TASKS.md](docs/TASKS.md)** - Detailed work breakdown
  - *What's being built, task by task*
  - All 27 tasks for v0.1 with acceptance criteria
  - Dependencies and estimates
  - Current progress tracker (19/27 complete)

- **[CONTEXT.md](docs/CONTEXT.md)** - Development context (living document)
  - *Current state, next action, and development standards*
  - What works now vs. in progress
  - Quick reference for LLM sessions
  - Updated after each task completion

### Architecture Decisions

- **[Architecture Decision Records](docs/adr/)** - Design decisions and rationale
  - *Why we made specific choices*
  - 16 ADRs covering all major decisions
  - Immutable history (append-only)
  - Alternatives considered with tradeoffs
  - Implementation details for completed decisions

### Implementation Logs

- **[Implementation Logs](docs/implementation_logs/)** - Detailed task implementation records
  - *How each task was implemented*
  - 18 comprehensive logs (150-500 lines each)
  - Organized by development phase
  - Code examples, verification steps, design decisions
  - Complete technical context for each task

### User Guides

- **[QUICKSTART.md](docs/QUICKSTART.md)** - Get started in 5 minutes
  - *Step-by-step tutorial for beginners*
  - Installation and API key setup
  - Your first workflow
  - Understanding outputs

- **[CONFIG_REFERENCE.md](docs/CONFIG_REFERENCE.md)** - Config schema guide
  - *User-friendly config reference*
  - All fields explained with examples
  - State, nodes, edges, global config
  - Python API reference

- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
  - *Fix problems quickly*
  - Error messages explained
  - Debugging tips and techniques
  - FAQ and patterns

- **[OBSERVABILITY.md](docs/OBSERVABILITY.md)** - Monitoring and tracking workflows (v0.1+)
  - *Track execution metrics and costs*
  - MLFlow integration and setup
  - Cost tracking and reporting
  - Docker integration with MLFlow UI
  - OpenTelemetry and Prometheus (v0.2+)

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Docker deployment guide (v0.1+)
  - *Deploy workflows as microservices*
  - One-command deployment
  - FastAPI server with sync/async execution
  - Environment variable handling
  - Container management and optimization

### Developer Guides

- **[SETUP.md](SETUP.md)** - Development setup guide
  - *How to get the project running*
  - Environment setup
  - Dependencies installation
  - Running tests

---

## 🤝 Contributing

This project is in **active development** (v0.1 alpha).

We're not accepting external contributions yet, but you can:
- ⭐ Star the repo to follow progress
- 📝 Open issues for bugs or feature requests
- 💬 Join discussions

---

## 🎯 Use Cases

### Research & Analysis
```yaml
# Multi-step research workflow
nodes:
  - id: search
    tools: [serper_search]
  - id: analyze
  - id: summarize
```

### Content Generation
```yaml
# Blog post pipeline
nodes:
  - id: outline
  - id: draft
  - id: review
  - id: polish
```

### Data Processing
```yaml
# ETL workflow
nodes:
  - id: extract
  - id: transform
  - id: validate
  - id: load
```

### Automation
```yaml
# Email triage
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
- Infrastructure as Code (Terraform, Docker Compose)
- GitHub Actions (config-driven CI/CD)
- LangGraph (graph-based agent execution)
- DSPy (prompt optimization)

---

## 📬 Contact

Questions? Ideas? Feedback?

- 📧 Email: [your.email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/configurable-agents/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/configurable-agents/discussions)

---

<div align="center">

**Made with ❤️ for the agent builder community**

*Star ⭐ this repo to follow our progress!*

</div>
