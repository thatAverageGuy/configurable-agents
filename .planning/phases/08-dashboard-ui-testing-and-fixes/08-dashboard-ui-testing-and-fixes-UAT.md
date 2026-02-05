---
status: testing
phase: 08-dashboard-ui-testing-and-fixes
source: 08-01-SUMMARY.md, 08-02-SUMMARY.md, 08-03-SUMMARY.md, 08-04-SUMMARY.md, 08-05-SUMMARY.md, 08-06-SUMMARY.md
started: 2026-02-05T14:30:00Z
updated: 2026-02-05T14:32:00Z
---

## Current Test

UAT complete

## Tests

### 1. Dashboard Home Page Loads
expected: Start the dashboard with `configurable-agents ui --dashboard-port-only 7861` (or just `configurable-agents ui` for all services). Visit http://localhost:7861/ in your browser. You should see the main dashboard page loads without errors, status panel showing workflow/agent counts, navigation sidebar with links to Workflows/Agents/Experiments/Optimization, and no error messages in browser console or terminal.
result: pass

### 2. Workflows Page Loads and Displays
expected: Start the dashboard with `configurable-agents ui --dashboard-port-only 7861` (or just `configurable-agents ui` for all services). Visit http://localhost:7861/workflows. The page should load without TemplateNotFound errors. You should see a table displaying workflow runs (or "No workflows found" if empty). Status badges should be colored (running=blue, completed=green, failed=red, etc.). Durations should be formatted as "Xm Ys" or "< 1s". Costs should be formatted as "$X.XXXX".
result: pass

### 3. Agents Page Loads and Displays
expected: Click the "Agents" link in the navigation sidebar (or visit http://localhost:7861/agents). The page should load without TemplateAssertionError about underscore imports. You should see a table displaying registered agents (or "No agents found" if empty). Agent last heartbeat times should be formatted as "just now", "Xm ago", "Xh ago", or "Xd ago". Capabilities should be parsed and displayed as tags or list items.
result: pass

### 4. MLFlow Link Shows Friendly Unavailable Page
expected: Without MLFlow enabled, click the "MLFlow" link in the navigation (or visit http://localhost:7861/mlflow). You should see a friendly HTML page (not JSON 404) with the heading "MLFlow Not Configured". The page should include clear instructions: install MLFlow with `pip install mlflow`, start dashboard with `--mlflow` flag, or use `--mlflow-uri` for external MLFlow server. No crash or generic error page.
result: issue - User feedback: "couldn't see any --mlflow flag"

### 5. Optimization Page Shows Graceful MLFlow Message
expected: Click the "Optimization" link in the navigation (or visit http://localhost:7861/optimization/experiments). Without MLFlow configured, you should see a friendly warning message box with "MLFlow Not Available" heading. The message should explain that optimization features require MLFlow and provide installation/configuration instructions. The page should load without filesystem errors (no WinError 2 or "cannot find file" errors).
result: pass

### 6. HTMX Table Refresh Works (Workflows)
expected: On the Workflows page, the table should refresh dynamically. If you have workflow data, you can click status filter buttons (if present) or the page should auto-refresh. The table partial should load via HTMX without full page reload. Look for network activity in browser dev tools - requests to `/workflows/table` returning HTML partials.
result: issue - User feedback: "htmx:targetError" in console when updating status filter

### 7. HTMX Table Refresh Works (Agents)
expected: On the Agents page, the table should refresh dynamically via HTMX. Look for requests to `/agents/table` returning HTML partials. If you have agent data, the table should update without full page reload.
result: issue - User feedback: "Refresh button on agents page has same error as the workflows: htmx:targetError"

### 8. Empty States Display Correctly
expected: With no workflow or agent data, the Workflows and Agents pages should show "No workflows found" or "No agents found" empty states (not crash or show errors). These empty states are helpful - they suggest running a workflow or registering an agent.
result: pass - User feedback: "I think we call it a pass as there are no crashes and it is ok. However, I noticed one thing, there's this [] empty array type thing at the bottom left of the tables on both workflows and agents page."

### 9. Status Badge Colors Render Correctly
expected: On the Workflows page, status badges should have appropriate CSS classes and colors. Running workflows should look distinct from completed/failed ones. The badges should be visually distinct with proper background colors.
result: skipped - No workflow data available to test badge rendering

### 10. Time Formatting is Readable
expected: On the Agents page, last heartbeat times should be human-readable: "just now" for recent activity, "5m ago" for 5 minutes ago, "2h ago" for 2 hours ago, "3d ago" for 3 days ago. No raw timestamps or ISO dates visible to users.
result: skipped - No agent data available to test time formatting

## Summary

total: 10
passed: 5
issues_fixed: 4
notes_fixed: 1
doc_issues: 1
pending: 0
skipped: 2

## Gaps

### Issue 001: MLFlow auto-start feature missing (test 4) ✅ FIXED
- **User feedback:** "couldn't see any --mlflow flag"
- **User requirement:** `configurable-agents ui` should auto-start everything including MLFlow UI by default
- **Implementation completed:**
  1. ✅ Added `--mlflow-port <port>` flag (default: 5000)
  2. ✅ Auto-start MLFlow UI when MLFlow is installed
  3. ✅ Graceful degradation with terminal message if MLFlow not installed
  4. ✅ Flag precedence: `--mlflow-uri` overrides `--mlflow-port`
  5. ✅ Added terminal messages for flag precedence
  6. ✅ Created `_run_mlflow_with_config()` and `_run_mlflow_service()` functions
- **Commit:** 88dffee

### Issue 002: --dashboard-port-only flag doesn't exist (UAT only)
- **User feedback:** "there is no such command as configurable-agents ui --dashboard-port-only 7861"
- **Root cause:** UAT test instructions use non-existent flag name
- **Actual flags:**
  - `--dashboard-port <port>` - set dashboard port (default: 7861)
  - `--chat-port <port>` - set chat port (default: 7860)
  - `--no-chat` - skip chat UI, start dashboard only
- **Severity:** documentation bug in UAT test (not in actual code)
- **Fix needed:** Update UAT test expected instructions to use `--dashboard-port` instead of `--dashboard-port-only`

### Issue 003: HTMX targetError on Workflows page (test 6) ✅ FIXED
- **User feedback:** "When I update the status, htmx:targetError logged into console"
- **Root cause:** Status filter had `hx-target="#workflows-table"` but no `hx-swap`, causing HTMX to use default `outerHTML` swap which couldn't find target element
- **Fix:** Added `hx-swap="innerHTML"` to status filter select element
- **Commit:** 88dffee

### Issue 004: HTMX targetError on Agents page (test 7) ✅ FIXED
- **User feedback:** "Refresh button on agents page has same error as the workflows: htmx:targetError"
- **Root cause:** Refresh button had `hx-swap="outerHTML"` which replaced entire div but response didn't include div with id="agents-table"
- **Fix:** Changed `hx-swap="outerHTML"` to `hx-swap="innerHTML"` on refresh button
- **Commit:** 88dffee

### Note 001: Empty array [] displayed at bottom of tables (test 8) ✅ FIXED
- **User feedback:** "I noticed one thing, there's this [] empty array type thing at the bottom left of the tables on both workflows and agents page"
- **Root cause:** SSE connection divs (for real-time updates) were visible on page
- **Fix:** Added `style="display: none;"` to SSE divs in both workflows.html and agents.html
- **Commit:** 88dffee
