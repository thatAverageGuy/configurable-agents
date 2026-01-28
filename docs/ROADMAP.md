# Roadmap

**Product evolution from v0.1 to v0.4**

This document outlines the planned features, timeline, and version availability for Configurable Agents.

---

## Version Overview

| Version | Status | Timeline | Theme | Key Features |
|---------|--------|----------|-------|--------------|
| **v0.1** | 🔄 In Progress (80%) | March 2026 | Foundation | Linear flows, structured outputs, Gemini |
| **v0.2** | 📋 Planned | Q2 2026 (+8-12 weeks) | Intelligence | Conditionals, loops, multi-LLM |
| **v0.3** | 🔮 Future | Q3 2026 (+12-16 weeks) | Optimization | DSPy, parallel execution |
| **v0.4** | 🌟 Vision | Q4 2026 (+16-24 weeks) | Ecosystem | Visual tools, deployment, SaaS |

---

## v0.1 - Foundation (Current)

**Status:** 80% complete (16/20 tasks) | **Target:** March 2026

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
- 443 tests passing
- Comprehensive error messages
- "Did you mean?" suggestions for typos
- Example workflows with detailed READMEs

### Limitations

❌ **Not available in v0.1:**
- Conditional routing (if/else)
- Loops and retry logic
- Multiple LLM providers (only Gemini)
- State persistence (in-memory only)
- Parallel execution
- DSPy optimization

### Remaining Work (4 tasks)

- ⏳ **T-016:** Documentation (this file!)
- ⏳ **T-017:** Integration tests
- ⏳ **T-018:** Error message improvements
- ⏳ **T-019-020:** DSPy verification tests

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
| Docker | ⚠️ Manual | ✅ | ✅ | ✅ |
| Cloud deployment | ❌ | ❌ | ❌ | ✅ |
| SaaS platform | ❌ | ❌ | ❌ | ✅ |
| **Tooling** |
| Visual editor | ❌ | ❌ | ❌ | ✅ |
| AI config generator | ❌ | ❌ | ✅ | ✅ |
| Monitoring | ⚠️ Logs | ⚠️ MLFlow | ✅ | ✅ |
| Observability | ⚠️ Basic | ⚠️ MLFlow | ✅ | ✅ |

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

Phase 1:  Foundation (6-8 weeks)
Phase 2:  Intelligence (8-12 weeks)
Phase 3:  Optimization (12-16 weeks)
Phase 4:  Ecosystem (16-24 weeks)
```

**Current:** v0.1 - 80% complete (16/20 tasks)

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
- [ ] All Phase 3 tasks complete (2/5) ⏳
  - [x] T-014: CLI ✅
  - [x] T-015: Examples ✅
  - [ ] T-016: Docs ⏳
  - [ ] T-017: Integration tests
  - [ ] T-018: Error messages
- [ ] All Phase 4 tasks complete (0/2)
  - [ ] T-019: DSPy integration test
  - [ ] T-020: Structured output + DSPy test
- [ ] 443+ tests passing ✅
- [ ] Documentation complete
- [ ] Example workflows working
- [ ] Installation tested on Windows/Mac/Linux
- [ ] Performance benchmarks completed
- [ ] Security review passed

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
