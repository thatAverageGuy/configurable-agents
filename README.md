# 🤖 Configurable Agents

> **Transform YAML into production-grade AI agent workflows**

Config-driven LLM agent runtime that turns your ideas into executable workflows in minutes, not days.

[![Status](https://img.shields.io/badge/status-alpha-orange)]()
[![Version](https://img.shields.io/badge/version-0.1.0--dev-blue)]()
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

---

## 🗺️ Roadmap

### v0.1 - Foundation ⏳ (Current - Week 1 of 6-8)
**Status**: 20% complete (4/20 tasks) | **Target**: March 2026

**What's working**:
- ✅ T-001: Project setup and structure
- ✅ T-002: Config parser (YAML + JSON support)
- ✅ T-003: Config schema (Pydantic models - Full Schema v1.0)
- ✅ T-004: Config validator (comprehensive validation with helpful errors)
- ✅ 153 tests passing (67 schema + 31 types + 29 validator + 18 parser + 5 integration + 3 setup)

**In progress**:
- ⏳ T-004.5: Runtime feature gating
- ⏳ T-005: Type system (partially complete)
- ⏳ State management
- ⏳ LLM integration (Google Gemini)
- ⏳ Linear workflow execution
- ⏳ Tool registry (web search)

**Capabilities when complete**:
- Define workflows in YAML
- Sequential node execution
- Structured outputs (Pydantic)
- Basic tool calling (Serper search)
- Parse-time validation (fail fast, save money)
- Google Gemini support

**Limitations**:
- Linear flows only (no conditionals)
- In-memory state (no persistence)
- Single LLM provider (Gemini)

---

### v0.2 - Intelligence 🔮 (+8-12 weeks)
**Advanced Control Flow**

- ✨ Conditional routing (if/else)
- 🔁 Loops and retry logic
- 🌐 Multi-LLM support (OpenAI, Anthropic, Ollama)
- 💾 State persistence and resume
- 🧩 Config composition (import/extend)

**Example**:
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

### v0.3 - Optimization 🎯 (+12-16 weeks)
**DSPy-Powered Prompt Optimization**

- 🔬 Automatic prompt optimization
- 📊 Quality metrics and evaluation
- ⚡ Parallel node execution
- 🤖 AI config generator (chatbot)
- 📦 Config marketplace

**Example**:
```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
  metric: "semantic_match"
```

---

### v0.4 - Ecosystem 🌍 (+16-24 weeks)
**Visual Tools & Deployment**

- 🎨 Visual workflow editor
- 🚀 One-click deployments
- 📈 Monitoring and observability
- 🔌 Plugin system
- 🌐 SaaS offering

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

See [docs/](docs/) for comprehensive guides.

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

### Phase 1: Foundation (4/7 complete)
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ⏳ T-005: Type System
- ⏳ T-006: State Schema Builder
- ⏳ T-007: Output Schema Builder

### Phase 2: Core Execution (0/6 complete)
- ⏳ T-008: Tool Registry
- ⏳ T-009: LLM Provider
- ⏳ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

### Phase 3: Polish & UX (0/5 complete)
- ⏳ T-014: CLI Interface
- ⏳ T-015: Example Configs
- ⏳ T-016: Documentation
- ⏳ T-017: Integration Tests
- ⏳ T-018: Error Messages

### Phase 4: DSPy Verification (0/2 complete)
- ⏳ T-019: DSPy Integration Test
- ⏳ T-020: Structured Output + DSPy

**Next up**: T-004.5 (Runtime Feature Gating - Reject unsupported features)

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
  - All 20 tasks for v0.1 with acceptance criteria
  - Dependencies and estimates
  - Current progress tracker (2/20 complete)

- **[DISCUSSION.md](docs/DISCUSSION.md)** - Project status (living document)
  - *Current state and recent changes*
  - What works now vs. in progress
  - Known issues and blockers
  - Updated weekly

### Architecture Decisions

- **[Architecture Decision Records](docs/adr/)** - Design decisions and rationale
  - *Why we made specific choices*
  - 9 ADRs covering all major decisions
  - Immutable history (append-only)
  - Alternatives considered with tradeoffs

### Getting Started

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
