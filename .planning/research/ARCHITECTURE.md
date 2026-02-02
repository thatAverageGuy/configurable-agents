# Architecture Research: Agent Orchestration Platforms

**Domain:** Agent Orchestration Platforms
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

Agent orchestration platforms in 2026 follow a distinct architectural pattern that separates concerns into four primary layers: **orchestration/control plane**, **execution/worker plane**, **observability**, and **storage**. Leading platforms (LangGraph Platform, Prefect, Temporal) converge on key patterns including service discovery through registries, bidirectional agent-orchestrator communication, pluggable storage backends, and decoupled UI components. The shift toward "agent-as-microservice" architecture is accelerating, with 1,445% surge in multi-agent system inquiries from Q1 2024 to Q2 2025 (Gartner).

For the configurable-agents project, the research indicates a phased evolution from the current monolithic runtime (v0.1) toward:
1. **Control/Data Plane Separation** - Orchestrator service + Agent containers
2. **Bidirectional Registry** - Agent registration with health checks
3. **UI Sidecar Pattern** - Optional UI container (Gradio + HTMX + MLFlow)
4. **Storage Abstraction** - SQLite → PostgreSQL → Cloud backends

## Standard Architecture

### System Overview

Modern agent orchestration platforms separate into four distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CONTROL PLANE                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ Orchestrator│  │   Service    │  │    Task     │  │   API        │  │
│  │   Engine    │──│   Registry   │──│   Queue     │──│   Gateway    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  │
│         │                │                 │                │           │
├─────────┼────────────────┼─────────────────┼────────────────┼───────────┤
│         │                │                 │                │           │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌──────▼──────┐  ┌──────▼───────┐  │
│  │   Agent     │  │    Agent     │  │   Agent     │  │    Agent     │  │
│  │ Container 1 │  │ Container 2  │  │ Container N │  │  Container M │  │
│  │             │  │              │  │             │  │              │  │
│  │ (Minimal)   │  │  (Minimal)   │  │  (Minimal)  │  │   (Minimal)  │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │
│                       EXECUTION PLANE                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                       OBSERVABILITY LAYER                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐                     │
│  │   Tracing   │  │   Metrics    │  │   Logging   │                     │
│  │  (MLFlow/   │  │ (OpenTelemetry│  │ (Structured)│                     │
│  │ LangSmith)  │  │  Prometheus) │  │             │                     │
│  └─────────────┘  └──────────────┘  └─────────────┘                     │
├──────────────────────────────────────────────────────────────────────────┤
│                       STORAGE LAYER                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │   Workflow  │  │    State     │  │   Results   │  │   Metadata   │  │
│  │   Store     │  │    Store     │  │   Store     │  │   Store      │  │
│  │  (SQLite/   │  │   (Redis/    │  │   (S3/      │  │  (Postgres)  │  │
│  │  Postgres)  │  │   Postgres)  │  │   Object)   │  │              │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

OPTIONAL UI SIDECAR (Decoupled):
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │   Chat UI    │  │ Orchestration│  │  Observability│                   │
│  │   (Gradio)   │  │   Dashboard  │  │   Dashboard   │                   │
│  │              │  │   (HTMX)     │  │   (MLFlow UI) │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│              Communicates via API Gateway                                │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Orchestrator Engine** | Workflow execution, task scheduling, state management | LangGraph (graph execution), Prefect (DAG scheduler), Temporal (durable workflows) |
| **Service Registry** | Agent discovery, health checks, capability catalog | Client-side discovery (agents query registry) or Server-side (load balancer queries) |
| **Task Queue** | Work distribution, backpressure, priority queues | Redis (simple), RabbitMQ (complex), Kafka (high-throughput) |
| **API Gateway** | Request routing, authentication, rate limiting | FastAPI, Kong, Envoy |
| **Agent Container** | Execute tasks, report results, maintain heartbeat | Minimal Docker image (~50-100MB), single-purpose |
| **Tracing** | LLM call tracking, token counting, prompt/response storage | MLFlow (ML-focused), LangSmith (LangChain-native), OpenTelemetry (general) |
| **Metrics** | System health, performance counters, alerting | Prometheus + Grafana, DataDog, OpenTelemetry Collector |
| **Workflow Store** | Persist workflow definitions, execution history | SQLite (local), PostgreSQL (team), Cloud DB (enterprise) |
| **State Store** | Runtime state, checkpoints for resume | In-memory (dev), Redis (production), PostgreSQL (durable) |
| **UI Sidecar** | Optional user interfaces, deployed separately | Gradio (chat), HTMX (orchestration), MLFlow UI (observability) |

## Deployment Topology Patterns

### Pattern 1: Local Development (Single Process)

**When:** Individual developer prototyping

**Architecture:**
```
┌──────────────────────────────┐
│  Single Python Process       │
│  ┌────────────────────────┐  │
│  │ Orchestrator + Agent   │  │
│  │ (Monolithic Runtime)   │  │
│  └────────────────────────┘  │
│                              │
│  Storage: SQLite (file)      │
│  Observability: File logs    │
└──────────────────────────────┘
```

**Pros:** Zero setup, fast iteration, full debugging
**Cons:** No scalability, no multi-user support
**Example:** Current configurable-agents v0.1

---

### Pattern 2: Local Multi-Container (Docker Compose)

**When:** Team development, integration testing

**Architecture:**
```
┌─────────────────────────────────────────┐
│  Docker Compose Network                 │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ Orchestrator │  │   Agent 1    │    │
│  │  Container   │  │  Container   │    │
│  └──────┬───────┘  └──────┬───────┘    │
│         │                 │             │
│  ┌──────▼─────────────────▼───────┐    │
│  │    Shared Volume (SQLite)      │    │
│  └────────────────────────────────┘    │
│                                         │
│  Optional: UI Sidecar Container        │
└─────────────────────────────────────────┘
```

**Pros:** Isolated containers, realistic deployment testing, shared storage
**Cons:** Requires Docker, slower than single-process
**Example:** Target for configurable-agents v0.2

---

### Pattern 3: Kubernetes Cluster (Production)

**When:** Enterprise deployment, auto-scaling needed

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│  Kubernetes Cluster                                 │
│  ┌──────────────────────────────────────────────┐  │
│  │  Control Plane (Orchestrator)                │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐               │  │
│  │  │ Pod1 │  │ Pod2 │  │ Pod3 │ (replicas)    │  │
│  │  └──────┘  └──────┘  └──────┘               │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │  Agent Pool (StatefulSet/Deployment)         │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ...           │  │
│  │  │Agent1│  │Agent2│  │AgentN│ (auto-scaled) │  │
│  │  └──────┘  └──────┘  └──────┘               │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Storage: PostgreSQL (StatefulSet) or Cloud DB     │
│  Observability: OpenTelemetry → Prometheus         │
│  UI: Optional Ingress to UI Sidecar Service        │
└─────────────────────────────────────────────────────┘
```

**Pros:** Auto-scaling, high availability, production-grade
**Cons:** Complex setup, requires K8s expertise, higher cost
**Example:** Target for configurable-agents v0.4

---

### Pattern 4: Hybrid (Edge + Cloud)

**When:** Distributed agents, some on-premise, some cloud

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│  Cloud Control Plane                                │
│  ┌──────────────────────────────────────────────┐  │
│  │ Central Orchestrator                          │  │
│  └───────────┬──────────────────────────────────┘  │
│              │                                       │
│  ┌───────────▼────────┐  ┌────────────────────┐   │
│  │ Cloud Agent Pool    │  │ Observability Hub  │   │
│  └─────────────────────┘  └────────────────────┘   │
└──────────────┬──────────────────────────────────────┘
               │ (Internet)
┌──────────────▼──────────────────────────────────────┐
│  Edge Location 1          Edge Location 2           │
│  ┌──────────────┐         ┌──────────────┐          │
│  │ Local Agent  │         │ Local Agent  │          │
│  │ (registers   │         │ (registers   │          │
│  │  with cloud) │         │  with cloud) │          │
│  └──────────────┘         └──────────────┘          │
└─────────────────────────────────────────────────────┘
```

**Pros:** Low-latency edge execution, centralized monitoring
**Cons:** Network dependency, complexity in failure modes
**Example:** Future enterprise pattern (v0.4+)

---

## Service Discovery Patterns

### Pattern 1: Client-Side Discovery

**How it works:**
1. Agent starts and queries **Service Registry** for orchestrator location
2. Agent caches location and makes direct requests
3. Agent handles load balancing (if multiple orchestrators)

**Implementation:**
```python
# Agent startup sequence
registry_client = RegistryClient("http://registry:8500")
orchestrator_endpoints = registry_client.query(service="orchestrator")
orchestrator = random.choice(orchestrator_endpoints)  # Client-side LB
agent.connect(orchestrator)
```

**Pros:** Simple, no intermediary, agents control routing
**Cons:** Agents need discovery logic, more complex agent code
**Used by:** Consul, Eureka, etcd

---

### Pattern 2: Server-Side Discovery

**How it works:**
1. Agent sends request to **Load Balancer** (fixed location)
2. Load balancer queries registry for healthy orchestrators
3. Load balancer forwards request to selected orchestrator

**Implementation:**
```python
# Agent startup sequence
LOAD_BALANCER = "http://lb.cluster.local:8080"  # Well-known address
agent.connect(LOAD_BALANCER)  # Load balancer handles discovery
```

**Pros:** Simple agent code, centralized routing logic
**Cons:** Load balancer becomes single point of failure
**Used by:** Kubernetes (kube-proxy), AWS ELB, Envoy

---

### Pattern 3: Bidirectional Registration

**How it works:**
1. **Orchestrator → Agent:** Orchestrator knows agents via registry
2. **Agent → Orchestrator:** Agent registers itself on startup
3. Heartbeat mechanism keeps registry up-to-date

**Implementation:**
```python
# Agent registration
def register_agent(registry, agent_id, capabilities):
    registry.register(
        service_id=agent_id,
        address=agent.address,
        port=agent.port,
        metadata={
            "capabilities": capabilities,
            "version": agent.version,
            "max_concurrent_tasks": 5
        },
        health_check={
            "http": f"http://{agent.address}/health",
            "interval": "10s",
            "timeout": "2s"
        }
    )

    # Heartbeat loop
    while True:
        registry.heartbeat(agent_id)
        time.sleep(5)
```

**Orchestrator perspective:**
```python
# Orchestrator discovering agents
def schedule_task(task):
    agents = registry.query(
        service="agent",
        filter=f"capabilities contains '{task.required_capability}'"
    )
    healthy_agents = [a for a in agents if a.health_status == "passing"]
    selected = load_balance(healthy_agents)
    selected.submit_task(task)
```

**Pros:** Both sides can initiate, flexible routing, health-aware
**Cons:** More complex protocol, requires registry service
**Used by:** Prefect (work pools), Temporal (task queues), LangGraph Platform

---

## Data Flow Patterns

### Request Flow (Orchestrated Workflow)

```
[User/API Request]
    ↓
[API Gateway] ───────────────────────────────────────────┐
    ↓                                                     │
[Orchestrator Engine]                                     │
    ├─ Parse workflow config                             │
    ├─ Validate against schema                           │
    ├─ Build execution graph                             │
    └─ Schedule tasks                                     │
         ↓                                                │
[Task Queue] ← enqueue(task_1, task_2, ...)              │
    ↓                                                     │
[Service Registry] ← query(agents with capability X)     │
    ↓                                                     │
[Select Agent(s)]                                         │
    ↓                                                     │
[Agent Container 1]                                       │
    ├─ Receive task                                       │
    ├─ Execute (LLM call, tools)                          │
    ├─ Publish intermediate results                       │
    └─ Report completion                                  │
         ↓                                                │
[State Store] ← update(workflow_state, agent_results)    │
    ↓                                                     │
[Orchestrator Engine] ← task_complete event              │
    ├─ Check workflow completion                          │
    └─ If done: aggregate results ────────────────────────┘
         ↓
[API Gateway] ← return(final_output)
    ↓
[User/API Response]
```

### Observability Flow

```
[Agent Container]
    ├─ LLM call initiated
    ├─ Create trace span
    ├─ Log: {timestamp, node_id, prompt, model}
    └─ Emit metrics: {latency, token_count}
         ↓
[Tracing Backend] ← MLFlow.start_run() or OTel.start_span()
    ├─ Store prompt/response artifacts
    ├─ Calculate cost (tokens × rate)
    └─ Link to parent workflow trace
         ↓
[Metrics Backend] ← Prometheus scrapes /metrics
    ├─ token_count_total{agent="agent1", model="gemini"}
    ├─ llm_call_duration_seconds{agent="agent1"}
    └─ workflow_completion_rate{status="success|failure"}
         ↓
[Monitoring Dashboard] (Grafana, MLFlow UI)
    ├─ Visualize trends
    ├─ Alert on anomalies
    └─ Debug failed runs
```

### State Management Flow

```
[Workflow Execution]
    ↓
[State Store] ← write(workflow_id, state_version, state_data)
    │
    ├─ In-memory (dev): Python dict
    ├─ Redis (prod): SET workflow:{id}:state:v{N} {json}
    └─ PostgreSQL (durable): INSERT INTO workflow_states (...)
         ↓
[Checkpoint] ← periodic save (every N nodes or on error)
    ↓
[Failure Occurs]
    ↓
[Resume Workflow]
    ├─ Read latest checkpoint from State Store
    ├─ Reconstruct state
    └─ Continue from last successful node
```

---

## Communication Protocols

### Agent ↔ Orchestrator

**Protocol:** HTTP/REST (simple) or gRPC (high-performance)

**REST Example:**
```
POST /orchestrator/tasks/{task_id}/results
{
  "agent_id": "agent-1",
  "task_id": "task-12345",
  "status": "completed",
  "result": {
    "output": "...",
    "duration_ms": 1250,
    "tokens_used": 450
  }
}

Response: 200 OK
{
  "acknowledged": true,
  "next_task": null  // or next task if pipelining
}
```

**gRPC Example:**
```protobuf
service OrchestratorService {
  rpc SubmitTaskResult(TaskResult) returns (Acknowledgment);
  rpc GetNextTask(AgentStatus) returns (Task);
  rpc RegisterAgent(AgentMetadata) returns (RegistrationAck);
}
```

**Pros/Cons:**
- **REST:** Simple, debuggable (curl), firewall-friendly, language-agnostic
- **gRPC:** Faster, type-safe, streaming support, but needs codegen

---

### Orchestrator ↔ Registry

**Protocol:** HTTP API (Consul, etcd) or Client Library (Zookeeper)

**Registration:**
```bash
# Consul HTTP API
curl -X PUT http://registry:8500/v1/agent/service/register \
  -d '{
    "ID": "agent-1",
    "Name": "agent",
    "Address": "10.0.1.5",
    "Port": 8000,
    "Meta": {
      "capabilities": "text-generation,web-search",
      "version": "0.2.0"
    },
    "Check": {
      "HTTP": "http://10.0.1.5:8000/health",
      "Interval": "10s"
    }
  }'
```

**Discovery:**
```bash
# Query healthy agents with capability filter
curl http://registry:8500/v1/health/service/agent?passing=true
```

---

### Agent ↔ Storage

**Protocol:** Database-specific (PostgreSQL wire protocol, Redis RESP)

**Abstraction Layer:**
```python
# Storage interface (pluggable backend)
class WorkflowStore(ABC):
    @abstractmethod
    def save_workflow(self, workflow_id, config): pass

    @abstractmethod
    def load_workflow(self, workflow_id): pass

    @abstractmethod
    def save_state(self, workflow_id, state): pass

    @abstractmethod
    def load_state(self, workflow_id): pass

# Implementations
class SQLiteStore(WorkflowStore): ...
class PostgreSQLStore(WorkflowStore): ...
class CloudStore(WorkflowStore): ...  # S3 + DynamoDB, etc.
```

---

## Architectural Patterns from Leading Platforms

### LangGraph Platform Pattern

**Key Characteristics:**
- **Graph-based orchestration**: Workflows as explicit StateGraph (nodes + edges)
- **Durable execution**: Workflows persist through failures, resume from checkpoints
- **Stateful workflows**: Short-term (working memory) + long-term (cross-session) state
- **Streaming support**: Real-time output streaming during execution
- **Human-in-the-loop**: Pause for inspection/modification of agent state
- **LangSmith integration**: Purpose-built observability (tracing, prompt inspection)

**Architecture:**
```
[LangGraph Runtime]
    ├─ StateGraph executor (in-process)
    ├─ Checkpoint store (persistence layer)
    └─ LangSmith client (tracing)
         ↓
[LangSmith Agent Server] (deployment platform)
    ├─ Long-running workflows
    ├─ API endpoints for workflow invocation
    └─ Observability dashboard
```

**Strengths:** Low-level control, DSPy-compatible, excellent for complex workflows
**Weaknesses:** Requires understanding graph paradigm, less opinionated

---

### Prefect Pattern

**Key Characteristics:**
- **Work Pools + Workers**: Mediator between orchestration and execution
- **Dynamic infrastructure**: Workers dynamically provision infrastructure per flow run
- **Hybrid execution**: Server (orchestration) + Client (execution) separation
- **Platform approach**: Modular architecture for custom platforms
- **Deployment metadata**: Server-side flow representations (when/where/how to run)

**Architecture:**
```
[Prefect Cloud/Server] (orchestration layer)
    ├─ Orion API server
    ├─ REST API services
    ├─ UI dashboard
    └─ Workflow scheduler
         ↓
[Work Pools] (mediator/queue)
    ├─ Job templates (infrastructure patterns)
    ├─ RBAC controls (who uses what infra)
    └─ Dynamic assignment
         ↓
[Workers] (execution layer)
    ├─ Poll work pools for scheduled runs
    ├─ Spawn flow run in subprocess
    └─ Report results to server
```

**Alternative: `serve` method** (static infrastructure)
- Long-lived process communicating with Prefect API
- Monitors for work, submits runs in subprocesses

**Strengths:** Flexible deployment, strong platform approach, mature tooling
**Weaknesses:** More complex for simple use cases, requires Prefect server

---

### Temporal Pattern

**Key Characteristics:**
- **Durable execution**: Workflow state persisted to database (Cassandra, MySQL, PostgreSQL)
- **Built-in primitives**: Retries, task queues, signals, timers
- **Service discovery**: Workflow engine provides SD, load balancing, stability
- **Microservices orchestration**: Designed for distributed systems
- **Event-driven**: Activities triggered by events, decoupled services

**Architecture:**
```
[Temporal Cluster]
    ├─ Frontend Service (API gateway for clients)
    ├─ History Service (workflow state and history)
    ├─ Matching Service (match tasks with workers)
    ├─ Worker Service (execute activities)
    └─ Persistence Service (database: state, history, tasks)
         ↓
[Task Queues] (work distribution)
    ├─ Workflow task queues
    └─ Activity task queues
         ↓
[Workers] (execution)
    ├─ Poll task queues
    ├─ Execute workflow/activity code
    └─ Report completion to History Service
```

**Strengths:** Production-grade, handles failures gracefully, massive scale (75M+ workflows/month at Instacart)
**Weaknesses:** Heavy infrastructure, steep learning curve, overkill for simple workflows

---

## Storage Abstraction Patterns

### Pluggable Backend Architecture

**Goal:** Support SQLite (local) → PostgreSQL (team) → Cloud (enterprise) without code changes

**Interface:**
```python
class StorageBackend(ABC):
    """Abstract storage interface"""

    @abstractmethod
    def save_workflow(self, workflow_id: str, config: dict) -> None:
        """Save workflow definition"""

    @abstractmethod
    def load_workflow(self, workflow_id: str) -> dict:
        """Load workflow definition"""

    @abstractmethod
    def save_state(self, workflow_id: str, state: dict, version: int) -> None:
        """Save workflow state (with versioning for checkpoints)"""

    @abstractmethod
    def load_state(self, workflow_id: str, version: Optional[int] = None) -> dict:
        """Load workflow state (latest or specific version)"""

    @abstractmethod
    def list_runs(self, workflow_id: str, limit: int = 100) -> List[dict]:
        """List execution history"""
```

**Implementations:**

**SQLiteBackend (v0.1 - Local Development):**
```python
class SQLiteBackend(StorageBackend):
    def __init__(self, db_path: str = "./workflows.db"):
        self.db = sqlite3.connect(db_path)
        self._init_schema()

    def save_workflow(self, workflow_id, config):
        self.db.execute(
            "INSERT OR REPLACE INTO workflows (id, config) VALUES (?, ?)",
            (workflow_id, json.dumps(config))
        )

    def load_workflow(self, workflow_id):
        row = self.db.execute(
            "SELECT config FROM workflows WHERE id = ?",
            (workflow_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None
```

**PostgreSQLBackend (v0.2 - Team Collaboration):**
```python
class PostgreSQLBackend(StorageBackend):
    def __init__(self, connection_string: str):
        self.db = psycopg2.connect(connection_string)
        self._init_schema()

    def save_state(self, workflow_id, state, version):
        # Use JSONB for efficient querying
        self.db.execute(
            """INSERT INTO workflow_states
               (workflow_id, version, state, created_at)
               VALUES (%s, %s, %s, NOW())""",
            (workflow_id, version, json.dumps(state))
        )
```

**CloudBackend (v0.3+ - Enterprise):**
```python
class CloudBackend(StorageBackend):
    """S3 for artifacts, DynamoDB for metadata"""

    def __init__(self, s3_bucket: str, dynamodb_table: str):
        self.s3 = boto3.client('s3')
        self.dynamo = boto3.resource('dynamodb').Table(dynamodb_table)

    def save_workflow(self, workflow_id, config):
        # Metadata in DynamoDB
        self.dynamo.put_item(Item={
            'workflow_id': workflow_id,
            'created_at': datetime.now().isoformat(),
            'config_s3_key': f"workflows/{workflow_id}/config.json"
        })
        # Config in S3
        self.s3.put_object(
            Bucket=self.s3_bucket,
            Key=f"workflows/{workflow_id}/config.json",
            Body=json.dumps(config)
        )
```

**Factory Pattern:**
```python
def create_storage_backend(config: dict) -> StorageBackend:
    backend_type = config.get("storage", {}).get("backend", "sqlite")

    if backend_type == "sqlite":
        return SQLiteBackend(config["storage"].get("path", "./workflows.db"))
    elif backend_type == "postgresql":
        return PostgreSQLBackend(config["storage"]["connection_string"])
    elif backend_type == "cloud":
        return CloudBackend(
            s3_bucket=config["storage"]["s3_bucket"],
            dynamodb_table=config["storage"]["dynamodb_table"]
        )
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")
```

---

## UI Decoupling Patterns

### Sidecar Pattern for UI

**Principle:** UI components run in separate containers, communicate via API Gateway

**Why:**
- **Minimal agent containers**: No UI dependencies (Flask, Gradio, etc.) in agent images
- **Independent scaling**: Scale UI separately from agents
- **Optional deployment**: Headless agents for production, UI for development
- **Technology flexibility**: Swap UI frameworks without rebuilding agents

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│  Agent Container (~50-100MB)                        │
│  ┌──────────────────────────────────────────────┐  │
│  │  FastAPI Server (minimal)                     │  │
│  │  - POST /run (execute workflow)               │  │
│  │  - GET /health                                │  │
│  │  - GET /status/{job_id}                       │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
          │ (HTTP API)
          ▼
┌─────────────────────────────────────────────────────┐
│  UI Sidecar Container (~200-300MB)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Gradio UI   │  │ HTMX Dash    │  │ MLFlow UI │ │
│  │  (Chat)      │  │ (Orchestr.)  │  │ (Observe) │ │
│  │  :7860       │  │  :8080       │  │  :5000    │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│          All communicate with Agent API              │
└─────────────────────────────────────────────────────┘
```

**Docker Compose Example:**
```yaml
services:
  agent:
    image: configurable-agents:0.2
    ports:
      - "8000:8000"
    environment:
      - STORAGE_BACKEND=sqlite
    volumes:
      - ./data:/data

  ui-sidecar:
    image: configurable-agents-ui:0.2
    ports:
      - "7860:7860"  # Gradio
      - "8080:8080"  # HTMX dashboard
      - "5000:5000"  # MLFlow UI
    environment:
      - AGENT_API_URL=http://agent:8000
    depends_on:
      - agent
```

**Deployment Modes:**

**Local Development:**
```bash
# Run both agent + UI
docker-compose up
```

**Production (Headless):**
```bash
# Run only agent
docker run configurable-agents:0.2
```

**Production (with UI for monitoring):**
```bash
# Run agent + UI with authentication
docker-compose -f docker-compose.prod.yml up
```

---

### Gradio + HTMX Pattern

**Gradio for Chat Interface:**
- Purpose-built for LLM interactions
- Real-time streaming
- Minimal setup (~20 lines)

**HTMX for Orchestration Dashboard:**
- Lightweight (~14KB)
- Server-side rendering (no React/Vue complexity)
- Perfect for CRUD operations (view workflows, trigger runs, inspect state)

**Example Architecture:**
```python
# Gradio Chat (ui_sidecar/chat.py)
import gradio as gr

def chat(message, history):
    response = requests.post(
        f"{AGENT_API_URL}/run",
        json={"workflow": "chat", "input": message}
    )
    return response.json()["output"]

gr.ChatInterface(chat).launch(server_port=7860)
```

```python
# HTMX Dashboard (ui_sidecar/dashboard.py)
from flask import Flask, render_template, request

@app.route("/workflows")
def list_workflows():
    workflows = requests.get(f"{AGENT_API_URL}/workflows").json()
    return render_template("workflows.html", workflows=workflows)

@app.route("/workflows/<id>/run", methods=["POST"])
def trigger_workflow(id):
    result = requests.post(f"{AGENT_API_URL}/run/{id}")
    # Return HTML fragment (HTMX will swap into page)
    return f'<div class="alert success">Workflow triggered: {result.json()["job_id"]}</div>'
```

**HTML with HTMX:**
```html
<button hx-post="/workflows/{{ workflow.id }}/run"
        hx-target="#result"
        hx-swap="innerHTML">
    Run Workflow
</button>
<div id="result"></div>
```

---

## Multi-Deployment Mode Strategy

### Mode 1: Local CLI (v0.1)

**User:** Individual developer
**Interface:** Command-line
**Storage:** SQLite file
**Observability:** File logs + MLFlow file backend

```bash
configurable-agents run workflow.yaml --input '{"topic": "AI safety"}'
```

**No containers, no services, just Python process.**

---

### Mode 2: Local Docker (v0.1)

**User:** Developer wanting containerization
**Interface:** HTTP API
**Storage:** SQLite (mounted volume)
**Observability:** MLFlow file backend (mounted volume)

```bash
configurable-agents deploy workflow.yaml
# Generates Docker artifacts + docker-compose.yml
docker-compose up -d
curl -X POST http://localhost:8000/run -d '{"topic": "AI safety"}'
```

**Single container, minimal setup, persistent storage via volume.**

---

### Mode 3: Multi-Container Local (v0.2)

**User:** Team development, testing decoupled architecture
**Interface:** HTTP API + UI Sidecar
**Storage:** PostgreSQL container
**Observability:** MLFlow server container

```yaml
# docker-compose.yml
services:
  orchestrator:
    image: configurable-agents-orchestrator:0.2

  agent-1:
    image: configurable-agents-agent:0.2
    environment:
      - ORCHESTRATOR_URL=http://orchestrator:8000

  agent-2:
    image: configurable-agents-agent:0.2
    environment:
      - ORCHESTRATOR_URL=http://orchestrator:8000

  postgres:
    image: postgres:16

  mlflow:
    image: mlflow-server:latest
    environment:
      - BACKEND_STORE_URI=postgresql://...

  ui-sidecar:
    image: configurable-agents-ui:0.2
```

**Multiple containers, service discovery via Docker networking.**

---

### Mode 4: Kubernetes Production (v0.4)

**User:** Enterprise, auto-scaling, high availability
**Interface:** Ingress → API Gateway
**Storage:** Cloud-native (RDS, DynamoDB, S3)
**Observability:** OpenTelemetry → Prometheus/DataDog

```yaml
# k8s/orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orchestrator
  template:
    spec:
      containers:
      - name: orchestrator
        image: configurable-agents-orchestrator:0.4
        env:
        - name: STORAGE_BACKEND
          value: cloud
        - name: S3_BUCKET
          value: my-workflows
```

```yaml
# k8s/agent-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: agent
spec:
  replicas: 10
  serviceName: agent
  selector:
    matchLabels:
      app: agent
  template:
    spec:
      containers:
      - name: agent
        image: configurable-agents-agent:0.4
```

**Kubernetes-native, auto-scaling (HPA), production-grade.**

---

## Build Order & Dependencies

Based on research and project context, recommended implementation order:

### Phase 1: Storage Abstraction (Foundation)
**Why first:** All other components depend on storage
**Components:**
- Storage interface (`StorageBackend` ABC)
- SQLite implementation (v0.1 baseline)
- PostgreSQL implementation (v0.2 target)
- Factory pattern for backend selection

**Effort:** ~1-2 weeks
**Blockers:** None

---

### Phase 2: API Gateway Layer (Enables Decoupling)
**Why second:** Required for UI sidecar and multi-container deployments
**Components:**
- FastAPI server with REST endpoints
- `/run` (execute workflow)
- `/health` (health check)
- `/status/{job_id}` (async job status)
- `/workflows` (list available workflows)

**Effort:** ~1-2 weeks
**Blockers:** Storage abstraction complete

---

### Phase 3: Agent Container Minimal Image (Deployment Target)
**Why third:** Enables multi-container architecture
**Components:**
- Dockerfile for agent (minimal, ~50-100MB)
- Remove UI dependencies from core
- Environment variable configuration
- Health check endpoint

**Effort:** ~1 week
**Blockers:** API Gateway layer complete

---

### Phase 4: Service Registry (Enables Discovery)
**Why fourth:** Needed for agent-orchestrator bidirectional communication
**Components:**
- Registry interface (Consul, etcd, or simple in-memory for v0.2)
- Agent registration logic (on startup)
- Orchestrator discovery logic (query for agents)
- Heartbeat mechanism

**Effort:** ~2-3 weeks
**Blockers:** Agent container image complete

---

### Phase 5: UI Sidecar (Optional, Enhances DX)
**Why fifth:** Improves developer experience, but not blocking for core functionality
**Components:**
- Gradio chat interface
- HTMX orchestration dashboard
- MLFlow UI integration
- Separate Docker image (`-ui` suffix)

**Effort:** ~2-3 weeks
**Blockers:** API Gateway layer complete

---

### Phase 6: Multi-Container Orchestration (Production-Ready)
**Why sixth:** Combines all previous components
**Components:**
- Docker Compose templates
- Orchestrator container (separate from agent)
- Agent pool (multiple agent containers)
- Networking configuration
- Volume management

**Effort:** ~1-2 weeks
**Blockers:** Service registry, UI sidecar complete

---

### Phase 7: Observability Integration (OpenTelemetry)
**Why seventh:** Enhances existing MLFlow tracking
**Components:**
- OpenTelemetry SDK integration
- Distributed tracing across containers
- Metrics export (Prometheus format)
- Correlation with MLFlow traces

**Effort:** ~2-3 weeks
**Blockers:** Multi-container orchestration complete

---

### Phase 8: Kubernetes Deployment (Enterprise)
**Why last:** Most complex, requires all previous components
**Components:**
- Kubernetes manifests (Deployments, StatefulSets, Services)
- Helm charts
- Ingress configuration
- Auto-scaling policies (HPA)
- Cloud storage integration

**Effort:** ~4-6 weeks
**Blockers:** All previous phases complete

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Premature Microservices

**What people do:** Split every component into separate containers from day one
**Why it's wrong:** Operational complexity explodes before value is proven
**Do this instead:** Start monolithic (v0.1), evolve to multi-container (v0.2), then microservices (v0.4)

**Example:**
```
❌ Bad (v0.1):
- orchestrator container
- agent container
- registry container
- storage container
- observability container
→ 5 containers to debug for simple workflow

✅ Good (v0.1):
- Single Python process
- SQLite file
- File-based observability
→ Fast iteration, easy debugging

✅ Good (v0.2):
- Orchestrator + Agent containers
- Shared PostgreSQL
- MLFlow server
→ Realistic deployment, manageable complexity
```

---

### Anti-Pattern 2: Tight Coupling to Storage Implementation

**What people do:** Use database-specific features (PostgreSQL JSONB queries, Redis Lua scripts) throughout codebase
**Why it's wrong:** Impossible to switch backends later, blocks local-first approach
**Do this instead:** Abstract behind interface, implement for SQLite first, extend to PostgreSQL/Cloud

**Example:**
```python
❌ Bad:
def get_workflow(workflow_id):
    # Directly using PostgreSQL JSONB
    return db.execute(
        "SELECT config->'nodes' FROM workflows WHERE id = %s",
        (workflow_id,)
    )

✅ Good:
class StorageBackend(ABC):
    @abstractmethod
    def get_workflow(self, workflow_id): pass

class SQLiteBackend(StorageBackend):
    def get_workflow(self, workflow_id):
        row = self.db.execute("SELECT config FROM workflows WHERE id = ?", (workflow_id,))
        return json.loads(row[0]) if row else None

class PostgreSQLBackend(StorageBackend):
    def get_workflow(self, workflow_id):
        row = self.db.execute("SELECT config FROM workflows WHERE id = %s", (workflow_id,))
        return row[0] if row else None  # PostgreSQL returns JSONB as dict
```

---

### Anti-Pattern 3: Monolithic UI Container

**What people do:** Bundle all UI components (Gradio, HTMX, MLFlow) into single large image
**Why it's wrong:** Forces users to run entire UI stack even if they only need one component
**Do this instead:** Separate images for each UI component, compose with Docker Compose

**Example:**
```yaml
❌ Bad:
services:
  agent:
    image: configurable-agents:0.2  # Agent code
  ui:
    image: configurable-agents-ui:0.2  # 500MB image with Gradio + HTMX + MLFlow

✅ Good:
services:
  agent:
    image: configurable-agents:0.2  # Agent code
  ui-chat:
    image: configurable-agents-chat:0.2  # ~100MB, Gradio only
  ui-dashboard:
    image: configurable-agents-dashboard:0.2  # ~80MB, HTMX only
  mlflow:
    image: mlflow-server:latest  # Official MLFlow image
```

---

### Anti-Pattern 4: Synchronous Service Discovery

**What people do:** Query service registry on every request
**Why it's wrong:** High latency, registry becomes bottleneck, failures cascade
**Do this instead:** Cache registry results, subscribe to updates, implement circuit breakers

**Example:**
```python
❌ Bad:
def execute_task(task):
    agents = registry.query(service="agent")  # Query on every task!
    selected = random.choice(agents)
    return selected.execute(task)

✅ Good:
class AgentPool:
    def __init__(self, registry):
        self.registry = registry
        self.cache = []
        self.cache_ttl = 30  # seconds
        self.last_refresh = 0

    def get_agent(self):
        if time.time() - self.last_refresh > self.cache_ttl:
            self.cache = self.registry.query(service="agent", passing=True)
            self.last_refresh = time.time()

        if not self.cache:
            raise NoHealthyAgentsError()

        return random.choice(self.cache)
```

---

### Anti-Pattern 5: No Health Checks

**What people do:** Register agents in registry without health checks
**Why it's wrong:** Orchestrator routes tasks to dead agents, tasks fail silently
**Do this instead:** Implement `/health` endpoint, configure registry health checks, handle failures

**Example:**
```python
✅ Good:
# Agent health endpoint
@app.get("/health")
def health_check():
    # Check dependencies
    if not llm_client.is_healthy():
        return JSONResponse({"status": "unhealthy"}, status_code=503)

    if not storage.is_connected():
        return JSONResponse({"status": "unhealthy"}, status_code=503)

    return {"status": "healthy", "version": "0.2.0"}

# Registry configuration
registry.register(
    service_id="agent-1",
    health_check={
        "http": "http://agent-1:8000/health",
        "interval": "10s",
        "timeout": "2s",
        "deregister_critical_service_after": "30s"  # Remove if unhealthy too long
    }
)
```

---

## Key Takeaways for Configurable-Agents

### 1. Start Simple, Evolve Gradually
- **v0.1:** Monolithic runtime (current) ✅
- **v0.2:** Storage abstraction + API layer
- **v0.3:** Multi-container + service discovery
- **v0.4:** Kubernetes + cloud backends

### 2. Prioritize Local-First
- SQLite before PostgreSQL
- File-based observability before server
- Docker Compose before Kubernetes
- CLI before UI

### 3. Decouple UI from Core
- Minimal agent containers (~50-100MB)
- UI sidecar pattern (optional deployment)
- Gradio for chat, HTMX for dashboards
- Communicate via REST API

### 4. Abstract Storage Early
- Define `StorageBackend` interface in v0.2
- Implement SQLite first (baseline)
- Add PostgreSQL (team collaboration)
- Plan for cloud backends (enterprise)

### 5. Registry Enables Multi-Agent
- Bidirectional registration (agent ↔ orchestrator)
- Health checks (deregister dead agents)
- Capability-based routing (match agents to tasks)
- Start simple (in-memory), evolve to Consul/etcd

### 6. Observability is Non-Negotiable
- MLFlow for LLM tracking (current) ✅
- Add OpenTelemetry for distributed tracing (v0.3)
- Prometheus metrics (v0.3)
- Grafana dashboards (v0.4)

### 7. Learn from Industry Leaders
- **LangGraph:** Graph-based execution, durable workflows
- **Prefect:** Work pools/workers, deployment metadata
- **Temporal:** Durable execution, event-driven, production-scale

---

## Sources

### Primary Research
- [LangGraph Multi-Agent Orchestration Guide (2025)](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [LangGraph Overview - LangChain Docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [Prefect Deployments Documentation](https://docs.prefect.io/v3/concepts/deployments)
- [Prefect Platform Approach](https://www.prefect.io/blog/a-platform-approach-to-workflow-orchestration)
- [Temporal Workflow Orchestration (Jan 2026)](https://medium.com/@milinangalia/the-rise-of-temporal-how-netflix-and-leading-tech-companies-are-revolutionizing-workflow-822fbcc736e6)
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)

### Architecture Patterns
- [Google's Eight Essential Multi-Agent Design Patterns (Jan 2026)](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)
- [Multi-Agent Orchestration: Enterprise Strategy 2025-2026](https://www.onabout.ai/p/mastering-multi-agent-orchestration-architectures-patterns-roi-benchmarks-for-2025-2026)
- [AWS Multi-Agent Orchestration Guidance](https://aws.amazon.com/solutions/guidance/multi-agent-orchestration-on-aws/)

### Service Discovery & Deployment
- [Microservices Pattern: Service Registry](https://microservices.io/patterns/service-registry.html)
- [Service Discovery Guide (2026 Edition)](https://middleware.io/blog/service-discovery/)
- [Sidecar Design Pattern](https://microservices.io/patterns/deployment/sidecar.html)
- [Kubernetes Container Orchestration 2026](https://www.techaheadcorp.com/blog/the-growth-of-containers-and-kubernetes-architecture-in-cloud-deployment-a-2025-perspective/)

### Observability
- [MLOps in 2026 — Definitive Guide](https://rahulkolekar.com/mlops-in-2026-the-definitive-guide-tools-cloud-platforms-architectures-and-a-practical-playbook/)
- [Top 5 LLM Observability Platforms 2026](https://www.getmaxim.ai/articles/top-5-llm-observability-platforms-in-2026/)
- [15 AI Agent Observability Tools 2026](https://research.aimultiple.com/agentic-monitoring/)
- [MLflow Tracing - Databricks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/)

### Storage & State Management
- [NestJS Pluggable DB Architecture](https://github.com/deadislove/nestJS-modular-monolith-event-driven-architecture-template)
- [SQLite4 Pluggable Storage Engine](https://sqlite.org/src4/doc/trunk/www/storage.wiki)

### Agent Lifecycle
- [Agent Lifecycle Management 2026](https://onereach.ai/blog/agent-lifecycle-management-stages-governance-roi/)
- [AI Agent Identity Management (Okta)](https://www.okta.com/identity-101/ai-agent-lifecycle-management/)

### UI & Interface
- [Gradio Agents Documentation](https://www.gradio.app/guides/agents-and-tool-usage)
- [Sidecar Pattern Explained](https://blog.bytebytego.com/p/the-sidecar-pattern-explained-decoupling)

---

*Architecture research for: Agent Orchestration Platforms*
*Researched: 2026-02-02*
*Confidence: HIGH (verified with official documentation and recent 2026 sources)*
