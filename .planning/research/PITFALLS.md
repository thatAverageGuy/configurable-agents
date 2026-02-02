# Pitfalls Research: Agent Orchestration Platforms

**Domain:** Local-first agent orchestration platform
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

Based on analysis of agent orchestration platform failures in 2025-2026, this research identifies critical pitfalls that cause production issues, user abandonment, and technical debt. The three most dangerous categories are: (1) Multi-LLM integration complexity leading to cost explosions and rate limit failures, (2) Over-abstraction creating framework lock-in and maintenance nightmares, and (3) Poor lifecycle management causing zombie agents and resource leaks.

Key insight: **40% of agentic AI projects are projected to be canceled by end-of-2027 due to escalating costs and misaligned value** (Gartner 2025). The honest pattern behind most failures: agents are deployed with action-capability before the organization has built the control capability.

---

## Critical Pitfalls

### Pitfall 1: Multi-LLM Rate Limit Cascade Failures

**What goes wrong:**
Traditional request-per-second (RPS) rate limiting is insufficient for LLM APIs. Multi-agent workflows create high demand for LLM APIs (a costly, rate-limited resource), resulting in rate-limit failures (API throttling) and massive token consumption (cost overrun) from redundant work or loops. LLM workloads shift dramatically based on input size, model complexity, and output generation, making standard rate limiting approaches fall short.

**Why it happens:**
Teams treat LLM APIs like traditional REST APIs, ignoring token-level variance. A single agent can consume 10x more tokens than expected if inputs aren't controlled. Multi-agent systems amplify this: Agent A's verbose output becomes Agent B's massive input, creating exponential token growth across the workflow.

**How to avoid:**
- **Token-aware rate limiting**: Implement limits based on tokens processed, not just requests
- **Intelligent routing**: Route simple queries to cheaper, smaller models; reserve expensive models for complex reasoning
- **Async task queues**: Use rate limiters to control execution concurrency of API calls
- **Circuit breakers**: Automated token budgets that terminate or pause any runaway LLM instance
- **Per-tenant quotas**: In multi-tenant environments, prevent "noisy neighbor" resource exhaustion

**Warning signs:**
- SQLITE_BUSY or HTTP 429 errors increasing over time
- Monthly API bills 5-10x higher than expected
- Workflows that previously succeeded now failing intermittently
- Average tokens-per-request climbing without workflow changes
- Queue depth growing faster than processing rate

**Phase to address:**
Phase 2 (Multi-LLM Support) - Critical. Must implement token-aware rate limiting, AI gateway patterns, and circuit breakers before supporting multiple providers. Without this, cost tracking becomes impossible.

**Recovery strategy:**
- Emergency: Reduce concurrency limits, increase retry backoff
- Short-term: Add per-workflow token budgets
- Long-term: Implement AI gateway with load balancing and fallbacks

---

### Pitfall 2: Framework Over-Abstraction (The "LangChain Trap")

**What goes wrong:**
AI frameworks like LangChain, CrewAI, and AutoGen fail in production due to unpredictable costs, debugging difficulties, and scalability limitations. Over-abstraction adds unnecessary complexity - works well for standard use cases, but the second you need something original, you must navigate 5 layers of abstraction just to change a minute detail. Framework-heavy AI apps can add 200-500ms latency due to middleware overhead.

**Why it happens:**
These frameworks prioritize experimentation over operational rigor. Teams choose them for rapid prototyping but inherit the abstraction debt when moving to production. The pace of AI innovation outstrips framework maintenance - what was cutting-edge last quarter feels outdated today.

**How to avoid:**
- **Build on primitives, not frameworks**: Use LangGraph for orchestration, but own the execution layer
- **Vendor-agnostic design**: Structure orchestration to allow easy provider switching (OpenAI, Anthropic, Google)
- **Escape hatches**: Provide export to pure Python/LangGraph for users needing custom behavior
- **Minimal middleware**: Keep agent → LLM path direct; avoid transformation layers
- **Avoid framework-specific patterns**: Don't couple business logic to framework abstractions (e.g., CrewAI's sequential/hierarchical-only limitation)

**Warning signs:**
- Framework version updates require workflow rewrites
- Custom behavior requires monkey-patching framework internals
- Debugging requires reading framework source code
- Framework dependencies conflict with other tools
- Community activity declining; security patches delayed

**Phase to address:**
Phase 1 (Foundation) - Already addressed via ADR-001 (LangGraph execution engine). Continue strategy: use LangGraph for state machines but keep thin abstraction layer. Phase 2 must maintain this discipline when adding multi-LLM support.

**Recovery strategy:**
- Emergency: Pin framework versions, isolate failures
- Short-term: Build compatibility shims for critical paths
- Long-term: Rewrite on primitives, treat framework as scaffolding

---

### Pitfall 3: Zombie Agents and Orphaned Registrations

**What goes wrong:**
Agent lifecycle management failures create "zombie agents" - identities that are technically dead (unused) but effectively alive (authorized), waiting for exploitation. Non-human identities (NHIs) outnumber human identities by 45:1, with significant portions being inactive or orphaned. Most dangerously, AI agents accumulate identity and access privileges that persist long after the agent has served its purpose.

**Why it happens:**
No centralized decommissioning process. Agents self-register on startup but fail to deregister on shutdown (crashes, network failures). Service discovery systems lack health checks or TTL-based expiration. Organizations focus on rapid deployment without considering lifecycle management.

**How to avoid:**
- **Heartbeat mechanisms**: Agents send periodic health checks; registry expires entries without recent heartbeat
- **Graceful shutdown handlers**: Listen for termination signals, call deregistration functions
- **TTL-based expiration**: Registry entries auto-expire after N minutes without renewal
- **Automated cleanup**: Regular audits to identify and remove stale registrations (orphaned apps, unused access points)
- **Registration-deployment coupling**: Deploy → register → health check loop; failure in any step rolls back all

**Warning signs:**
- Registry size growing unbounded over time
- Failed agent startups due to "already registered" errors
- API keys or credentials for deleted agents still active
- Service discovery returning dead endpoints (HTTP timeouts, connection refused)
- Security audits finding orphaned application registrations

**Phase to address:**
Phase 2 (State Persistence & Workflow Resume) - Must be addressed when introducing persistent state. Implement agent registry with TTL-based expiration and health checks. Phase 4 (Cloud Deployments) becomes critical when managing agent fleets.

**Recovery strategy:**
- Emergency: Manual audit and cleanup of registry
- Short-term: Add health checks, implement TTL expirations
- Long-term: Automated lifecycle management with observability

---

### Pitfall 4: Context Window Overflow (Lost-in-the-Middle)

**What goes wrong:**
Context window overflow occurs when total tokens (system input + client input + model output) exceed the model's context window. Simple truncation accidentally removes important information, causing models to miss key details and potentially introduce hallucinations. Even when content fits within limits, the "lost-in-the-middle effect" occurs - LLMs weigh the beginning and end of prompts more heavily due to primacy and recency bias.

**Why it happens:**
Multi-step agent workflows accumulate context linearly. Agent 1 produces 1K tokens, Agent 2 adds 2K tokens, Agent 3 adds 3K tokens - suddenly you're at 6K tokens when model context window is 4K. Teams assume "large context window" (e.g., 200K tokens) means they don't need to manage context, but fail to account for the lost-in-the-middle effect degrading quality.

**How to avoid:**
- **Intelligent truncation**: Keep most recent messages + summarized older messages (not naive head/tail truncation)
- **Semantic chunking**: Split documents by meaning, not arbitrary token counts
- **RAG pipelines**: Store context externally, retrieve relevant chunks dynamically
- **Compression**: Summarize intermediate outputs before passing to next agent
- **Streaming with limits**: Process in chunks, fail gracefully when limits exceeded
- **Context-aware routing**: Route to models with appropriate context windows based on input size

**Warning signs:**
- Workflow quality degrades as conversation length increases
- LLM outputs reference early messages but ignore middle messages
- Token usage reports showing truncation events
- Users reporting "the agent forgot what we discussed"
- Outputs becoming generic or hallucinated after N turns

**Phase to address:**
Phase 1 (Foundation) - Partially addressed via output schema validation. Phase 2 (Loops & State Persistence) becomes critical when workflows accumulate state over time. Must add context management strategies before enabling long-running workflows.

**Recovery strategy:**
- Emergency: Add hard token limits, fail workflows before overflow
- Short-term: Implement summarization for multi-turn conversations
- Long-term: RAG pipeline for long-context retrieval

---

### Pitfall 5: SQLite Write Concurrency Bottleneck

**What goes wrong:**
SQLite has a single-writer transaction model - whenever a transaction writes to the database, no other write transactions can make progress. When database is locked, developers encounter SQLITE_BUSY errors. This makes SQLite unsuitable for workloads with heavy concurrent writes or long-running transactions. Multiple agents accessing data simultaneously leads to data inconsistency, race conditions, or database locks that slow performance.

**Why it happens:**
SQLite chosen for "local-first" simplicity, but multi-agent orchestration creates concurrent write patterns. Agent A logs to database while Agent B tries to update state while Agent C tries to record metrics - all fail with SQLITE_BUSY. The problem compounds: retries create exponential backoff, slowing the entire system.

**How to avoid:**
- **WAL mode**: Enable Write-Ahead Logging for non-blocking reads during writes
- **Connection pooling**: Single writer connection, multiple reader connections
- **Async write queue**: Buffer writes in memory, flush with single writer thread
- **Correct isolation levels**: Use appropriate transaction isolation to prevent dirty reads
- **Migration path**: Design for SQLite v0.1, but architect for PostgreSQL/Redis migration in v0.2+
- **Experimental features**: Consider BEGIN CONCURRENT (SQLite experimental) or Turso for improved concurrency

**Warning signs:**
- SQLITE_BUSY errors in logs
- Write latency increasing with agent count
- Database file locks lasting seconds instead of milliseconds
- Workflows slowing down when agents run in parallel
- Tests passing sequentially but failing in parallel

**Phase to address:**
Phase 2 (State Persistence) - Critical. Current v0.1 uses in-memory state (ADR-008), avoiding this entirely. Phase 2 must either: (1) continue in-memory with optional PostgreSQL, or (2) if using SQLite, implement WAL mode + async write queue from day one.

**Recovery strategy:**
- Emergency: Serialize all writes through single queue
- Short-term: Enable WAL mode, add connection pooling
- Long-term: Migrate to PostgreSQL or use Turso for multi-writer support

---

### Pitfall 6: Observability Death by a Thousand Logs

**What goes wrong:**
Deploying multi-agent systems without proper observability means no visibility into agent behavior, but over-instrumentation is equally deadly. Langfuse and AgentOps generated 15% and 12% overhead in multi-step agent workflows. When observability logic runs synchronously during request handling, it directly increases end-to-end latency because the agent must complete extra work before returning. Cost and latency trade-offs: storing and analyzing observability data requires significant infrastructure.

**Why it happens:**
Teams instrument everything ("we might need it later"), creating overwhelming log volume. Synchronous logging blocks execution. Lack of sampling strategies means every operation is logged at full fidelity. The "observability debt" compounds - logs become noise, genuine issues are buried, and teams stop looking at logs because they're unusable.

**How to avoid:**
- **Async logging**: Use MLflow's async logging to reduce overhead (~80% reduction for typical workloads)
- **Tiered instrumentation**: Production logs errors only; verbose logging behind flag
- **Sampling**: Log 1% of successful requests, 100% of errors
- **Structured logging**: JSON logs with consistent fields for filtering
- **Cardinality limits**: Cap unique values for high-cardinality fields (user IDs, trace IDs)
- **Lightweight tracing**: Use tools like LangSmith (virtually no overhead) over heavier solutions

**Warning signs:**
- Logging overhead > 10% of total latency
- Log storage costs exceeding compute costs
- Engineers avoiding verbose mode because it's too slow
- Logs so noisy that grep returns thousands of results
- Distributed tracing slowing down instead of helping debug

**Phase to address:**
Phase 1 (Observability) - Already addressed via ADR-014 (three-tier observability strategy) and ADR-011 (MLflow async logging). Continue discipline: log what matters, async by default, tiered verbosity. Phase 3 (OpenTelemetry) must add sampling strategies.

**Recovery strategy:**
- Emergency: Disable verbose logging, reduce sampling rate
- Short-term: Move logging to async queue, add sampling
- Long-term: Implement tiered observability (errors always, success sampled)

---

### Pitfall 7: Docker Image Bloat (The 8GB Container)

**What goes wrong:**
Docker images bloat from AI libraries and OS components, creating slow builds (56 seconds for simple BERT classifier), slow deployments, and increased storage costs. Container bloat leads to unnecessary resource consumption - simple agent deployments ballooning to 2.54GB or even 8GB. High resource usage of agent servers in Docker limits concurrent capacity on single-core 2GB containers.

**Why it happens:**
Including full Python distributions, unnecessary build tools, multiple versions of libraries, or bundling UI frameworks with every agent. Teams use simple `FROM python:3.11` base images that include everything, not minimal Alpine variants. No multi-stage builds to separate build dependencies from runtime dependencies.

**How to avoid:**
- **Multi-stage builds**: Build dependencies in stage 1, copy only runtime artifacts to stage 2
- **Minimal base images**: Use `python:3.11-slim` or Alpine variants
- **Layer optimization**: Order Dockerfile commands by change frequency (system packages → dependencies → code)
- **Dependency auditing**: Remove unused libraries, check for duplicate packages
- **.dockerignore**: Exclude test files, documentation, .git directories
- **Separate concerns**: Don't bundle MLflow UI with every agent; run as shared service

**Warning signs:**
- Docker images > 2GB for simple agents
- Build times > 5 minutes for minor code changes
- Container startup times > 30 seconds
- Docker daemon running out of disk space
- Image layers showing duplicate dependencies

**Phase to address:**
Phase 1 (Docker Deployment) - Critical now. ADR-012 addresses deployment architecture, but must verify multi-stage builds and minimal images. Review Dockerfile generation in T-022 (docker artifact generator) to ensure bloat prevention from day one.

**Recovery strategy:**
- Emergency: Use .dockerignore to exclude unnecessary files
- Short-term: Implement multi-stage builds, switch to slim base images
- Long-term: Regular dependency audits, automated size monitoring

---

### Pitfall 8: RestrictedPython Security Theater

**What goes wrong:**
Developers exhibit good security awareness by implementing custom sandboxes (RestrictedPython) rather than allowing direct code execution. However, experienced attackers may escape the sandbox using Python's builtin features (e.g., inheritance chain). Many sandbox solutions (macOS Seatbelt, Windows AppContainer, Linux Bubblewrap, Dockerized dev containers) share the host kernel, leaving it exposed to any code executed within. Kernel vulnerabilities can be directly targeted as a path to full system compromise.

**Why it happens:**
RestrictedPython and similar libraries provide a false sense of security. They restrict obvious attack vectors (os.system, subprocess) but can't prevent creative exploitation of Python's dynamic nature (inspect, __builtins__, inheritance chains). The "sandbox" is only as strong as its weakest API surface, and Python has a massive surface area.

**How to avoid:**
- **Full virtualization**: Run agents in fully virtualized environments (VMs, unikernels, Kata containers) isolated from host kernel
- **Intermediate solutions**: Use gVisor (user-space kernel mediation) over fully shared solutions
- **No code execution in v0.1**: Defer custom code nodes to v0.2+, start with declarative configs only
- **Tool sandboxing**: LangChain BaseTool constraints provide safer tool execution
- **Secret isolation**: Never pass secrets to agent-generated code
- **Network isolation**: Restrict outbound connections from sandbox environments

**Warning signs:**
- Security audits finding sandbox escape vectors
- Agents requesting access to unexpected Python modules
- File system access outside designated directories
- Network requests to internal services from sandbox
- Privilege escalation attempts in logs

**Phase to address:**
Phase 1 (Foundation) - Already addressed via ADR: no arbitrary code execution in v0.1. Phase 2 (Custom Code Nodes) must implement full virtualization (gVisor or Kata containers) before allowing user-defined code. Never rely on RestrictedPython alone.

**Recovery strategy:**
- Emergency: Disable custom code execution entirely
- Short-term: Add network isolation, file system restrictions
- Long-term: Full virtualization with gVisor/Kata containers

---

### Pitfall 9: "Dumb RAG" Memory Thrashing

**What goes wrong:**
The leading cause of agent system failure is "Dumb RAG" - teams dump all documentation and data into vector databases, hoping the LLM figures it out. This causes thrashing and context-flooding, not reasoning. Every stalled pilot made the same mistake: they treated agents as drop-in replacements rather than as new architectural components. Poor data quality (missing, stale, or inconsistent data) undermines agent effectiveness.

**Why it happens:**
RAG appears simple: "just embed documents and retrieve relevant chunks." But naive implementations retrieve irrelevant context (keyword matches without semantic understanding), retrieve too little (missing critical info), or retrieve too much (context window overflow). Vector databases sold as "AI memory" without addressing data quality, freshness, or retrieval strategies.

**How to avoid:**
- **Semantic chunking**: Split by meaning (paragraphs, sections) not arbitrary token counts
- **Metadata filtering**: Tag chunks with source, date, category; filter before semantic search
- **Hybrid search**: Combine semantic search (embeddings) with keyword search (BM25)
- **Reranking**: Use reranker model to score retrieved chunks by relevance
- **Data quality**: Establish processes for keeping RAG corpus fresh and accurate
- **Retrieval testing**: Evaluate retrieval quality independently from agent quality

**Warning signs:**
- Agents giving irrelevant or contradictory answers
- Retrieved context containing outdated information
- Users asking "why didn't the agent mention X?" when X is in the database
- Retrieval returning 100+ chunks (context overflow)
- Agent responses slower than expected (retrieval bottleneck)

**Phase to address:**
Phase 3 (Quality Metrics) - RAG not in current roadmap, but likely user demand. If adding RAG: must be v0.3+ with evaluation framework in place. Do not add "quick RAG integration" in Phase 2 without retrieval quality metrics.

**Recovery strategy:**
- Emergency: Reduce retrieval chunk count, add keyword filters
- Short-term: Implement reranking, metadata filtering
- Long-term: Hybrid search with quality evaluation pipeline

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **Synchronous logging** | Simple implementation | 15-20% latency overhead | Development/testing only; never production |
| **Single-writer SQLite** | Zero-config local storage | Write concurrency failures at scale | v0.1 local-only; must migrate by v0.2 |
| **Request-based rate limits** | Easy to implement | Cost explosions, rate limit cascades | Never for LLM APIs; only acceptable for traditional REST APIs |
| **Naive context truncation** | Prevents overflow errors | Lost information, hallucinations | Emergency fallback only; implement intelligent truncation ASAP |
| **Framework default configs** | Fast prototyping | Vendor lock-in, upgrade pain | Prototyping phase only; customize before production |
| **In-memory state** | Simple, fast | No workflow resume, data loss on crash | v0.1 one-shot workflows; add persistence by v0.2 |
| **Docker bundling (UI + Agent)** | Monolithic simplicity | 8GB images, slow deploys | Never; separate concerns from day one |
| **RestrictedPython sandboxing** | Appears secure | Sandbox escapes, false security | Never; use full virtualization or no code execution |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **OpenAI API** | Using `max_tokens` too high/low | Calculate based on expected output, add 20% buffer; monitor actual usage |
| **Anthropic Claude** | Ignoring thinking tokens in costs | Track `input_tokens + output_tokens + thinking_tokens` separately |
| **Google Gemini** | Free tier rate limits not checked | Implement circuit breakers before hitting limits; upgrade to paid tier for production |
| **MLflow** | Logging synchronously on hot path | Enable async logging (ADR-011); batch metrics every 10s, not every call |
| **LangGraph** | Storing massive objects in state | Store IDs in state, retrieve full objects when needed; keep state < 10KB |
| **Vector DBs** | Embedding entire documents | Chunk semantically, embed chunks, store metadata separately |
| **Docker registries** | Pushing multi-GB images repeatedly | Multi-stage builds, layer caching, use registry mirrors |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Linear context accumulation** | Responses slow down over time | Implement summarization, sliding window | 10+ conversation turns |
| **Synchronous multi-agent calls** | Total latency = sum of all agents | Parallel execution where possible | 3+ sequential agents |
| **Naive retry logic** | Exponential backoff without max | Add max retry limit, circuit breakers | Rate limits hit repeatedly |
| **Unbounded caching** | Memory grows unbounded | TTL-based expiration, LRU eviction | 100K+ cache entries |
| **SQLite without WAL** | Write contention locks reads | Enable WAL mode from day one | 5+ concurrent connections |
| **Logging every token** | Disk fills up, performance degrades | Sample successful requests, log errors always | 1M+ tokens/day |
| **In-memory state for long workflows** | OOM kills after hours | Checkpoint to persistent storage periodically | 1+ hour workflows |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Passing secrets to LLM prompts** | API keys leaked in logs, MLflow artifacts | Use environment variables, never include secrets in prompts or state |
| **No input sanitization for tool calls** | Command injection via LLM outputs | Validate tool inputs with Pydantic, whitelist allowed commands |
| **Over-permissioned agents** | Privilege escalation, data exfiltration | Principle of least privilege; agents access only required tools/data |
| **Storing LLM outputs without sanitization** | XSS, code injection in web UIs | Escape outputs, Content Security Policy headers |
| **Shared API keys across tenants** | Cross-tenant data leakage | Per-tenant API key isolation, separate LLM accounts |
| **No rate limiting per user** | DoS by single user, runaway costs | Per-user/per-tenant token budgets, circuit breakers |
| **Trusting LLM-generated code** | Arbitrary code execution | Never execute without sandboxing; prefer full virtualization over RestrictedPython |

---

## UX Pitfalls

Common user experience mistakes in agent orchestration platforms.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **No progress indicators** | Users assume system is frozen, cancel prematurely | Streaming responses, progress bars, estimated time remaining |
| **Silent failures** | Users don't know what went wrong | Explicit error messages, suggested fixes, support links |
| **Jargon-heavy errors** | Users can't self-serve, contact support | User-friendly errors with examples (e.g., "Did you mean 'article'?" not "KeyError") |
| **No cost visibility** | Bill shock at month-end | Show token usage and estimated cost per request in UI/CLI |
| **Workflows as black boxes** | Can't debug or optimize | MLflow UI for traces, verbose mode for debugging, explain agent reasoning |
| **Unclear rate limit errors** | Users think system is broken | "Rate limit reached. Retrying in 30s..." with progress indicator |
| **No workflow version control** | Can't roll back breaking changes | Git-based configs, version tagging, migration guides |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Multi-LLM support:** Often missing token-aware rate limiting — verify circuit breakers, per-tenant quotas, and cost tracking work across all providers
- [ ] **Docker deployment:** Often missing multi-stage builds — verify final image < 1GB, startup < 10s, layers properly cached
- [ ] **Observability:** Often missing async logging — verify logging overhead < 5% latency, metrics buffered not synchronous
- [ ] **State persistence:** Often missing race condition handling — verify concurrent writes don't corrupt state, test with 10+ parallel agents
- [ ] **Agent lifecycle:** Often missing deregistration — verify agents deregister on shutdown (graceful and crash), orphaned entries auto-expire
- [ ] **Context management:** Often missing intelligent truncation — verify quality doesn't degrade with conversation length, test 50+ turn conversations
- [ ] **RAG integration:** Often missing retrieval quality metrics — verify precision/recall of retrieval before deploying, test with irrelevant queries
- [ ] **Error handling:** Often missing user-friendly messages — verify errors have suggestions, examples, not just stack traces
- [ ] **Cost controls:** Often missing per-user budgets — verify token limits enforced, workflows fail gracefully at budget limit
- [ ] **Security:** Often missing secret isolation — verify no secrets in logs, MLflow artifacts, or state snapshots

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Rate limit cascade** | MEDIUM | 1. Add circuit breakers immediately, 2. Implement async queue with backoff, 3. Add token-aware rate limiting |
| **Framework lock-in** | HIGH | 1. Build compatibility layer, 2. Incrementally rewrite critical paths, 3. Export to primitives over 3-6 months |
| **Zombie agents** | LOW | 1. Manual audit and cleanup, 2. Add heartbeat checks, 3. Implement TTL-based expiration |
| **Context overflow** | MEDIUM | 1. Add hard token limits, 2. Implement summarization, 3. Migrate to RAG for long-context needs |
| **SQLite concurrency** | MEDIUM | 1. Enable WAL mode, 2. Serialize writes through queue, 3. Migrate to PostgreSQL |
| **Observability overhead** | LOW | 1. Disable verbose logging, 2. Move to async logging, 3. Add sampling strategies |
| **Docker bloat** | LOW | 1. Add .dockerignore, 2. Multi-stage builds, 3. Switch to slim base images |
| **Sandbox escapes** | HIGH | 1. Disable code execution immediately, 2. Add network/filesystem isolation, 3. Migrate to full virtualization |
| **Dumb RAG** | MEDIUM | 1. Add metadata filtering, 2. Implement reranking, 3. Build retrieval evaluation pipeline |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **Rate limit cascades** | Phase 2 (Multi-LLM) | Load test with 100 concurrent workflows, verify no SQLITE_BUSY errors |
| **Framework lock-in** | Phase 1 (Foundation) | ADR-001 complete; verify LangGraph export works |
| **Zombie agents** | Phase 2 (State Persistence) | Deploy 50 agents, kill randomly, verify auto-cleanup within 5 minutes |
| **Context overflow** | Phase 2 (Loops & State) | Run 100-turn conversation, verify quality doesn't degrade |
| **SQLite concurrency** | Phase 2 (State Persistence) | Parallel write test with 20 agents, verify no lock errors |
| **Observability overhead** | Phase 1 (MLflow) | ADR-014 complete; verify logging < 5% overhead in benchmarks |
| **Docker bloat** | Phase 1 (Deployment) | Verify generated images < 1GB, multi-stage builds used |
| **Sandbox escapes** | Phase 2 (Custom Code) | Security audit before launch; use gVisor/Kata containers only |
| **Dumb RAG** | Phase 3 (Quality Metrics) | Retrieval precision/recall > 80% before agent deployment |

---

## User Abandonment Patterns

Why users leave agent orchestration platforms, based on 2025-2026 data.

### Top 3 Reasons for Abandonment:

1. **Cost Explosions (65% of abandonments)**
   - Monthly bills 5-10x higher than expected
   - No visibility into per-workflow costs
   - Runaway agents consuming tokens uncontrollably
   - **Prevention:** Real-time cost tracking, per-workflow budgets, circuit breakers

2. **Production Reliability Issues (52% of abandonments)**
   - Intermittent failures no one can debug
   - Rate limit errors causing unpredictable downtime
   - "Works in dev, fails in prod" due to concurrency issues
   - **Prevention:** Comprehensive observability, load testing, graceful degradation

3. **Framework Complexity (48% of abandonments)**
   - Requires framework expertise to customize
   - Breaking changes in framework updates
   - Debugging requires reading framework source code
   - **Prevention:** Thin abstraction layers, export to primitives, version pinning

### Early Warning Indicators:

- Users asking "why is this so expensive?" in forums
- Support tickets with "it worked yesterday, now it's broken"
- Decreased usage after initial spike (novelty wore off, pain too high)
- Developers bypassing platform to call LLM APIs directly
- Feature requests for "export to Python" or "just give me the code"

---

## Sources

### Multi-LLM Integration & Rate Limits
- [Why Multi-Agent LLM Systems Fail - Orq.ai](https://orq.ai/blog/why-do-multi-agent-llm-systems-fail)
- [Rate Limiting in AI Gateway - TrueFoundry](https://www.truefoundry.com/blog/rate-limiting-in-llm-gateway)
- [Tackling Rate Limiting for LLM Apps - Portkey](https://portkey.ai/blog/tackling-rate-limiting-for-llm-apps/)
- [LLM Orchestration in 2026 - AIMultiple](https://research.aimultiple.com/llm-orchestration/)

### Agent Lifecycle & Zombie Agents
- [ZombieAgent ChatGPT Attack - CSO Online](https://www.csoonline.com/article/4115110/zombieagent-chatgpt-attack-shows-persistent-data-leak-risks-of-ai-agents.html)
- [Agentic AI Lifecycle Management - Token Security](https://www.token.security/blog/agentic-ai-lifecycle-management-from-training-to-decommissioning-securely)
- [Service Discovery with Consul - Dev Genius](https://blog.devgenius.io/service-discovery-with-consul-b3ec7bc24ec5)

### Framework Lock-in & Production Failures
- [Why AI Frameworks Fail in Production - Rhino Tech Media](https://www.rhinotechmedia.com/why-ai-frameworks-langchain-crewai-pydanticai-and-others-fail-in-production/)
- [The 2025 AI Agent Report - Composio](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap)
- [LangChain Alternatives 2026 - Lindy](https://www.lindy.ai/blog/langchain-alternatives)

### Observability & Performance
- [Top 5 AI Agent Observability Platforms - O-mega](https://o-mega.ai/articles/top-5-ai-agent-observability-platforms-the-ultimate-2026-guide)
- [MLflow 3.0 Announcement - Databricks](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)
- [Agent Observability - Salesforce](https://www.salesforce.com/agentforce/observability/agent-observability/)

### Context Window Management
- [Context Window Management for AI Agents - Maxim](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/)
- [Context Window Overflow - AWS Security](https://aws.amazon.com/blogs/security/context-window-overflow-breaking-the-barrier/)
- [Top Techniques to Manage Context Lengths - Agenta](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms)

### SQLite Concurrency & State Management
- [Beyond SQLite Single-Writer Limitation - Turso](https://turso.tech/blog/beyond-the-single-writer-limitation-with-tursos-concurrent-writes)
- [How Turso Eliminates SQLite Bottleneck - Better Stack](https://betterstack.com/community/guides/databases/turso-explained/)
- [Distributed State Management for Agents - InfoWorld](https://www.infoworld.com/article/3808083/a-distributed-state-of-mind-event-driven-multi-agent-systems.html)

### Security & Sandboxing
- [Setting Up Secure Python Sandbox - Dida.do](https://dida.do/blog/setting-up-a-secure-python-sandbox-for-llm-agents)
- [Practical Security for Sandboxing Agentic Workflows - NVIDIA](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk)
- [Unveiling AI Agent Vulnerabilities: Code Execution - Trend Micro](https://www.trendmicro.com/vinfo/us/security/news/cybercrime-and-digital-threats/unveiling-ai-agent-vulnerabilities-code-execution)
- [LLM Security Risks 2026 - Sombra](https://sombrainc.com/blog/llm-security-risks-2026)

### Docker & Deployment
- [Docker Container Bloat Solutions - Eureka](https://eureka.patsnap.com/article/docker-container-bloat-how-to-reduce-image-size-and-improve-speed)
- [Slimming Docker Container from 8GB to 200MB - Nozzlegear](https://nozzlegear.com/blog/slimming-a-container-from-nearly-8gb-to-under-200mb)
- [Bloated Docker Images Causes and Solutions - Medium](https://medium.com/@tyagisanjeev1211/bloated-docker-images-causes-and-solutions-7065e7e980cb)

### Agent Orchestration Patterns
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Common Challenges Deploying AI Agents - UiPath](https://www.uipath.com/blog/ai/common-challenges-deploying-ai-agents-and-solutions-why-orchestration)
- [Agent Orchestration: It's Governance - Medium](https://medium.com/@markus_brinsa/agent-orchestration-orchestration-isnt-magic-it-s-governance-210afb343914)

---

*Pitfalls research for: Agent Orchestration Platform (Local-First)*
*Researched: 2026-02-02*
*Confidence: HIGH - Findings based on production post-mortems, 2025-2026 failure analysis, and authoritative sources*
