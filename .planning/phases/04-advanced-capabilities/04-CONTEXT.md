# Phase 4: Advanced Capabilities - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Building advanced runtime capabilities — code sandboxing, persistent memory, reusable tools, and MLFlow prompt optimization. This phase adds safety, persistence, modularity, and experimentation to the agent platform.

Deliverables:
- Safe code execution (RestrictedPython + Docker opt-in)
- Cross-run memory (configurable scope with namespaced keys)
- Tool ecosystem (essential LangChain integrations)
- Prompt optimization (MLFlow A/B testing with bidirectional sync)

These are infrastructure capabilities that users configure through YAML and manage through the existing dashboard UI from Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Code Sandbox

**Execution Mode:**
- **RestrictedPython by default** — Fast, portable, works everywhere without Docker
- **Docker opt-in** — User enables at workflow level: `use_docker: true`
- **Per-node override** — Can disable Docker for specific nodes: `sandbox: {mode: "python"}`
- **Rationale:** Portability first (local dev), security available for production

**Resource Limits:**
- **4 preset levels:** Low (0.5 CPU, 256MB, 30s), Medium (1 CPU, 512MB, 60s), High (2 CPU, 1GB, 120s), Max (4 CPU, 2GB, 300s)
- **Configurable per node:** `resources: {preset: "high", cpu: 3, memory: "1.5GB", timeout: 180s}`
- **Workflow default:** Set preset at workflow level, override per node if needed
- **Rationale:** Presets simplify common cases, customization allows edge cases

**Network Access:**
- **Enabled by default** — Allows web scraping, API calls, data fetching
- **User can disable explicitly:** `network: false` or `network: {enabled: false}`
- **Future extension:** Allowlist support for production hardening (not v1)
- **Rationale:** Most agent use cases need network access; opt-out for security-sensitive deployments

**Error Handling:**
- **Best-effort partial execution** — Graceful degradation where possible
- **Partial results debug-only** — Available via CLI/dashboard traces, not returned to workflow
- **Workflow sees error** — Node result includes error details, execution continues or fails based on workflow config
- **Rationale:** Debugging visibility without contaminating workflow logic with partial data

### Memory Persistence

**Memory Scope:**
- **Configurable per workflow** — Default scope set at workflow level: `memory: {default_scope: "agent"}`
- **Per-node override** — Can override scope for specific nodes: `memory: {scope: "workflow|node"}`
- **Three scopes available:**
  - `agent` — Shared across all workflows using this agent
  - `workflow` — Shared across nodes within a single workflow execution
  - `node` — Isolated to a specific node instance
- **Rationale:** Flexibility for different collaboration patterns

**Storage Backend:**
- **SQLite by default** — Uses existing storage abstraction, zero-config
- **Pluggable backends** — Can swap to Redis/Postgres via storage abstraction layer
- **Rationale:** Local-first simplicity with scale path

**Memory API (Hybrid):**
- **Dict-like reads** — `value = agent.memory['key']` for simple access
- **Explicit writes** — `agent.memory.write(key, value, ttl=None)` for persistence
- **Additional operations** — `memory.read(key, default=None)`, `memory.delete(key)`, `memory.list(prefix="")`
- **Rationale:** Natural Python syntax for reads, explicit writes for clarity

**Memory Keys:**
- **Namespaced structure** — Automatic namespacing to prevent conflicts
- **Namespace components** — `{agent_id}:{workflow_id}:{node_id}:{key}`
- **User sees simplified keys** — Agent writes `memory.write("last_query", "...")`, system stores as `agent_123:workflow_456:node_789:last_query`
- **Rationale:** Deterministic key structure prevents collisions between agents/workflows

**Retention:**
- **Forever by default** — No automatic eviction, memory persists until explicitly cleared
- **Manual clearing** — API (`memory.clear()`) and dashboard UI for cleanup
- **Future extension:** TTL support per key (not v1)
- **Rationale:** User has full control, no surprises from auto-deletion

### Tool Integration

**Tool Selection:**
- **Essential subset (~10-15 tools)** — Focus on high-value, commonly-used tools
- **Four categories:**
  - **Web tools:** `web_search` (Serper/Tavily), `web_scrape` (BeautifulSoup), `http_client` (requests)
  - **File tools:** `file_read`, `file_write`, `file_glob`, `file_move`
  - **Data tools:** `sql_query`, `dataframe_to_csv`, `json_parse`, `yaml_parse`
  - **System tools:** `shell` (run command), `process` (spawn/monitor), `env_vars` (read environment)
- **Rationale:** Cover 80% of use cases with minimal maintenance burden

**Tool Configuration:**
- **Hybrid approach** — Simple list with defaults, override specific tools with detailed config
- **Example:**
  ```yaml
  tools: ["web_search", "file_read"]
  # Override specific tools:
  tools: [
    "web_search",  # Uses default provider (Serper)
    {name: "file_read", path: "/custom/data"}
  ]
  ```
- **Default providers** — Configurable via environment variables (e.g., `WEB_SEARCH_PROVIDER=serper`)
- **Rationale:** Simplicity for common cases, flexibility when needed

**Custom Tools:**
- **Not in v1** — Only pre-built LangChain tools available
- **Future extension:** User can register Python functions as tools via API (v2+)
- **Rationale:** Reduce complexity, validate core workflow first

**Tool Results:**
- **Structured only** — Results returned as native Python types (dict, list, str, int, etc.)
- **Type information preserved** — Workflow can process results programmatically
- **Rationale:** Type safety, enables data flow between tools and agents

**Error Handling:**
- **Configurable per tool** — `tools: [{name: "web_search", on_error: "continue|fail"}]`
- **Default:** Errors fail the node (fail-fast for reliability)
- **Continue mode** — Tool errors are caught and returned as error results, workflow continues
- **Rationale:** Flexibility for different reliability requirements

### MLFlow Optimization

**Experiment Organization:**
- **Hybrid approach** — Workflow-level default with node-level override
- **Workflow-level:** `mlflow: {experiment: "my-workflow-ab-test"}` — All nodes tracked under this experiment
- **Node-level override:** `nodes: [{name: "agent", mlflow: {experiment: "prompt-variants"}}]`
- **Rationale:** Most users want workflow-level grouping, power users need node-level granularity

**A/B Testing:**
- **Config + manual support** — Two complementary approaches:
  - **Config variants (declarative):** Define variants in YAML, system runs all automatically
    ```yaml
    mlflow:
      variants:
        - name: "concise"
          prompt: "You are a concise assistant..."
        - name: "detailed"
          prompt: "You are a detailed assistant..."
    ```
  - **Manual runs (flexible):** Run workflow multiple times with different prompts, MLFlow groups results
- **Rationale:** Config variants for automation, manual runs for exploratory testing

**Metrics Tracking:**
- **Built-in + custom** — Best of both worlds
- **Built-in metrics (automatic):** Cost, latency, token count, success/failure status
- **Custom metrics (user-defined):** Add via callback API or node config
- **Rationale:** Immediate value without setup, extensibility for advanced use cases

**Result Comparison:**
- **Both CLI and Dashboard** — Complementary interfaces:
  - **CLI:** `gsd evaluate --experiment "prompt-test" --metric cost` — Automation-friendly
  - **Dashboard UI:** Embedded in orchestration UI with visual charts — Exploration-friendly
- **Rationale:** CLI for CI/CD and automation, UI for interactive analysis

**Quality Gates:**
- **Global action configuration** — Consistent behavior across all gates
- **Example:**
  ```yaml
  mlflow:
    gates:
      - metric: "cost"
        max: 0.50
      - metric: "latency"
        max: 30
    on_fail: "warn"  # or "fail" or "block_deploy"
  ```
- **Actions:**
  - `warn` — Gates warn but don't fail, runs complete, warnings logged
  - `fail` — Workflow fails if gates exceeded, run marked as failed
  - `block_deploy` — Cannot deploy workflow if quality gates fail in testing
- **Rationale:** Consistent behavior, flexibility for different environments (dev vs prod)

**Prompt Versioning:**
- **Bidirectional sync** — YAML and MLFlow stay synchronized:
  - **YAML→MLFlow:** Every run tracks prompt config from YAML
  - **MLFlow→YAML:** Users can apply optimized prompts from MLFlow back to YAML (with approval)
- **Apply methods (all 3 supported):**
  - **CLI:** `gsd apply-optimized --experiment "test" --variant "best"` — Automation
  - **Dashboard UI:** "Apply" button with diff review — Interactive
  - **Suggestions only:** MLFlow suggests optimizations, user manually updates YAML — Manual control
- **Deployed containers:** Hot-reload config when YAML changes, or restart to pick up updates
- **Rationale:** Git is source of truth, MLFlow is experimentation layer, bidirectional flow enables optimization loop

### Claude's Discretion

**Code Sandbox:**
- Exact RestrictedPython implementation (AST-based or compile-based)
- Docker image base and dependencies
- Partial result formatting in debug output
- Exact error messages and logging levels

**Memory Persistence:**
- Memory schema in SQLite (table structure, indexing)
- Namespace separator character (`:` vs `.` vs `/`)
- Memory cleanup API design (bulk delete, wildcard patterns)
- Dashboard UI for memory inspection and management

**Tool Integration:**
- Exact list of tools in each category (final 10-15 selection)
- Tool parameter validation and error messages
- Tool result size limits (for memory/storage safety)
- Tool execution timeout handling

**MLFlow Optimization:**
- MLFlow experiment naming conventions
- Metric aggregation strategies (avg, p95, p99)
- Visualization chart types in dashboard
- Prompt diff presentation in apply workflow

</decisions>

<specifics>
## Specific Ideas

**Code Sandbox:**
- "I want it to be easy to develop locally with RestrictedPython, then switch to Docker for production"
- "Resource presets should cover dev (Low), staging (Medium), production (High), and heavy workloads (Max)"

**Memory Persistence:**
- "Namespaced keys are important — I don't want agent A's memory clobbering agent B's memory"
- "Forever retention because I want agents to build up long-term knowledge"

**Tool Integration:**
- "Start with essential tools — we can add more based on user demand post-v1"
- "Structured tool results for type safety"

**MLFlow Optimization:**
- "Config variants are more crazy and awesome" — Declarative A/B testing in YAML
- "Both CLI and dashboard for different workflows: CLI for automation, UI for exploration"
- "Deployed containers need to get prompt updates — hot-reload or restart"

</specifics>

<deferred>
## Deferred Ideas

**Code Sandbox:**
- Network allowlist for production hardening (network: {allow: ["api.openai.com"]})
- Firecracker microVM support for even stronger isolation
- Code signing and verification for untrusted code execution

**Memory Persistence:**
- TTL-based eviction (memory.write(key, value, ttl="7d"))
- Semantic memory search (vector embeddings for memory retrieval)
- Memory export/import between agents

**Tool Integration:**
- Custom tool registration (user functions as tools)
- Tool marketplace or plugin system
- Full LangChain tool registry (500+ tools)

**MLFlow Optimization:**
- Multi-armed bandit algorithms for automatic prompt optimization
- Automated prompt engineering (LLM-generated prompt variants)
- Federated learning across deployments

</deferred>

---

*Phase: 04-advanced-capabilities*
*Context gathered: 2026-02-03*
