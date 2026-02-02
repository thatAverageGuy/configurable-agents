# Technology Stack

**Analysis Date:** 2026-02-02

## Languages

**Primary:**
- Python 3.10+ - Core runtime for all application code, LLM orchestration, CLI, and deployment artifacts

**Secondary:**
- YAML - Workflow configuration format (user-facing DSL for defining agent workflows)
- JSON - Configuration interchange and output serialization

## Runtime

**Environment:**
- Python 3.10, 3.11, 3.12 (specified in `pyproject.toml` classifiers)
- Requires `GOOGLE_API_KEY` environment variable for LLM functionality
- Requires `SERPER_API_KEY` environment variable for web search tool

**Package Manager:**
- pip/setuptools (defined in `pyproject.toml`)
- Lockfile: present via `.venv` virtual environment
- Installation: `pip install -e .` or `pip install -e ".[dev]"` for development

## Frameworks

**Core Execution:**
- LangGraph 0.0.20+ (`src/configurable_agents/core/graph_builder.py`) - Graph-based agent execution engine
  - Uses `StateGraph`, `START`, `END` primitives for workflow orchestration
  - Compiles to `CompiledStateGraph` for runtime execution
- LangChain 0.1.0+ - LLM abstraction and tool orchestration framework
  - `langchain-core` 0.1.0+ - Base interfaces and ChatModel abstractions
  - `langchain-community` 0.0.20+ - Third-party tool integrations (Serper)
  - `langchain-google-genai` 1.0.0+ - Google Gemini provider implementation

**Data Validation & Schema:**
- Pydantic 2.0+ - Type validation and schema generation
  - Full schema validation at parse-time (`src/configurable_agents/config/schema.py`)
  - Structured output enforcement in LLM calls

**Configuration & Parsing:**
- PyYAML 6.0+ - YAML workflow configuration parsing (`src/configurable_agents/config/parser.py`)
- python-dotenv 1.0.0+ - Environment variable loading (`.env` files)

**CLI & UI:**
- FastAPI 0.109.1 - REST API server for deployed workflows (`deploy/server.py`)
- Streamlit 1.30.0+ - Web UI for workflow execution and deployment (optional, in `ui` extras)
- Uvicorn 0.27.0 - ASGI server for FastAPI containers

**Testing:**
- pytest 7.4.0+ - Test runner
- pytest-cov 4.1.0+ - Coverage measurement
- pytest-asyncio 0.21.0+ - Async test support

**Code Quality:**
- black 23.0.0+ - Code formatter
- ruff 0.1.0+ - Fast Python linter
- mypy 1.5.0+ - Static type checker (strict mode: `disallow_untyped_defs = true`)

**Observability:**
- MLFlow 3.9.0+ - Experiment tracking and observability
  - MLFlow tracing (auto-instrumentation via `mlflow.langchain.autolog()`)
  - SQLite backend for local tracking (`sqlite:///mlflow.db`)
  - GenAI dashboard for span visualization
  - Automatic token usage tracking

**Deployment:**
- Docker - Container runtime for workflow deployment
- Docker Compose - Multi-container orchestration in deployment templates

## Key Dependencies

**Critical:**
- pydantic>=2.0 - Full schema validation (parse-time fail-fast)
- langgraph>=0.0.20 - Execution engine (no alternatives in use)
- langchain>=0.1.0 - LLM abstraction layer
- langchain-google-genai>=1.0.0 - Google Gemini integration (v0.1 only provider)

**Infrastructure:**
- mlflow>=3.9.0 - Observability and cost tracking (required for `/report costs` CLI)
- fastapi>=0.109.1 - REST API server for deployments
- uvicorn>=0.27.0 - ASGI server
- streamlit>=1.30.0 - UI (optional dependency, only needed for `streamlit_app.py`)

## Configuration

**Environment Variables:**
```
GOOGLE_API_KEY          # Required: Google Gemini API key (https://ai.google.dev/)
SERPER_API_KEY          # Required: Serper web search API key (https://serper.dev)
MLFLOW_TRACKING_URI     # Optional: MLFlow tracking server (default: sqlite:///mlflow.db)
LOG_LEVEL               # Optional: Logging verbosity (INFO, DEBUG)
```

**Build Configuration:**
- `pyproject.toml` - Package metadata, dependencies, tool configuration
- `pytest.ini` - Test discovery and pytest settings
- `.env.example` - Template for environment variables
- `setup.sh` / `setup.bat` - Platform-specific setup scripts

**Tool Configuration:**
- `[tool.black]` - Code formatter (line-length: 100)
- `[tool.ruff]` - Linter (E, W, F, I, B, C4 rules enabled)
- `[tool.mypy]` - Type checker (strict mode, disallow_untyped_defs)
- `[tool.pytest.ini_options]` - Test discovery (testpaths: `tests/`)

## Platform Requirements

**Development:**
- Python 3.10+ with pip
- Docker (optional, for deployment testing)
- Git
- Virtual environment support

**Production:**
- Deployment target: Docker containers (no bare metal support documented)
- Container registry: No external registry required (local Docker builds)
- Runtime: Any system capable of running Docker (Linux, macOS, Windows with Docker Desktop)
- API endpoint: HTTP/FastAPI on configurable port (default: 8000)
- MLFlow UI: HTTP on configurable port (default: 5000)

## Version Constraints

**Python:**
- Minimum: 3.10
- Tested: 3.10, 3.11, 3.12
- No Python 2.x or pre-3.10 support

**LangChain Ecosystem:**
- langchain >= 0.1.0
- langgraph >= 0.0.20
- Explicitly supports LangGraph's StateGraph primitive

**LLM Provider (v0.1):**
- Google Gemini only
- Alternative providers (OpenAI, Anthropic) deferred to v0.2+
- See `src/configurable_agents/llm/provider.py:LLMProviderError` for provider validation

---

*Stack analysis: 2026-02-02*
