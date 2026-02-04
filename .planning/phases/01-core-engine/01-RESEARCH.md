# Phase 1: Core Engine - Research

**Researched:** 2026-02-03
**Domain:** Multi-provider LLM orchestration, storage abstraction, advanced control flow
**Confidence:** HIGH

## Summary

Phase 1 requires building three interconnected systems: (1) a pluggable storage abstraction layer using the Repository Pattern with SQLite as default, (2) multi-LLM provider support via LiteLLM for unified access to OpenAI, Anthropic, Gemini, and Ollama, and (3) advanced control flow (branching, loops, parallelism) using LangGraph's conditional edges and Send objects.

The standard approach in 2026 is Repository Pattern for storage (SQLAlchemy 2.0 + abstract interfaces), LiteLLM as the unified LLM gateway (OpenAI-compatible interface for 100+ providers), and LangGraph's native conditional_edges + Send objects for control flow. MLflow Tracing provides OpenTelemetry-compatible observability with per-node metrics tracking.

**Primary recommendation:** Use LiteLLM for multi-provider abstraction (already decided in STATE.md), implement Repository Pattern with SQLAlchemy 2.0 for storage, leverage LangGraph's built-in conditional edges for branching/loops, and integrate MLflow Tracing for per-node observability.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LiteLLM | 1.80.16+ | Multi-LLM provider gateway | Industry standard for unified LLM access; OpenAI-compatible interface for 100+ providers; built-in cost tracking |
| SQLAlchemy | 2.0.46 | Database abstraction layer | Python's de facto ORM/database toolkit; mature dialect system for pluggable backends |
| LangGraph | 0.0.20+ | Workflow execution engine | LangChain's native orchestration framework with first-class support for conditional branching, loops, parallelism |
| MLflow | 3.9+ | Observability and tracing | OpenTelemetry-compatible tracing for GenAI workflows; 20+ framework integrations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | 0.19+ | Async SQLite driver | When using async workflows with SQLite backend |
| asyncpg | 0.29+ | Async PostgreSQL driver | When scaling to PostgreSQL with async support |
| psycopg2 | 2.9+ | PostgreSQL driver | Synchronous PostgreSQL connections |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LiteLLM | Direct provider SDKs | More control but lose unified interface, cost tracking, fallback logic |
| Repository Pattern | Direct SQLAlchemy models | Simpler initially but hard to swap backends, poor testability |
| LangGraph control flow | Custom state machines | More control but reinventing wheels, no DSPy compatibility |

**Installation:**
```bash
pip install litellm>=1.80.16 sqlalchemy>=2.0.46 langgraph>=0.0.20 mlflow>=3.9
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── storage/              # Storage abstraction layer
│   ├── base.py          # Abstract repository interfaces
│   ├── sqlite.py        # SQLite implementation
│   └── models.py        # SQLAlchemy ORM models
├── llm/                 # LLM provider integration
│   ├── provider.py      # LiteLLM wrapper (existing, extend)
│   ├── cost_tracker.py  # Per-provider cost tracking
│   └── fallback.py      # Retry/fallback logic
├── runtime/             # Execution runtime (existing, extend)
│   ├── control_flow.py  # Conditional/loop routing functions
│   └── parallel.py      # Send object factories for parallelism
└── observability/       # Tracing and metrics (existing, extend)
    └── tracer.py        # MLflow tracing integration
```

### Pattern 1: Repository Pattern for Storage Abstraction
**What:** Decouple domain logic from persistence by abstracting storage behind add/get/update/delete methods
**When to use:** When supporting multiple storage backends (SQLite, PostgreSQL, Redis)
**Example:**
```python
# Source: https://www.cosmicpython.com/book/chapter_02_repository.html
from abc import ABC, abstractmethod
from typing import Optional

class AbstractWorkflowRepository(ABC):
    """Abstract storage interface for workflows"""

    @abstractmethod
    def add(self, workflow: Workflow) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, workflow_id: str) -> Optional[Workflow]:
        raise NotImplementedError

    @abstractmethod
    def list_active(self) -> list[Workflow]:
        raise NotImplementedError

class SQLiteWorkflowRepository(AbstractWorkflowRepository):
    """SQLite implementation"""

    def __init__(self, session):
        self.session = session

    def add(self, workflow: Workflow) -> None:
        self.session.add(workflow)
        self.session.commit()

    def get(self, workflow_id: str) -> Optional[Workflow]:
        return self.session.query(Workflow).filter_by(id=workflow_id).one_or_none()
```

### Pattern 2: LiteLLM Provider Abstraction
**What:** Unified OpenAI-compatible interface for multiple LLM providers
**When to use:** When supporting OpenAI, Anthropic, Gemini, Ollama, etc.
**Example:**
```python
# Source: https://docs.litellm.ai/
from litellm import completion

def call_llm(provider: str, model: str, messages: list) -> dict:
    """Unified LLM call across providers"""
    # LiteLLM handles provider-specific formatting
    response = completion(
        model=f"{provider}/{model}",  # e.g., "openai/gpt-4", "ollama_chat/llama3"
        messages=messages,
        stream=False
    )
    return {
        "content": response.choices[0].message.content,
        "usage": response.usage,
        "cost": response._hidden_params.get("response_cost", 0)
    }
```

### Pattern 3: LangGraph Conditional Branching
**What:** Route execution to different nodes based on state evaluation
**When to use:** When implementing if/else logic or branching workflows
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api
from langgraph.graph import StateGraph, END

def routing_function(state: dict) -> str:
    """Determine next node based on state"""
    if state.get("quality_score", 0) > 0.8:
        return "approve"
    elif state.get("retry_count", 0) < 3:
        return "retry"
    else:
        return END

graph = StateGraph(state_schema)
graph.add_node("evaluate", evaluate_node)
graph.add_node("approve", approve_node)
graph.add_node("retry", retry_node)

# Add conditional edge with routing function
graph.add_conditional_edges("evaluate", routing_function)
```

### Pattern 4: LangGraph Parallel Execution with Send
**What:** Execute multiple node instances concurrently with different state
**When to use:** Map-reduce patterns, fan-out/fan-in, data parallelism
**Example:**
```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api
from langgraph.types import Send

def continue_to_workers(state: dict) -> list[Send]:
    """Fan-out to multiple parallel workers"""
    return [
        Send("process_item", {"item": item, "index": i})
        for i, item in enumerate(state["items"])
    ]

graph.add_conditional_edges("fanout", continue_to_workers)
# All Send targets execute in parallel, results merged by reducer
```

### Pattern 5: MLflow Tracing for Per-Node Metrics
**What:** Capture latency, tokens, cost for each node execution
**When to use:** Production observability, debugging, cost optimization
**Example:**
```python
# Source: https://mlflow.org/docs/latest/genai/tracing/
import mlflow

@mlflow.trace(name="node_execution", span_type="AGENT")
def execute_node(state: dict, node_config: dict) -> dict:
    """Execute node with automatic tracing"""
    # MLflow captures: latency, inputs, outputs, metadata
    result = call_llm(node_config["provider"], node_config["model"], messages)

    # Log custom metrics
    mlflow.log_metrics({
        "input_tokens": result["usage"].prompt_tokens,
        "output_tokens": result["usage"].completion_tokens,
        "cost": result["cost"]
    })

    return result
```

### Anti-Patterns to Avoid
- **Direct database coupling:** Don't import SQLAlchemy models directly in domain logic; use repository interfaces
- **Provider-specific code in nodes:** Don't write `if provider == "openai"` in node logic; LiteLLM abstracts this
- **Manual parallelism:** Don't use threading/multiprocessing for parallel nodes; use LangGraph's Send objects
- **Synchronous tracing in hot path:** Don't use blocking tracing calls; enable async logging in MLflow

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM abstraction | Custom provider wrappers | LiteLLM | Handles 100+ providers, cost tracking, retries, fallbacks, streaming; 8ms P95 latency |
| Storage migration | Manual SQL for each backend | SQLAlchemy dialects | Mature dialect system handles PostgreSQL, SQLite, MySQL differences; production-tested |
| Parallel execution | threading.Pool, asyncio.gather | LangGraph Send objects | Built-in state management, error handling, checkpointing, superstep semantics |
| Cost tracking | Manual pricing lookups | LiteLLM cost_per_token | Live pricing API, automatic updates, multi-provider support |
| Workflow tracing | Custom logging | MLflow Tracing | OpenTelemetry-compatible, framework integrations, async logging, PII masking |

**Key insight:** All five areas (multi-provider, storage, parallelism, cost, tracing) have mature, production-tested libraries. Building custom solutions wastes time and introduces bugs that these libraries have already solved.

## Common Pitfalls

### Pitfall 1: LiteLLM Database Performance Degradation at Scale
**What goes wrong:** LiteLLM stores request logs in PostgreSQL; at 1M+ logs, queries slow down LLM API requests
**Why it happens:** LiteLLM's default logging setup doesn't implement log rotation or archival; database fills with historical logs
**How to avoid:** For production, disable LiteLLM's database logging and use MLflow Tracing instead; if using LiteLLM proxy, configure DynamoDB or blob storage for logs
**Warning signs:** LLM requests taking >1s when they should be <100ms; PostgreSQL CPU spikes; growing database size

### Pitfall 2: LangGraph Parallel State Update Conflicts
**What goes wrong:** When multiple parallel nodes update the same state key without a reducer, updates are lost or overwritten
**Why it happens:** LangGraph applies all parallel updates simultaneously; without reducers, last-write-wins
**How to avoid:** Define reducer functions for state keys updated by parallel nodes (e.g., `add_messages`, `extend_list`, `merge_dicts`)
**Warning signs:** Missing data after parallel execution; non-deterministic results; state smaller than expected

### Pitfall 3: SQLAlchemy 2.0 Migration - Unexpected Transaction Auto-Start
**What goes wrong:** `conn.execute()` now automatically starts a transaction; using `conn.begin()` after execute raises "transaction already initialized"
**Why it happens:** SQLAlchemy 2.0 changed transaction semantics for safety; legacy code patterns break
**How to avoid:** Use context managers: `with engine.begin() as conn:` or explicitly manage transactions; read migration guide
**Warning signs:** "This Connection has already begun a transaction" errors; unexpected rollbacks

### Pitfall 4: Ollama Local Model Streaming Issues
**What goes wrong:** Ollama models return empty responses or hang when using LiteLLM's default `ollama/` prefix
**Why it happens:** `/api/generate` endpoint (default) has different behavior than `/api/chat` endpoint
**How to avoid:** Use `ollama_chat/` prefix instead of `ollama/` for better chat responses; set `api_base="http://localhost:11434"` explicitly
**Warning signs:** Empty responses from local models; timeouts; models work with ollama CLI but not LiteLLM

### Pitfall 5: MLflow Tracing Performance Impact in Production
**What goes wrong:** Synchronous tracing adds 50-200ms latency to each LLM call; throughput drops significantly
**Why it happens:** Default MLflow tracing blocks on I/O to write traces; multiplies across workflow nodes
**How to avoid:** Enable async logging: `mlflow.config.enable_async_logging(True)`; use lightweight SDK (`mlflow-tracing`); configure sampling
**Warning signs:** Workflow latency 2-3x higher than expected; tracing logs show slow writes; P95 latency >1s

### Pitfall 6: Repository Pattern Abstraction Leakage
**What goes wrong:** SQLAlchemy-specific code (sessions, queries) leaks into domain logic; defeats purpose of abstraction
**Why it happens:** Developers bypass repository interface for "just this one query"; spreads over time
**How to avoid:** Strict dependency inversion: domain imports repository interface only, never SQLAlchemy; code reviews enforce
**Warning signs:** `from sqlalchemy` in domain files; session passed to business logic; unit tests require database

## Code Examples

Verified patterns from official sources:

### Multi-Provider LLM Setup with Cost Tracking
```python
# Source: https://docs.litellm.ai/docs/completion/token_usage
import litellm
from typing import Dict, Any

def setup_litellm_providers() -> None:
    """Configure LiteLLM for multiple providers"""
    # Set API keys via environment or config
    litellm.set_verbose = False  # Disable debug logs

    # Optional: Custom pricing for local models
    litellm.register_model({
        "ollama_chat/llama3": {
            "input_cost_per_token": 0.0,  # Free for local
            "output_cost_per_token": 0.0
        }
    })

def call_with_tracking(provider: str, model: str, messages: list) -> Dict[str, Any]:
    """Call LLM and extract cost/token metrics"""
    response = litellm.completion(
        model=f"{provider}/{model}",
        messages=messages
    )

    return {
        "content": response.choices[0].message.content,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
        "cost_usd": litellm.completion_cost(response)
    }
```

### SQLite Repository with SQLAlchemy 2.0
```python
# Source: https://docs.sqlalchemy.org/en/20/ + https://www.cosmicpython.com/book/chapter_02_repository.html
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from typing import Optional

class Base(DeclarativeBase):
    pass

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32))

class SQLiteWorkflowRepository:
    """SQLite implementation of workflow storage"""

    def __init__(self, db_path: str = "workflows.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def add(self, workflow: WorkflowRun) -> None:
        with Session(self.engine) as session:
            session.add(workflow)
            session.commit()

    def get(self, workflow_id: str) -> Optional[WorkflowRun]:
        with Session(self.engine) as session:
            return session.get(WorkflowRun, workflow_id)
```

### LangGraph Loop with Retry Logic
```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    attempt: int
    max_attempts: int
    success: bool
    result: str

def should_retry(state: State) -> str:
    """Routing function for retry loop"""
    if state["success"]:
        return "finish"
    elif state["attempt"] < state["max_attempts"]:
        return "process"
    else:
        return "handle_failure"

def process_node(state: State) -> dict:
    """Node that may need retries"""
    # Attempt processing
    result = do_work()
    return {
        "attempt": state["attempt"] + 1,
        "success": result.is_valid(),
        "result": result.data
    }

# Build graph with loop
graph = StateGraph(State)
graph.add_node("process", process_node)
graph.add_node("finish", finish_node)
graph.add_node("handle_failure", failure_node)

graph.set_entry_point("process")
graph.add_conditional_edges("process", should_retry)
graph.add_edge("finish", END)
graph.add_edge("handle_failure", END)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct provider SDKs | LiteLLM unified gateway | 2024-2025 | Reduced code by 70%, automatic cost tracking, easy fallbacks |
| SQLAlchemy 1.4 `bind` param | SQLAlchemy 2.0 context managers | Jan 2023 (v2.0.0) | Safer transactions, better typing, breaking changes |
| Manual threading for parallelism | LangGraph Send objects | 2024 (LangGraph 0.0.20+) | Built-in state management, checkpointing, error handling |
| Custom LLM logging | MLflow Tracing | 2024-2025 (MLflow 2.9+) | OpenTelemetry standard, async, 20+ framework integrations |
| In-memory workflow state | Pluggable storage backends | Current best practice | Scalability, persistence, multi-instance support |

**Deprecated/outdated:**
- SQLAlchemy 1.x `MetaData(bind=engine)`: Use `metadata.reflect(bind=engine)` instead
- LiteLLM `ollama/` prefix for chat: Use `ollama_chat/` for better responses
- Synchronous MLflow tracing: Enable async logging for production
- Global LangGraph state: Use reducers for parallel execution safety

## Open Questions

Things that couldn't be fully resolved:

1. **LiteLLM Production Scalability**
   - What we know: LiteLLM has documented issues at 100K+ requests/day with database logging; community recommends disabling DB logging
   - What's unclear: Whether using only the SDK (not proxy) avoids these issues; if MLflow Tracing is sufficient replacement
   - Recommendation: Use LiteLLM SDK only (not proxy), disable any DB logging, rely on MLflow for observability

2. **Storage Backend Switch Complexity**
   - What we know: SQLAlchemy abstracts database dialects; repository pattern abstracts SQLAlchemy
   - What's unclear: How much code change needed to swap SQLite → PostgreSQL in practice; whether connection pooling config differs significantly
   - Recommendation: Build with SQLite first, test PostgreSQL switch early (Phase 2), document migration checklist

3. **LangGraph Parallel Execution Limits**
   - What we know: LangGraph executes parallel nodes in "supersteps"; all succeed or all fail; Send objects create independent execution paths
   - What's unclear: Practical limits on parallel Send count; performance characteristics at 100+ parallel nodes; memory usage patterns
   - Recommendation: Start with 10-20 parallel nodes max, test scalability explicitly, use Send for map-reduce only

## Sources

### Primary (HIGH confidence)
- LiteLLM official docs (https://docs.litellm.ai/) - Provider setup, cost tracking, token usage
- LangGraph API docs (https://docs.langchain.com/oss/python/langgraph/graph-api) - Conditional edges, Send objects, control flow
- SQLAlchemy 2.0 docs (https://docs.sqlalchemy.org/en/20/) - ORM patterns, migration guide, dialects
- MLflow Tracing docs (https://mlflow.org/docs/latest/genai/tracing/) - Observability, async logging, per-node metrics
- Repository Pattern (Cosmic Python) (https://www.cosmicpython.com/book/chapter_02_repository.html) - Storage abstraction patterns

### Secondary (MEDIUM confidence)
- [LiteLLM production issues](https://dev.to/debmckinney/youre-probably-going-to-hit-these-litellm-issues-in-production-59bg) - Verified with GitHub issues (800+ open)
- [LangGraph state management guide](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025) - Verified with official docs
- [SQLAlchemy 2.0 migration gotchas](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html) - Official migration guide
- [LiteLLM with Ollama guide](https://apidog.com/blog/litellm-ollama/) - Verified with official LiteLLM docs

### Tertiary (LOW confidence)
- [Repository Pattern in Python](https://pybit.es/articles/repository-pattern-in-python/) - General pattern guide, not library-specific
- [SQLite vs PostgreSQL 2026](https://www.selecthub.com/relational-database-solutions/postgresql-vs-sqlite/) - General comparison, not implementation-focused

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified through official docs and Context7-equivalent sources; versions confirmed via PyPI
- Architecture: HIGH - Patterns verified through official documentation (LangGraph, SQLAlchemy, Cosmic Python); code examples tested in community
- Pitfalls: MEDIUM - Issues documented in multiple sources but based primarily on community reports; LiteLLM production issues have 800+ GitHub issues confirming

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - relatively stable ecosystem, but LiteLLM evolves quickly)
