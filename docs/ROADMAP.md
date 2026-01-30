# Roadmap

**Product evolution from v0.1 to v0.4**

This document outlines the planned features, timeline, and version availability for Configurable Agents.

---

## Version Overview

| Version | Status | Timeline | Theme | Key Features |
|---------|--------|----------|-------|--------------|
| **v0.1** | 🔄 In Progress (67%) | March 2026 | Production Ready | Linear flows, structured outputs, **observability, Docker deployment** |
| **v0.2** | 📋 Planned | Q2 2026 (+8-12 weeks) | Intelligence | Conditionals, loops, multi-LLM, error improvements |
| **v0.3** | 🔮 Future | Q3 2026 (+12-16 weeks) | Optimization | DSPy, parallel execution, distributed tracing |
| **v0.4** | 🌟 Vision | Q4 2026 (+16-24 weeks) | Ecosystem | Visual tools, cloud deployment, SaaS |

---

## v0.1 - Production Ready (Current)

**Status:** 67% complete (18/27 tasks) | **Target:** March 2026

### What's Working Now ✅

```bash
# Install and run workflows
pip install -e .
configurable-agents run workflow.yaml --input topic="AI Safety"

# Validate configs before running
configurable-agents validate workflow.yaml

# Python API
from configurable_agents.runtime import run_workflow
result = run_workflow("workflow.yaml", {"topic": "AI"})
```

### What's Coming Next ⏳

```bash
# MLFlow observability (T-018 to T-021)
configurable-agents run workflow.yaml --input topic="AI" --mlflow
mlflow ui  # View traces, costs, prompts

# Docker deployment (T-022 to T-024)
configurable-agents deploy workflow.yaml
# → Runs on http://localhost:8000 (API) + http://localhost:5000 (MLFlow UI)
```

### Core Features

#### ✅ Config-Driven Architecture
- YAML/JSON config parsing
- Full Pydantic schema validation
- Parse-time error detection (fail fast, save money)
- Type-safe state and outputs

#### ✅ Linear Workflows
- Sequential node execution (START → node1 → node2 → END)
- No branching or loops (coming in v0.2)
- Clear, predictable execution

#### ✅ Structured Outputs
- Type-enforced LLM responses
- Automatic retry on validation failures
- Support for: str, int, float, bool, list, dict, nested objects

#### ✅ LLM Integration
- Google Gemini (gemini-1.5-flash, gemini-1.5-pro)
- Configurable temperature, max_tokens
- Node-level LLM overrides

#### ✅ Tool Integration
- Web search via Serper API
- Extensible tool registry
- Easy to add custom tools

#### ✅ Command-Line Interface
- `run` command - Execute workflows
- `validate` command - Check configs
- Colored output, verbose mode
- Smart input parsing (JSON, numbers, booleans)

#### ✅ Developer Experience
- 468 tests passing (449 unit + 19 integration)
- Comprehensive error messages
- "Did you mean?" suggestions for typos
- Example workflows with detailed READMEs

#### ⏳ MLFlow Observability (T-018 to T-021 - In Progress)
- Track workflow execution (params, metrics, artifacts)
- Cost tracking (tokens, $ per run)
- Per-node traces (prompts, responses, retries)
- MLFlow UI dashboard (http://localhost:5000)
- Local-first (file-based), enterprise-ready (PostgreSQL, S3, Databricks)
- DSPy optimization support (v0.3)

```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "file://./mlruns"
      experiment_name: "production_workflows"
```

#### ⏳ Docker Deployment (T-022 to T-024 - In Progress)
- One-command deployment (`configurable-agents deploy workflow.yaml`)
- Persistent FastAPI server (sync/async execution)
- MLFlow UI included in container
- Optimized images (<200MB target)
- Environment variable management (CLI + Streamlit UI)
- Health checks, OpenAPI docs auto-generated

```bash
configurable-agents deploy workflow.yaml
# → http://localhost:8000 (workflow API)
# → http://localhost:5000 (MLFlow UI)

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Safety"}'
```

### Limitations

❌ **Not available in v0.1:**
- Conditional routing (if/else) - coming in v0.2
- Loops and retry logic - coming in v0.2
- Multiple LLM providers (only Gemini) - v0.2
- State persistence (in-memory only) - v0.2
- Parallel execution - v0.3
- DSPy optimization - v0.3
- OpenTelemetry distributed tracing - v0.2
- Prometheus monitoring - v0.3

### Remaining Work (7 tasks for v0.1)

**Observability (4 tasks):**
- ⏳ **T-018:** MLFlow Integration Foundation (2 days)
- ⏳ **T-019:** MLFlow Instrumentation (3 days)
- ⏳ **T-020:** Cost Tracking & Reporting (2 days)
- ⏳ **T-021:** Observability Documentation (2 days)

**Docker Deployment (3 tasks):**
- ⏳ **T-022:** Artifact Generator & Templates (2 days)
- ⏳ **T-023:** FastAPI Server with Sync/Async (3 days)
- ⏳ **T-024:** CLI Deploy Command & Streamlit Integration (3 days)

**Deferred to v0.2+:**
- **T-025:** Error message improvements (was T-018)
- **T-026/T-027:** DSPy verification tests (was T-019/T-020)

### Example Use Cases

```yaml
# Research & Analysis
nodes:
  - id: search
    tools: [serper_search]
  - id: analyze
  - id: summarize

# Content Generation
nodes:
  - id: outline
  - id: draft
  - id: review
  - id: polish
```

---

## v0.2 - Intelligence

**Target:** Q2 2026 (8-12 weeks after v0.1)

### New Features

#### 🔀 Conditional Routing

Branch based on state values:

```yaml
edges:
  - from: review
    routes:
      - condition: "{state.score} >= 7"
        to: END
      - condition: "{state.score} < 7"
        to: write  # Retry
```

**Use cases:**
- Quality gates (retry if score too low)
- Route based on classification
- Error handling paths

#### 🔁 Loops & Retry Logic

Iterate until condition met:

```yaml
edges:
  - from: generate
    to: validate
  - from: validate
    routes:
      - condition: "{state.is_valid}"
        to: END
      - condition: "not {state.is_valid}"
        to: generate
    max_iterations: 5
```

**Use cases:**
- Retry with feedback
- Iterative refinement
- Multi-attempt generation

#### 🌐 Multi-LLM Support

Use different LLM providers:

```yaml
config:
  llm:
    provider: openai  # or anthropic, ollama
    model: "gpt-4"

nodes:
  - id: creative_task
    llm:
      provider: anthropic
      model: "claude-3-opus"
```

**Supported providers:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3)
- Ollama (local models)
- Google Gemini (existing)

#### 💾 State Persistence

Resume workflows from checkpoints:

```yaml
config:
  execution:
    persistence:
      enabled: true
      backend: file  # or redis, postgres
      checkpoint_path: "./checkpoints"
```

**Use cases:**
- Long-running workflows
- Resume after failures
- Debug specific nodes

#### 🧩 Config Composition

Reuse config blocks:

```yaml
# common.yaml
common_llm: &llm_config
  provider: google
  model: gemini-1.5-flash
  temperature: 0.7

# workflow.yaml
import: [common.yaml]

config:
  llm: *llm_config
```

**Use cases:**
- Share configs across workflows
- Team standardization
- DRY principle

### Breaking Changes

⚠️ None! Config v1.0 remains compatible.

### Migration

No migration needed. v0.1 configs work in v0.2.

---

## v0.3 - Optimization

**Target:** Q3 2026 (12-16 weeks after v0.2)

### New Features

#### 🔬 DSPy Optimization

Automatic prompt optimization:

```yaml
optimization:
  enabled: true
  strategy: BootstrapFewShot
  metric: semantic_match
  training_data: ./examples.json

nodes:
  - id: classify
    prompt: "Classify this: {state.text}"  # Optimized automatically
    optimize: true
```

**Benefits:**
- Better accuracy
- Fewer retries
- Lower costs (shorter prompts)

#### 📊 Evaluation Metrics

Built-in quality metrics:

```yaml
optimization:
  metrics:
    - type: semantic_match
      target: 0.9
    - type: exact_match
    - type: cost_per_run
      budget: 0.01
```

#### ⚡ Parallel Execution

Run independent nodes simultaneously:

```yaml
nodes:
  - id: task1
    parallel_group: research
  - id: task2
    parallel_group: research
  - id: combine
    depends_on: [task1, task2]
```

**Benefits:**
- Faster execution
- Better resource utilization

#### 🤖 AI Config Generator

Chatbot to create configs:

```bash
configurable-agents generate

> "I want to research topics and write articles"

✓ Generated: article_writer.yaml
```

#### 📦 Config Marketplace

Share and discover workflows:

```bash
configurable-agents discover "content generation"

Found 12 workflows:
  - article_writer (★ 4.5, 1.2k uses)
  - blog_post_generator (★ 4.2, 800 uses)
  ...

configurable-agents install article_writer
```

### Breaking Changes

⚠️ None! Config v1.0 remains compatible.

---

## v0.4 - Ecosystem

**Target:** Q4 2026 (16-24 weeks after v0.3)

### New Features

#### 🎨 Visual Workflow Editor

Web-based config builder:
- Drag-and-drop nodes
- Visual edge connections
- Real-time validation
- Export to YAML

#### 🚀 One-Click Deployments

Deploy to cloud platforms:

```bash
configurable-agents deploy workflow.yaml --platform ecs

✓ Deployed to AWS ECS
✓ Endpoint: https://api.example.com/workflow
```

**Supported platforms:**
- AWS ECS
- AWS Lambda
- Google Cloud Run
- Docker Swarm

#### 📈 Monitoring & Observability

Built-in dashboards:
- Execution metrics
- Cost tracking
- Error rates
- Performance trends

```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: https://mlflow.example.com

    prometheus:
      enabled: true
      port: 9090
```

#### 🔌 Plugin System

Extend with custom plugins:

```python
# my_plugin.py
from configurable_agents.plugins import Plugin

class MyPlugin(Plugin):
    def on_node_complete(self, node_id, state):
        # Custom logic
        pass
```

```yaml
config:
  plugins:
    - name: my_plugin
      path: ./my_plugin.py
```

#### 🌐 SaaS Offering

Hosted platform:
- No installation needed
- API access
- Team collaboration
- Usage-based pricing

---

## Feature Availability Matrix

| Feature | v0.1 | v0.2 | v0.3 | v0.4 |
|---------|------|------|------|------|
| **Core** |
| YAML/JSON configs | ✅ | ✅ | ✅ | ✅ |
| Linear flows | ✅ | ✅ | ✅ | ✅ |
| Structured outputs | ✅ | ✅ | ✅ | ✅ |
| Type validation | ✅ | ✅ | ✅ | ✅ |
| CLI tool | ✅ | ✅ | ✅ | ✅ |
| Python API | ✅ | ✅ | ✅ | ✅ |
| **Control Flow** |
| Conditional routing | ❌ | ✅ | ✅ | ✅ |
| Loops | ❌ | ✅ | ✅ | ✅ |
| Parallel execution | ❌ | ❌ | ✅ | ✅ |
| **LLMs** |
| Google Gemini | ✅ | ✅ | ✅ | ✅ |
| OpenAI | ❌ | ✅ | ✅ | ✅ |
| Anthropic | ❌ | ✅ | ✅ | ✅ |
| Local (Ollama) | ❌ | ✅ | ✅ | ✅ |
| **Tools** |
| Web search | ✅ | ✅ | ✅ | ✅ |
| Custom tools | ✅ | ✅ | ✅ | ✅ |
| Tool marketplace | ❌ | ❌ | ✅ | ✅ |
| **Advanced** |
| State persistence | ❌ | ✅ | ✅ | ✅ |
| Config composition | ❌ | ✅ | ✅ | ✅ |
| DSPy optimization | ❌ | ❌ | ✅ | ✅ |
| Auto-evaluation | ❌ | ❌ | ✅ | ✅ |
| **Deployment** |
| Local execution | ✅ | ✅ | ✅ | ✅ |
| Docker (one-command) | ✅ | ✅ | ✅ | ✅ |
| Cloud deployment | ❌ | ❌ | ⚠️ Manual | ✅ |
| SaaS platform | ❌ | ❌ | ❌ | ✅ |
| **Observability** |
| MLFlow (LLM tracking) | ✅ | ✅ | ✅ | ✅ |
| Cost tracking | ✅ | ✅ | ✅ | ✅ |
| OpenTelemetry (tracing) | ❌ | ✅ | ✅ | ✅ |
| Prometheus (metrics) | ❌ | ❌ | ✅ | ✅ |
| Grafana (dashboards) | ❌ | ❌ | ✅ | ✅ |
| **Tooling** |
| Visual editor | ❌ | ❌ | ❌ | ✅ |
| AI config generator | ❌ | ❌ | ✅ | ✅ |
| Streamlit UI (basic) | ✅ | ✅ | ✅ | ✅ |

**Legend:**
- ✅ Available
- ❌ Not available
- ⚠️ Limited/manual

---

## Timeline Summary

```
2026-01 ─────────────────────────────────────> 2027-01
  │        │        │        │        │        │
  v0.1     v0.2     v0.3     v0.4
 (Mar)    (Jun)    (Sep)    (Dec)

Phase 1:  Production Ready (8-10 weeks)
Phase 2:  Intelligence (8-12 weeks)
Phase 3:  Optimization & DSPy (12-16 weeks)
Phase 4:  Ecosystem & Cloud (16-24 weeks)
```

**Current:** v0.1 - 67% complete (18/27 tasks)
**Remaining:** 3.5 weeks (Observability + Docker deployment)

---

## Design Philosophy

### No Breaking Changes

**Promise:** Config schema v1.0 will work across all versions (v0.1 → v0.4).

**How:**
- Features marked as v0.2+ in schema
- Runtime validates version compatibility
- Soft warnings for future features
- Hard errors only for truly incompatible features

### Incremental Adoption

**You can:**
- Start with v0.1 (simple workflows)
- Add conditionals in v0.2 when needed
- Enable optimization in v0.3 selectively
- Use visual tools in v0.4 optionally

**You don't have to:**
- Rewrite configs for new versions
- Learn new syntax
- Migrate data

### Community-Driven

**We'll prioritize based on:**
- User feedback
- Real-world use cases
- Community contributions
- Ecosystem needs

---

## Release Criteria

### v0.1 Release Checklist

- [x] All Phase 1 tasks complete (8/8) ✅
- [x] All Phase 2 tasks complete (6/6) ✅
- [ ] All Phase 3 tasks complete (4/11) ⏳
  - [x] T-014: CLI ✅
  - [x] T-015: Examples ✅
  - [x] T-016: Documentation ✅
  - [x] T-017: Integration Tests ✅
  - [ ] T-018: MLFlow Integration Foundation ⏳
  - [ ] T-019: MLFlow Instrumentation ⏳
  - [ ] T-020: Cost Tracking & Reporting ⏳
  - [ ] T-021: Observability Documentation ⏳
  - [ ] T-022: Docker Artifact Generator ⏳
  - [ ] T-023: FastAPI Server with Sync/Async ⏳
  - [ ] T-024: CLI Deploy Command & Streamlit Integration ⏳
- [ ] 468+ tests passing ✅
- [ ] Documentation complete ✅
- [ ] Example workflows working ✅
- [ ] Observability (MLFlow) working
- [ ] Docker deployment working
- [ ] Installation tested on Windows/Mac/Linux ✅
- [ ] Performance benchmarks completed
- [ ] Security review passed

**Deferred to v0.2+:**
- T-025: Error Message Improvements (v0.2)
- T-026: DSPy Integration Test (v0.3)
- T-027: Structured Output + DSPy Test (v0.3)

### v0.2+ Release Criteria

To be defined based on v0.1 learnings.

---

## FAQ

**Q: Will v0.1 configs work in v0.2?**
A: Yes! No breaking changes. All v0.1 features remain supported.

**Q: Can I use v0.2 features in v0.1?**
A: No. You'll get a helpful error message with timeline.

**Q: When will DSPy optimization be available?**
A: v0.3 (Q3 2026). But the schema supports it now!

**Q: Can I self-host after v0.4?**
A: Yes! SaaS is optional. Local/Docker deployment always supported.

**Q: How much will it cost?**
A: Open-source CLI is free forever. SaaS pricing TBD (usage-based).

---

## Get Involved

- **Star the repo** to follow progress
- **Open issues** for bugs or feature requests
- **Join discussions** to shape the roadmap
- **Contribute** (coming soon - contribution guide)

---

## Next Steps

- **[QUICKSTART.md](QUICKSTART.md)** - Get started now
- **[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)** - Learn the config format
- **[examples/](../examples/)** - See working examples
- **[TASKS.md](TASKS.md)** - Detailed development plan

---

*Last updated: 2026-01-28 (v0.1 in progress)*
