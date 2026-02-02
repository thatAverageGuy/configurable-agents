# External Integrations

**Analysis Date:** 2026-02-02

## APIs & External Services

**LLM Providers:**
- Google Gemini - Primary LLM for v0.1
  - SDK/Client: `langchain-google-genai` (v1.0.0+)
  - Auth: Environment variable `GOOGLE_API_KEY`
  - Implementation: `src/configurable_agents/llm/google.py:create_google_llm()`
  - Models: `gemini-2.5-flash-lite` (default), configurable via workflow config
  - API Key: Obtained from https://ai.google.dev/
  - Token usage: Auto-tracked via `usage_metadata` from LangChain response objects

**Web Search & Tools:**
- Serper (Google Search API) - Web search capability
  - SDK/Client: `langchain-community` GoogleSerperAPIWrapper
  - Auth: Environment variable `SERPER_API_KEY`
  - Implementation: `src/configurable_agents/tools/serper.py:create_serper_search()`
  - Tool Name: `serper_search` (LangChain Tool)
  - API Key: Obtained from https://serper.dev/
  - Usage: Optional tool in workflow configs via `tools: [serper_search]`

## Data Storage

**Databases:**
- SQLite (MLFlow backend)
  - Connection: File-based (`sqlite:///mlflow.db`)
  - Client: MLFlow 3.9.0+ (built-in SQLite adapter)
  - Purpose: Experiment tracking, trace storage, cost metrics
  - Location: Project root as `mlflow.db`
  - No application data persistence (workflows are stateless/in-memory)

**File Storage:**
- Local filesystem only
  - Workflow configuration: YAML files (user-provided)
  - Deployment artifacts: Generated in `./deploy/` directory
  - MLFlow database: `mlflow.db` in project root
  - No cloud storage integration in v0.1

**Caching:**
- None - In-memory state during workflow execution
- Workflows do not persist state between executions (v0.1 limitation)
- Future versions may add persistence (v0.2+)

## Authentication & Identity

**Auth Provider:**
- Custom API key approach (no central auth system)
  - Google API key for Gemini (direct integration)
  - Serper API key for search tool (direct integration)
  - No OAuth, JWT, or session management in v0.1
  - No user authentication for CLI or web UI

**Implementation:**
- Environment variables loaded via `python-dotenv`
- `.env` file template: `.env.example`
- Keys checked at initialization time (fail-fast validation)
- See `src/configurable_agents/llm/google.py` for key validation pattern

## Monitoring & Observability

**Error Tracking & Tracing:**
- MLFlow 3.9 GenAI tracing (primary observability)
  - Auto-instrumentation via `mlflow.langchain.autolog()`
  - Automatic span creation for LLM calls
  - No external error tracking (Sentry, DataDog, etc.)
  - Configuration: `src/configurable_agents/observability/mlflow_tracker.py`

**Logs:**
- Python logging module (stdlib)
  - Configuration: `src/configurable_agents/logging_config.py`
  - Output: Console and file (if configured)
  - Level control via `LOG_LEVEL` environment variable
  - Structured logging via MLFlow traces (for LLM calls)

**Metrics & Cost Tracking:**
- MLFlow 3.9 automatic token counting
  - Token usage captured from LLM responses
  - Cost estimation via `src/configurable_agents/observability/cost_estimator.py`
  - Pricing data hard-coded for Google Gemini models
  - Queryable via `configurable-agents report costs` CLI command

**Tracing & Visualization:**
- MLFlow UI at `http://localhost:5000` (default)
- GenAI dashboard for span waterfall visualization
- Accessible after workflow execution via `mlflow ui`
- No external APM tool integration (New Relic, Datadog, etc.)

## CI/CD & Deployment

**Hosting:**
- Docker containers (containerized deployment)
  - Server: FastAPI + Uvicorn
  - Port: 8000 (API, configurable)
  - Health check: `GET /health` endpoint
  - Async execution for long-running workflows
  - Sync timeout: 30 seconds (configurable)

**Container Orchestration:**
- Docker Compose (for local multi-container setup)
  - Templates: `deploy/docker-compose.yml`
  - Services: API server + MLFlow tracker (separate containers)
  - Network: Internal Docker network for inter-service communication

**CI Pipeline:**
- None detected (no GitHub Actions, Jenkins, or GitLab CI config)
- Local testing only: `pytest` command-line

**Deployment Automation:**
- CLI-driven: `configurable-agents deploy workflow.yaml`
  - Generates Dockerfile, docker-compose.yml, server code
  - Builds Docker image automatically
  - Starts containers with health checks
  - Configuration stored in generated artifacts

## Environment Configuration

**Required Environment Variables:**
```
GOOGLE_API_KEY       # Google Gemini API key (fail if missing)
SERPER_API_KEY       # Serper search API key (fail if tool used without key)
```

**Optional Environment Variables:**
```
MLFLOW_TRACKING_URI  # MLFlow backend (default: sqlite:///mlflow.db)
LOG_LEVEL            # Logging verbosity (default: INFO)
```

**Deployment-Specific Variables:**
- Generated in deployment containers via `deploy/Dockerfile`
- Keys sourced from host environment at build time
- No secrets management (requires external vault/secret system)

**Secrets Location:**
- `.env` file (local development, not committed to git)
- Environment variables at deployment time
- No external secret store (AWS Secrets Manager, HashiCorp Vault, etc.)
- Recommendation: Use external secret management for production

## Webhooks & Callbacks

**Incoming Webhooks:**
- None detected - Workflows are request/response only
- Future versions may add event-driven workflows (v0.2+)

**Outgoing Webhooks:**
- None detected - No external service callbacks
- Tool integration (Serper) is unidirectional (search request → results)

## Feature Gates

**Runtime Feature Gating:**
- MLFlow observability: Enabled/disabled via config
  - Check: `src/configurable_agents/runtime/feature_gate.py`
  - Can be disabled if MLFlow not available
- Multi-LLM support: Placeholder for v0.2+ (see `LLMProviderError`)

## Version Compatibility

**Upstream Dependencies (v0.1):**
- LangChain 0.1.0+: Stable minor versions expected
- LangGraph 0.0.20+: Pre-release (breaking changes possible)
- Google GenAI API: Stable (pricing model subject to change)
- MLFlow 3.9.0+: Stable

**Future Dependencies (v0.2+):**
- OpenAI API integration (planned)
- Anthropic Claude API (planned)
- DSPy (prompt optimization, v0.3)

---

*Integration audit: 2026-02-02*
