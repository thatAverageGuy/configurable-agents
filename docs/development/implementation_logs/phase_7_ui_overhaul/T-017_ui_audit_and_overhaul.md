# T-017: UI Audit and Overhaul

**Phase**: 7 — UI Overhaul
**Status**: IN_PROGRESS
**Started**: 2026-03-26
**Priority**: HIGH

---

## Objective

Full audit and overhaul of all user-facing UI surfaces. Goal: every UI component works exactly as intended, is free of bugs, and is worth using. Remove dead surfaces. Fix broken functionality. Redesign where needed.

---

## Audit Findings (2026-03-26)

### Surfaces Inventoried

| Surface | Tech | Port | Verdict |
|---------|------|------|---------|
| Chat UI | Gradio | 7860 | Fix + redesign |
| Orchestration Dashboard | FastAPI + HTMX | 7861 | Fix + redesign |
| Webhook Server | FastAPI | 7862 | Fix (one bug) |
| Deployment Registry | FastAPI | 9000 | OK |
| Combined Launcher (`ui` cmd) | ProcessManager | — | OK |
| Streamlit | Streamlit | 8501 | Dead — remove |

---

## Issues Found

### Chat UI (Gradio) — `src/configurable_agents/ui/gradio_chat.py`

#### C1 — CRITICAL: Download YAML button is broken
`gr.File()` is created inline inside `.click(outputs=gr.File())` but is not defined in the `with gr.Blocks()` layout. Gradio requires all output components to be declared in the layout block. The Download button does nothing.

**Fix**: Declare `file_output = gr.File(visible=False, label="Download")` inside the `gr.Blocks()` layout and wire the button to it.

#### C2 — HIGH: Streaming is fake
`collect_response()` fully collects the LLM response before yielding. Then the method manually chunks it into 50-char pieces. The user waits the full LLM duration, then sees fast local replay. Real streaming (token-by-token as the LLM produces) never happens.

**Fix**: Yield each token chunk from `stream_chat` directly as it arrives using a proper async generator loop.

#### C3 — HIGH: System prompt is stale
The `CONFIG_GENERATION_PROMPT` describes `optimization` (a removed feature) and is silent on all v1.x additions: `memory`, `tools`, `reducer`, loop counter state injection (`__loop_counter_*`), `runtime_overrides`, `extract_facts`, parallel (fork-join) edges, and the `--memory-scope` flag. The Chat UI will generate configs with dead fields and miss real capabilities.

**Fix**: Rewrite `CONFIG_GENERATION_PROMPT` to reflect the current schema accurately, including what IS supported and explicitly what is NOT.

#### C4 — MEDIUM: Session ID is IP-based
Session ID is derived from `{client_ip}:{client_port}`. Two browser tabs from the same machine share a session. No proper per-browser or per-tab isolation.

**Fix**: Use a browser-side `gr.State()` UUID instead of IP-based derivation. Alternatively, generate a random UUID per session on first load.

#### C5 — LOW: `asyncio.get_event_loop()` deprecated
`asyncio.get_event_loop()` is deprecated in Python 3.10+. May emit DeprecationWarning.

**Fix**: Always use `asyncio.new_event_loop()` + `asyncio.set_event_loop()`, or restructure the async call.

#### C6 — LOW: CSS defined twice, once unused
`custom_css` is defined as a local variable inside `create_interface()` but never passed to `gr.Blocks(css=...)`. The same CSS is then defined again inside `launch()` and passed there. Dead code.

**Fix**: Remove the duplicate from `create_interface()`.

---

### Orchestration Dashboard — `src/configurable_agents/ui/dashboard/`

#### D1 — CRITICAL: "Deregister" button breaks the dashboard page
In `deployments_table.html`, the Deregister button uses:
```html
hx-delete="/deployments/{id}"
hx-swap="outerHTML"
hx-target="#deployments-table"
```
But `DELETE /deployments/{id}` returns JSON `{"status": "deregistered", ...}`, not HTML. After clicking, the entire table area is replaced with raw JSON text. The page is broken until reload.

**Fix**: After DELETE, trigger a fresh GET of the table partial via HTMX, or return an HTML partial from the delete endpoint.

#### D2 — HIGH: "Deployment ID" column in executions table shows wrong data
In `executions_table.html`:
```jinja
{% if workflow.workflow_name and '-' in workflow.workflow_name or workflow.workflow_name.endswith('-agent') %}
    <code>{{ workflow.workflow_name }}</code>
{% else %}
    -
{% endif %}
```
This uses `workflow_name` as a proxy for deployment ID based on a heuristic (`-` in name). Should use `workflow.deployment_id` directly.

**Fix**: Replace with `{{ workflow.deployment_id or '-' }}`.

#### D3 — HIGH: No deployment registration form in the dashboard UI
`POST /deployments/register` is fully implemented and works, but there is no HTML form on the deployments page to call it. Users cannot register a deployment through the dashboard.

**Fix**: Add a registration form to `deployments.html` (collapsible section or modal) with fields for deployment_id, deployment_name, deployment_url, workflow_name.

#### D4 — MEDIUM: SSE connections are dead code in the frontend
Both `executions.html` and `deployments.html` set up SSE connections:
```html
<div hx-ext="sse" sse-connect="/metrics/executions/stream" sse-swap="execution_update" style="display: none;">
```
The `sse-swap` targets a named event but there is no element in the page with a matching `sse-swap` target that accepts the JSON payload correctly. The SSE messages arrive and dump raw JSON into the hidden div. The actual refresh mechanism is HTMX polling (`every 5s`/`every 10s`), which works correctly. SSE is noise that adds open connections with no benefit.

**Fix**: Remove the SSE `<div>` and the associated `<script>` event listeners from both pages. Keep the HTMX polling.

#### D5 — LOW: Cancel button does not trigger table refresh
The cancel button uses `hx-swap="none"`, so after cancellation the table row stays showing "running" until the next auto-poll (up to 5s).

**Fix**: Change to `hx-swap="outerHTML"` targeting the table div, or trigger a table refresh after cancel.

#### D6 — LOW: No "Restart" button exposed in executions table
`POST /executions/{id}/restart` is fully implemented but no button in `executions_table.html` exposes it. The detail page also has no restart button.

**Fix**: Add a Restart button to the executions table actions for failed/cancelled executions.

#### D7 — LOW: System Resources card silently shows 0% when psutil is absent
The status panel shows `CPU 0% | RAM 0%` with no indication that this is because `psutil` is not installed vs. genuinely 0%.

**Fix**: If `psutil` is unavailable, show `N/A` or `(psutil not installed)` instead of misleading `0%`.

---

### Webhook Server — `src/configurable_agents/webhooks/router.py`

#### W1 — HIGH: `WebhookError` referenced but never imported
Line 493:
```python
except WebhookError as e:
```
`WebhookError` is not imported anywhere in `router.py`. This `except` clause will raise a `NameError` at runtime if that code path is hit, masking the original exception.

**Fix**: Import `WebhookError` from `configurable_agents.webhooks.base`, or replace with `except Exception`.

---

### Streamlit (`streamlit_app.py` at repo root)

#### S1 — Remove
Not integrated into any command or workflow. Uses old terminology. Not maintained. Confirmed by user as reference-only dead code.

**Action**: Delete `streamlit_app.py`.

---

## Overhaul Plan — Ordered by Surface

Work proceeds surface-by-surface, fully completing one before moving to the next.

### Phase 1: Chat UI (Current Focus)
1. Fix C1 — Download button
2. Fix C2 — Real streaming
3. Fix C3 — Rewrite system prompt (most impactful)
4. Fix C4 — Session ID
5. Fix C5 — asyncio deprecation
6. Fix C6 — Dead CSS
7. Review overall Gradio layout and UX — redesign if needed

### Phase 2: Orchestration Dashboard
1. Fix D1 — Deregister button (critical)
2. Fix D2 — Deployment ID column
3. Fix D3 — Add registration form
4. Fix D4 — Remove dead SSE code
5. Fix D5 — Cancel refresh
6. Fix D6 — Add Restart button
7. Fix D7 — psutil N/A display
8. Review overall dashboard UX — redesign if needed

### Phase 3: Webhook Server
1. Fix W1 — WebhookError import

### Phase 4: Cleanup
1. Delete `streamlit_app.py`

---

## Phase 1 Results: Chat UI (2026-03-26)

### What Was Done

Full rewrite of `src/configurable_agents/ui/gradio_chat.py` (~1230 lines).

**All 6 Chat UI issues resolved:**

| Issue | Status | How |
|-------|--------|-----|
| C1 — Download broken | ✅ Fixed | `file_output = gr.File(visible=False)` declared in layout; wired via `.change()` to show when path returned |
| C2 — Fake streaming | ✅ Fixed | `respond()` rewritten as true async generator; `async for chunk in stream_chat(...)` yields each token as it arrives |
| C3 — Stale system prompt | ✅ Fixed | Complete `CONFIG_GENERATION_PROMPT` rewrite covering full v1.0 schema, all tools, all providers, what IS and IS NOT supported |
| C4 — IP-based session ID | ✅ Fixed | `gr.State(self._new_session_id())` — UUID per page load; `create_session("local")` returns actual session UUID |
| C5 — asyncio deprecation | ✅ Fixed | Old `get_event_loop()` + `run_until_complete()` pattern replaced entirely by async generator approach |
| C6 — Duplicate CSS | ✅ Fixed | Dead `custom_css` variable removed; CSS lives only in `gr.Blocks(css=...)` |

**New design features added (per user spec):**

- **3-column layout**: Session history sidebar (scale=1) | Chat area (scale=3) | Config Preview panel (scale=2)
- **LLM config bar**: Provider dropdown, API key (password input), model dropdown, Apply button, status label — all above the chat
- **Dashboard button**: `gr.Button(link=dashboard_url)` in the header row (top-right), not sidebar footer
- **Config Preview panel**: `gr.Code(language="yaml")` with Validate, Download YAML, ▶ Run Ephemeral, 🚀 Deploy buttons
- **Run Ephemeral dialog**: `gr.Group(visible=False)` shown on demand; pre-populated with detected required ENV vars (from providers + tools) and workflow input fields (required=true, no default from `state.fields`); inputs as editable JSON; executes via `asyncio.to_thread(run_workflow, ...)`
- **Deploy dialog**: container name (auto-derived from `flow.name`), API port, ENV values textarea; generates artifacts → checks Docker → builds image → runs container; graceful fallback with manual instructions if Docker unavailable
- **Session sidebar**: New Chat button, recent sessions dropdown; loading a session restores chatbot history and config preview
- **`PROVIDER_CATALOGUE`**: OpenAI / Anthropic / Google / Ollama with env_var, model list, default model
- **`TOOL_ENV_VARS`**: Maps tool names to required env vars for auto-detection

**Bug found and fixed during implementation review:**
- `_new_session_id()` was passing UUID as `user_identifier` then discarding the returned `session_id`. Fixed to pass `"local"` as `user_identifier` and return the actual `session_id` from `create_session()`.
- `_load_session_config()` was looking for `config_yaml` key; actual model field is `generated_config`. Fixed.

### Testing Status

- Syntax check: ✅ `python -c "import ast; ast.parse(...)"` — no errors
- Core imports: ✅ `WorkflowConfig`, `create_llm`, `stream_chat`, `ChatSessionRepository` all resolve
- Manual run: ⏳ Pending (requires API key and running dependencies)

---

## Success Criteria

- Chat UI: User can describe a workflow, get a correct config, download it, and the session persists correctly
- Dashboard: All buttons work. Deployments can be registered, deregistered, and monitored. Executions can be cancelled and restarted. All data displays correctly.
- Webhook server: No NameErrors on any code path
- Streamlit: Deleted

---

## Testing Strategy

- Chat UI: Manual — describe a workflow, observe streaming, download YAML, validate it
- Dashboard: Manual — register a deployment, view health, deregister (verify page stays intact), cancel an execution, restart one
- Webhook: Unit test — trigger the `except WebhookError` code path via a mock

---

## References

- Audit session: 2026-03-26 (this document)
- Relevant source files:
  - `src/configurable_agents/ui/gradio_chat.py`
  - `src/configurable_agents/ui/dashboard/app.py`
  - `src/configurable_agents/ui/dashboard/routes/executions.py`
  - `src/configurable_agents/ui/dashboard/routes/deployments.py`
  - `src/configurable_agents/ui/dashboard/routes/metrics.py`
  - `src/configurable_agents/ui/dashboard/routes/status.py`
  - `src/configurable_agents/ui/dashboard/templates/`
  - `src/configurable_agents/webhooks/router.py`
  - `streamlit_app.py`
