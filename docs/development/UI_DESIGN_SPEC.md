# UI Design Specification

**Status**: APPROVED - Ready for Implementation
**Created**: 2026-02-13
**Related**: UI_PAGES_DESIGN.md (mockups), UI_REDESIGN_ANALYSIS.md (impact analysis)

---

## Executive Summary

This document specifies the redesigned UI architecture for Configurable Agents. The system consists of **4 pages** backed by **2 databases**, with the Chat UI serving as the primary entry point for users.

### Design Principles

1. **Chat UI as Entry Point**: Users start here to create and run workflows
2. **Table Names = Page Names**: `executions` table → Executions page, `deployments` table → Deployments page
3. **Single App Database**: All application data in `configurable_agents.db`
4. **MLflow Separate**: `mlflow.db` remains MLflow's own schema
5. **Orchestrator Absorbed**: All orchestration functionality merged into Deployments page

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [Chat UI] ←→ [Executions] ←→ [Deployments] ←→ [MLflow]        │
│       │              │               │               │          │
│       │              │               │               │          │
│       ▼              ▼               ▼               ▼          │
│   ┌─────────────────────────────────────────┐   ┌───────────┐  │
│   │     configurable_agents.db              │   │ mlflow.db │  │
│   │  ┌─────────────────────────────────┐   │   │ (external)│  │
│   │  │ chat_sessions                   │   │   └───────────┘  │
│   │  │ chat_messages                   │   │                   │
│   │  │ executions                      │   │                   │
│   │  │ execution_states                │   │                   │
│   │  │ deployments                     │   │                   │
│   │  │ (internal tables...)            │   │                   │
│   │  └─────────────────────────────────┘   │                   │
│   └─────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Page Summary

| Page | Purpose | Primary User | Data Store |
|------|---------|--------------|------------|
| **Chat UI** | Generate workflow configs conversationally | Developer/Designer | `chat_sessions`, `chat_messages` |
| **Executions** | View and manage all workflow runs | Operator/Developer | `executions`, `execution_states` |
| **Deployments** | Manage deployed workflow containers | Operator | `deployments` |
| **MLflow** | Observability: traces, experiments, metrics | Operator/Developer | MLflow's own DB |

---

## Page 1: Chat UI (Entry Point)

### Purpose

Conversational interface for generating valid workflow YAML configs through natural language interaction. This is the **primary entry point** for users of the system.

### User Flow

```
USER OPENS APP
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  WELCOME MESSAGE (from LLM)                                      │
│                                                                  │
│  "Welcome! I can help you create workflow configurations.       │
│   Here's what I support:                                         │
│   • Single-agent LLM workflows                                   │
│   • Multi-step pipelines                                         │
│   • Tool-augmented agents (web search, APIs, etc.)               │
│   • Conditional branching                                        │
│                                                                  │
│   Would you like to continue?"                                   │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼ User: "Yes, I want to research a topic and write an article"
      │
┌─────────────────────────────────────────────────────────────────┐
│  STATE MACHINE VISUALIZATION                                     │
│                                                                  │
│  "Here's what I understand your workflow to look like:           │
│                                                                  │
│       START ──► research ──► write_article ──► END              │
│                                                                  │
│   Does this match your vision?"                                  │
└─────────────────────────────────────────────────────────────────┘
      │
      ├──── User: "Yes" ────┐
      │                     │
      │                     ▼
      │        ┌─────────────────────────────────────────────────┐
      │        │ ENHANCEMENT SUGGESTIONS                          │
      │        │                                                  │
      │        │ "I suggest:                                      │
      │        │  • Add 'summarize' step between research & write │
      │        │  • Use Tavily for web search (needs API key)     │
      │        │  • Estimated cost: ~$0.05 per run                │
      │        │                                                  │
      │        │  Required: OPENAI_API_KEY                        │
      │        │  Optional: TAVILY_API_KEY                        │
      │        │                                                  │
      │        │  Approve?"                                       │
      │        └─────────────────────────────────────────────────┘
      │                      │
      │                      ▼ User: "Approve"
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  FINAL OUTPUT                                                    │
│                                                                  │
│  ┌──────────────────────┐   ┌────────────────────────────────┐  │
│  │ Final State Machine  │   │ Generated YAML Config          │  │
│  │                      │   │                                │  │
│  │ START ──► research   │   │ schema_version: "1.0"          │  │
│  │   │                  │   │ flow:                          │  │
│  │   ▼                  │   │   name: research_article       │  │
│  │ summarize ──► write  │   │ nodes:                         │  │
│  │   │                  │   │   - id: research               │  │
│  │   ▼                  │   │     prompt: "Research {topic}" │  │
│  │  END                 │   │   ...                          │  │
│  └──────────────────────┘   └────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────┐   ┌────────────────┐                        │
│  │   EXECUTE      │   │    DEPLOY      │                        │
│  │  (Runtime)     │   │   (Docker)     │                        │
│  └───────┬────────┘   └───────┬────────┘                        │
└──────────┼─────────────────────┼─────────────────────────────────┘
           │                     │
           ▼                     ▼
```

### Execute Flow (Runtime Execution)

When user clicks **EXECUTE**:

```
┌─────────────────────────────────────────────────────────────────┐
│  .ENV INPUT AREA (modal or side panel)                           │
│                                                                  │
│  "Your workflow requires these environment variables:"           │
│                                                                  │
│  OPENAI_API_KEY:  [••••••••••••••••••]  (required)               │
│  TAVILY_API_KEY:  [••••••••••••••••••]  (optional)               │
│                                                                  │
│  [Or paste your .env file contents here]                         │
│                                                                  │
│                              [Cancel]  [Execute Now]             │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼ User clicks Execute Now
           │
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTION IN PROGRESS                                           │
│                                                                  │
│  "Running your workflow...                                       │
│   ✓ research (2s)                                                │
│   ✓ summarize (1.5s)                                             │
│   ◐ write_article...                                             │
│                                                                  │
│   [spinner animation]                                            │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼ Workflow completes
           │
┌─────────────────────────────────────────────────────────────────┐
│  RESULT                                                          │
│                                                                  │
│  "Workflow completed successfully!                               │
│                                                                  │
│   Duration: 8.5 seconds                                          │
│   Cost: $0.042                                                   │
│                                                                  │
│   Output:                                                        │
│   {                                                              │
│     "article": "AI Safety Research has emerged as...",           │
│     "sources": ["url1", "url2", ...]                             │
│   }                                                              │
│                                                                  │
│   [View in Executions] [View in MLflow] [Run Again]"             │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
    Record created in `executions` table
    (deployment_id = NULL since it was runtime)
```

**Key Behavior**:
- Workflow runs in-memory (no persistent container)
- Result shown directly in chat
- Record created in `executions` table with `deployment_id = NULL`
- User can view details in Executions page

### Deploy Flow (Docker Deployment)

When user clicks **DEPLOY**:

```
┌─────────────────────────────────────────────────────────────────┐
│  .ENV INPUT AREA                                                 │
│                                                                  │
│  (Same as Execute - collect API keys)                            │
│                                                                  │
│                              [Cancel]  [Deploy Now]              │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼ User clicks Deploy Now
           │
┌─────────────────────────────────────────────────────────────────┐
│  DEPLOYMENT IN PROGRESS                                          │
│                                                                  │
│  "Deploying your workflow as a Docker container...               │
│   ✓ Generated deployment artifacts                               │
│   ✓ Built Docker image                                           │
│   ✓ Started container on port 8080                               │
│   ✓ Registered with dashboard                                    │
│                                                                  │
│   Deployment ID: research-article-prod                           │
│   URL: http://localhost:8080                                     │
│                                                                  │
│   [View in Deployments] [Test Endpoint] [View Docs]"             │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
    Record created in `deployments` table
    Container starts heartbeat loop (20s interval, 60s TTL)
```

**Key Behavior**:
- Docker container built and started
- Container runs workflow as FastAPI server
- Container auto-registers with dashboard
- Record created in `deployments` table
- Heartbeat loop keeps container "alive" in dashboard

### Data Storage

| Table | What | When |
|-------|------|------|
| `chat_sessions` | One row per browser session | When user first opens Chat UI |
| `chat_messages` | Every message (user + assistant) | Each time user sends or LLM responds |

**Schema**:

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[str]        # UUID primary key
    user_identifier: Mapped[str]   # Browser fingerprint or IP:port
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    generated_config: Mapped[Optional[str]]  # Final YAML when approved
    status: Mapped[str]            # "in_progress", "completed", "abandoned"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int]
    session_id: Mapped[str]        # FK to chat_sessions.session_id
    role: Mapped[str]              # "user" or "assistant"
    content: Mapped[str]           # Message text
    created_at: Mapped[datetime]
    message_metadata: Mapped[Optional[str]]  # JSON: model, tokens, state_machine, etc.
```

**Example Data**:

```sql
-- chat_sessions
session_id: "sess_abc123"
user_identifier: "192.168.1.1:54321"
generated_config: "schema_version: 1.0\nflow:\n  name: research_article..."
status: "completed"

-- chat_messages
{id: 1, session_id: "sess_abc123", role: "assistant", content: "Welcome! I can help..."}
{id: 2, session_id: "sess_abc123", role: "user", content: "Yes, I want to research..."}
{id: 3, session_id: "sess_abc123", role: "assistant", content: "Here's the state machine..."}
{id: 4, session_id: "sess_abc123", role: "user", content: "Looks good, approve"}
{id: 5, session_id: "sess_abc123", role: "assistant", content: "Final YAML:\n```yaml\n..."}
```

---

## Page 2: Executions

### Purpose

View and manage **ALL workflow executions** - whether they came from:
- Chat UI Execute button (runtime, `deployment_id = NULL`)
- Deployments page Execute button (on container, `deployment_id = "xxx"`)

### List View

```
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTIONS                                                      │
│                                                                  │
│  Filter: [All Status ▼] [All Workflows ▼] [Search...]           │
│          [Today] [This Week] [All]                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ STATUS │ WORKFLOW      │ STARTED    │ DURATION │ COST     │ │
│  ├────────┼───────────────┼────────────┼──────────┼───────────┤ │
│  │ 🟢 Run │ research_bot  │ 2 min ago  │ ---      │ ---       │ │
│  │ ✅ OK  │ article_write │ 10 min ago │ 45s      │ $0.042    │ │
│  │ ❌ Fail│ translator    │ 2 hr ago   │ 12s      │ $0.001    │ │
│  │ ✅ OK  │ research_bot  │ 1 hr ago   │ 1m20s    │ $0.089    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ◀ 1 2 3 ... 16 ▶                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Detail View

Clicking on a row shows full details:

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Executions                                            │
│                                                                  │
│  Execution: exec_abc123                                          │
│  ─────────────────────                                           │
│  Workflow:    research_bot                                       │
│  Status:      ✅ Completed                                       │
│  Started:     2026-02-13 10:30:45                               │
│  Completed:   2026-02-13 10:31:30                               │
│  Duration:    45 seconds                                         │
│  Tokens:      2,450                                              │
│  Cost:        $0.0245                                            │
│  Deployment:  research-bot-prod (localhost:8080)  [Go]          │
│                                                                  │
│  INPUTS:                                                         │
│  { "topic": "AI Safety", "depth": 3 }                           │
│                                                                  │
│  OUTPUTS:                                                        │
│  { "result": "Comprehensive analysis...", "sources": [...] }    │
│                                                                  │
│  STATE HISTORY:                                                  │
│  START ──► research ──► summarize ──► END                        │
│            (15s)       (20s)                                     │
│                                                                  │
│  [View in MLflow] [Download Config] [Re-run]                    │
└─────────────────────────────────────────────────────────────────┘
```

### Features

1. **Execution List**: All past runs with status, workflow name, duration, cost
2. **Filtering**: By status (completed, failed, running), by workflow name, by date range
3. **Execution Detail**: Inputs, outputs, state history, bottleneck analysis
4. **Actions**:
   - Cancel (for running executions)
   - Re-run (restart with same inputs)
   - View in MLflow (see traces)
5. **Deployment Link**: If `deployment_id` is set, shows link to the deployment

### Data Storage

| Table | What | When |
|-------|------|------|
| `executions` | One row per workflow run | Every time a workflow executes |
| `execution_states` | State checkpoint after each node | After each node completes |

**Schema**:

```python
class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str]                     # execution_id (UUID)
    workflow_name: Mapped[str]          # Name of workflow
    status: Mapped[str]                 # "pending", "running", "completed", "failed"
    config_snapshot: Mapped[Optional[str]]  # Full YAML used
    inputs: Mapped[Optional[str]]       # JSON inputs
    outputs: Mapped[Optional[str]]      # JSON outputs
    error_message: Mapped[Optional[str]]  # If failed
    started_at: Mapped[datetime]
    completed_at: Mapped[Optional[datetime]]
    duration_seconds: Mapped[Optional[float]]
    total_tokens: Mapped[Optional[int]]
    total_cost_usd: Mapped[Optional[float]]
    bottleneck_info: Mapped[Optional[str]]  # JSON analysis
    deployment_id: Mapped[Optional[str]]    # FK to deployments, NULL for runtime


class ExecutionState(Base):
    __tablename__ = "execution_states"

    id: Mapped[int]
    execution_id: Mapped[str]           # FK to executions.id
    node_id: Mapped[str]                # Which node produced this state
    state_data: Mapped[str]             # JSON state snapshot
    created_at: Mapped[datetime]
```

**Key Insight - The `deployment_id` Field**:

| Value | Meaning |
|-------|---------|
| `NULL` | Runtime execution (from Chat UI Execute button) |
| `"research-bot-prod"` | Executed on that deployment container |

This allows filtering executions by source.

---

## Page 3: Deployments

### Purpose

Manage **deployed workflow containers** - Docker containers running workflows as persistent services that can be called repeatedly.

### Sources of Deployments

```
┌─────────────────┐
│   Chat UI       │ ──► User clicks "Deploy" ──► Docker build/run
│   Deploy button │                              │
└─────────────────┘                              │
                                                 ▼
┌─────────────────┐                      ┌─────────────────┐
│   CLI command   │ ──► configurable-   │ deployments     │
│   deploy        │     agents deploy   │    table        │
└─────────────────┘                      └─────────────────┘
                                                 ▲
┌─────────────────┐                              │
│   Manual        │ ──► User fills form ────────┘
│   Register      │     on Deployments page
└─────────────────┘
```

### List View

```
┌─────────────────────────────────────────────────────────────────┐
│  DEPLOYMENTS                                                     │
│                                                                  │
│  [+ Register New Deployment]    [Refresh]  [Cleanup Expired]    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ HEALTH │ NAME              │ WORKFLOW     │ HOST:PORT      │ │
│  ├────────┼───────────────────┼──────────────┼────────────────┤ │
│  │ 🟢 OK  │ research-bot-prod │ research_bot │ localhost:8080 │ │
│  │        │ Heartbeat: 5s ago │              │ [Exec][Schema] │ │
│  ├────────┼───────────────────┼──────────────┼────────────────┤ │
│  │ 🟢 OK  │ summarizer-api    │ summarizer   │ localhost:8081 │ │
│  ├────────┼───────────────────┼──────────────┼────────────────┤ │
│  │ 🔴 DEAD│ old-translator    │ translator   │ localhost:8082 │ │
│  │        │ Heartbeat: 2hr ago│              │ [Delete]       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Health Monitoring

- **Heartbeat Interval**: Container sends heartbeat every 20 seconds
- **TTL**: 60 seconds (deployment considered dead if no heartbeat for 60s)
- **Dashboard Polling**: HTMX polls every 10 seconds to update health status
- **Cleanup**: User can click "Cleanup Expired" to remove dead deployments

### Execute on Deployment

Clicking [Exec] opens a modal:

```
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTE ON: research-bot-prod                              [X] │
│                                                                  │
│  Workflow: research_bot                                          │
│  Host: localhost:8080                                           │
│                                                                  │
│  INPUTS (from workflow schema):                                  │
│  topic (string, required):                                       │
│  [________________________________________]                      │
│                                                                  │
│  depth (integer, optional, default=3):                           │
│  [___3___]                                                       │
│                                                                  │
│  ENVIRONMENT VARIABLES:                                          │
│  OPENAI_API_KEY (required):                                      │
│  [••••••••••••••••••••••••]                                      │
│                                                                  │
│  [Or paste .env file here]                                       │
│                                                                  │
│                          [Cancel]  [Execute]                     │
└─────────────────────────────────────────────────────────────────┘
```

**Execute Flow**:
1. User fills inputs and env vars
2. POST to `http://localhost:8080/run` with inputs
3. Create record in `executions` table with `deployment_id = "research-bot-prod"`
4. Container runs workflow, returns results
5. Update execution record with outputs, cost, tokens
6. Show results to user

### Register New Deployment

Manual registration for containers started outside the system:

```
┌─────────────────────────────────────────────────────────────────┐
│  REGISTER NEW DEPLOYMENT                                    [X] │
│                                                                  │
│  Deployment ID:                                                  │
│  [my-workflow-deployment    ]                                    │
│                                                                  │
│  Deployment Name:                                                │
│  [My Workflow Deployment    ]                                    │
│                                                                  │
│  Host:                                                           │
│  [localhost                  ]                                    │
│                                                                  │
│  Port:                                                           │
│  [8080                       ]                                    │
│                                                                  │
│  [ ] Verify health by calling /health endpoint first            │
│                                                                  │
│                          [Cancel]  [Register]                    │
└─────────────────────────────────────────────────────────────────┘
```

### Features

1. **Deployment List**: All registered containers with health status
2. **Health Monitoring**: Alive/dead status via heartbeat TTL
3. **Manual Registration**: Register running containers
4. **Execute**: Run workflow on deployment with env vars
5. **View Schema**: See workflow inputs/outputs schema
6. **View Docs**: Link to container's `/docs` endpoint
7. **Deregister**: Remove dead/retired deployments

### Data Storage

| Table | What | When |
|-------|------|------|
| `deployments` | One row per deployed container | On deployment or manual registration |

**Schema**:

```python
class Deployment(Base):
    __tablename__ = "deployments"

    deployment_id: Mapped[str]          # Unique ID (primary key)
    deployment_name: Mapped[str]        # Human-readable name
    workflow_name: Mapped[str]          # Workflow this deployment runs
    host: Mapped[str]                   # Container host
    port: Mapped[int]                   # Container port
    last_heartbeat: Mapped[datetime]    # Last heartbeat timestamp
    ttl_seconds: Mapped[int]            # TTL for health check (default: 60)
    capabilities: Mapped[Optional[str]] # JSON: tools, features supported
    deployment_metadata: Mapped[Optional[str]]  # JSON: additional info
    registered_at: Mapped[datetime]

    def is_alive(self) -> bool:
        """Check if heartbeat is within TTL"""
        expiration = self.last_heartbeat + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() < expiration
```

### Absorbed from Orchestrator

The old "Orchestrator" page functionality is now in Deployments:

| Old Route | New Route | Action |
|-----------|-----------|--------|
| `POST /orchestrator/register` | `POST /deployments/register` | Register deployment |
| `POST /orchestrator/{id}/execute` | `POST /deployments/{id}/execute` | Execute on deployment |
| `DELETE /orchestrator/{id}` | `DELETE /deployments/{id}` | Deregister |
| `GET /orchestrator/{id}/schema` | `GET /deployments/{id}/schema` | Get workflow schema |

---

## Page 4: MLflow

### Purpose

Observability interface for traces, experiments, and metrics. This is MLflow's own UI - we just provide access to it.

### Modes

**Embedded Mode** (local MLflow):
- MLflow tracking URI is `file://` or `sqlite:///mlflow.db`
- MLflow UI embedded in iframe within our dashboard
- Seamless user experience

**External Mode** (remote MLflow):
- MLflow tracking URI is `http://mlflow.example.com:5000`
- Show link to external MLflow server
- User opens in new tab

### Embedded Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    MLFLOW UI EMBEDDED                       │ │
│  │                    (in iframe)                              │ │
│  │                                                             │ │
│  │   ┌───────────────────────┐                                 │ │
│  │   │ Experiments │ Runs    │                                 │ │
│  │   └───────────────────────┘                                 │ │
│  │                                                             │ │
│  │   ┌─────────────────────────────────────────────────────┐  │ │
│  │   │ Experiment List                                      │  │ │
│  │   │ • research_bot_exp                                   │  │ │
│  │   │ • summarizer_exp                                     │  │ │
│  │   │ • translator_exp                                     │  │ │
│  │   └─────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### External Redirect Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │              ┌─────────────────────────────────┐           │ │
│  │              │    MLflow is configured at:      │           │ │
│  │              │                                  │           │ │
│  │              │    http://mlflow.example.com:5000│           │ │
│  │              │                                  │           │ │
│  │              │    [Open MLflow UI ↗]            │           │ │
│  │              │                                  │           │ │
│  │              └─────────────────────────────────┘           │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Storage

| Database | What | Owner |
|----------|------|-------|
| `mlflow.db` | Experiments, runs, metrics, traces | MLflow (not our schema) |

**Key Insight**: We do NOT modify MLflow's schema. We just provide access to it. Each execution in our `executions` table has a corresponding MLflow run with detailed traces.

---

## Data Flow Summary

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    USER     │
                              └──────┬──────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │          CHAT UI               │
                    │      (Entry Point)             │
                    │                                │
                    │  • Generate configs via chat   │
                    │  • See state machine           │
                    │  • Iterate on design           │
                    └───────────────┬────────────────┘
                                    │
                                    │ Stores:
                                    │ - chat_sessions
                                    │ - chat_messages
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌─────────────────────┐       ┌─────────────────────┐
        │   EXECUTE (Runtime) │       │   DEPLOY (Docker)   │
        │                     │       │                     │
        │ • Run in memory     │       │ • Build container   │
        │ • No container      │       │ • Start service     │
        │ • Show result       │       │ • Auto-register     │
        └──────────┬──────────┘       └──────────┬──────────┘
                   │                             │
                   │ Creates:                    │ Creates:
                   │ - executions                │ - deployments
                   │ - execution_states          │ (container starts
                   │ - deployment_id = NULL      │  heartbeat loop)
                   │                             │
                   │                             ▼
                   │               ┌─────────────────────────────┐
                   │               │      DEPLOYMENTS PAGE       │
                   │               │                             │
                   │               │ • View containers           │
                   │               │ • Health monitoring         │
                   │               │ • Execute on deployment     │
                   │               │ • Deregister                │
                   │               └──────────────┬──────────────┘
                   │                              │
                   │                              │ Execute creates:
                   │                              │ - executions
                   │                              │ - execution_states
                   │                              │ - deployment_id = "xxx"
                   │                              │
                   └──────────────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────────┐
                    │       EXECUTIONS PAGE          │
                    │                                │
                    │  • All runs (runtime+deployed) │
                    │  • Filter by source            │
                    │  • View details                │
                    │  • Link to MLflow traces       │
                    └───────────────┬────────────────┘
                                    │
                                    │ View traces
                                    ▼
                    ┌────────────────────────────────┐
                    │        MLFLOW PAGE             │
                    │                                │
                    │  • LLM traces per execution    │
                    │  • Experiments                 │
                    │  • Metrics & costs             │
                    │  (MLflow's own data)           │
                    └────────────────────────────────┘
```

### Database Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                                      │
└─────────────────────────────────────────────────────────────────────────────┘

configurable_agents.db
│
├── chat_sessions
│   └── session_id (PK)
│
├── chat_messages ───────────────────────┐
│   ├── id (PK)                          │
│   ├── session_id (FK) ─────────────────┴──► chat_sessions.session_id
│   └── ...
│
├── deployments
│   └── deployment_id (PK)
│
├── executions
│   ├── id (PK)
│   └── deployment_id (FK) ──────────────────► deployments.deployment_id
│       (nullable: NULL = runtime, set = deployed)    │
│                                                      │
├── execution_states ─────────────────────┐           │
│   ├── id (PK)                           │           │
│   ├── execution_id (FK) ────────────────┴───────────┴──► executions.id
│   └── ...
│
├── session_state (ProcessManager crash detection)
├── webhook_events (Webhook idempotency)
├── workflow_registrations (Webhook configs)
└── memory_records (Agent memory)


mlflow.db (SEPARATE - MLflow's schema)
│
├── experiments
├── runs
├── params
├── metrics
└── traces
```

---

## Internal Tables

These tables support internal features and don't have dedicated UI pages:

| Table | Purpose | Used By |
|-------|---------|---------|
| `session_state` | ProcessManager crash detection | `ui` command startup/shutdown |
| `webhook_events` | Webhook idempotency tracking | `webhooks` command |
| `workflow_registrations` | Webhook workflow configurations | `webhooks` command |
| `memory_records` | Agent memory persistence | Workflow execution |

---

## Renaming Summary

### Table Renaming

| Old Name | New Name | Page |
|----------|----------|------|
| `workflow_runs` | `executions` | Executions |
| `agents` | `deployments` | Deployments |
| `orchestrators` | *(removed)* | Absorbed into Deployments |

### Model Renaming

| Old Class | New Class |
|-----------|-----------|
| `WorkflowRunRecord` | `Execution` |
| `ExecutionStateRecord` | `ExecutionState` |
| `AgentRecord` | `Deployment` |
| `OrchestratorRecord` | *(removed)* |

### Repository Renaming

| Old Class | New Class |
|-----------|-----------|
| `AbstractWorkflowRunRepository` | `AbstractExecutionRepository` |
| `SQLiteWorkflowRunRepository` | `SQLiteExecutionRepository` |
| `AgentRegistryRepository` | `DeploymentRepository` |
| `SqliteAgentRegistryRepository` | `SqliteDeploymentRepository` |
| `OrchestratorRepository` | *(removed)* |

### CLI Command Renaming

| Old Command | New Command |
|-------------|-------------|
| `workflow-registry start` | `deployments start` |
| `workflow-registry list` | `deployments list` |
| `workflow-registry cleanup` | `deployments cleanup` |

---

## Key Design Decisions

1. **Chat UI as Entry Point**: Primary interface for creating and running workflows
2. **Table Names = Page Names**: `executions` → Executions page, `deployments` → Deployments page
3. **Orchestrator Absorbed**: All orchestration functionality merged into Deployments page
4. **Single App Database**: `configurable_agents.db` for all application data
5. **MLflow Separate**: `mlflow.db` remains MLflow's own database
6. **Execution → Deployment Link**: `deployment_id` FK distinguishes runtime vs deployed executions

---

## Implementation Notes

### Breaking Changes

1. **Table renames** require fresh database or migration
2. **Class renames** affect all code using old names
3. **CLI command renames** affect scripts and muscle memory

### Recommended Approach

1. Clean break for v1.0 (fresh database)
2. Update all code in single PR
3. Clear documentation for users

---

*This document is approved for implementation. See UI_PAGES_DESIGN.md for visual mockups.*
