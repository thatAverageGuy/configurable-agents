---
phase: quick-005
plan: 005
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/process/manager.py
  - src/configurable_agents/cli.py
autonomous: true

must_haves:
  truths:
    - "Child process exceptions are printed with full traceback"
    - "Process exit codes are logged when detected"
    - "Service startup/shutdown is visible in console output"
  artifacts:
    - path: "src/configurable_agents/process/manager.py"
      contains: "traceback.print_exc"
    - path: "src/configurable_agents/cli.py"
      contains: "print.*Starting"
  key_links:
    - from: "_run_service_wrapper"
      to: "stderr"
      via: "traceback.print_exc() on exception"
      pattern: "traceback\\.print_exc"
---

<objective>
Add comprehensive debug logging to diagnose silent process exit failures.

Purpose: The services (Dashboard and Chat UI) exit immediately after starting instead of staying running. This diagnostic logging will make visible any exceptions being swallowed in child processes.

Output: Enhanced logging at critical points in the process lifecycle
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@src/configurable_agents/process/manager.py
@src/configurable_agents/cli.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add debug logging to process wrapper</name>
  <files>src/configurable_agents/process/manager.py</files>
  <action>
    Modify the `_run_service_wrapper` function to add comprehensive logging:

    1. Before calling target_func (line 46), add:
       ```python
       print(f"[{service_name}] Starting service target...", flush=True)
       ```

    2. After the try/except block, change the exception handling (lines 51-54) to:
       ```python
       import traceback
       print(f"[{service_name}] ERROR: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
       print(f"[{service_name}] TRACEBACK:", file=sys.stderr, flush=True)
       traceback.print_exc(file=sys.stderr)
       sys.exit(1)
       ```

    3. In the wait() method around line 206, add logging when process exits:
       ```python
       if not process.is_alive():
           exit_code = process.exitcode
           print(f"[ProcessManager] {name} exited (code: {exit_code})", flush=True)
       ```
    Do NOT change any logic, only add print statements with flush=True.
  </action>
  <verify>grep -n "print.*flush=True" src/configurable_agents/process/manager.py shows new logging statements</verify>
  <done>All process lifecycle events (start, error, exit) are logged to console</done>
</task>

<task type="auto">
  <name>Task 2: Add debug logging to service wrappers</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
    Add entry logging to both `_run_dashboard_with_config` and `_run_chat_with_config`:

    1. In `_run_dashboard_with_config` (line 1469), at the start of the function before calling `_run_dashboard_service`, add:
       ```python
       print(f"[Dashboard] Starting with config: host={config['host']}, port={config['port']}", flush=True)
       ```

    2. In `_run_chat_with_config` (line 1489), at the start of the function before calling `_run_chat_service`, add:
       ```python
       print(f"[ChatUI] Starting with config: host={config['host']}, port={config['port']}", flush=True)
       ```

    3. Wrap both `_run_dashboard_service` and `_run_chat_service` calls in try/except with traceback:
       ```python
       try:
           _run_dashboard_service(...)
       except Exception as e:
           import traceback
           print(f"[Dashboard] CRASH: {e}", file=sys.stderr, flush=True)
           traceback.print_exc(file=sys.stderr)
           raise
       ```
       (Do the same for _run_chat_service in _run_chat_with_config)

    Do NOT change any logic, only add print statements with flush=True.
  </action>
  <verify>grep -n "Starting with config" src/configurable_agents/cli.py shows both dashboard and chat logging</verify>
  <done>Service startup is visible in console, exceptions show full traceback</done>
</task>

</tasks>

<verification>
1. Run `configurable-agents ui` command
2. Observe console output for:
   - "Starting with config" messages from both services
   - Any "CRASH" or "ERROR" messages with tracebacks
   - Exit codes if processes terminate
3. The output should reveal WHY services are exiting
</verification>

<success_criteria>
- Running `configurable-agents ui` shows detailed startup logging
- Any exceptions in child processes display full traceback
- Exit reasons (exit codes, errors) are visible in console
- No changes to control flow - logging only
</success_criteria>

<output>
After completion, create `.planning/quick/005-add-process-debug-logging/005-SUMMARY.md`
</output>
