---
phase: quick
plan: 002
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/cli.py
autonomous: true

must_haves:
  truths:
    - "Windows multiprocessing starts without pickle errors"
    - "Dashboard and Chat UI launch successfully via cmd_ui"
    - "No AttributeError about local lambda objects"
  artifacts:
    - path: "src/configurable_agents/cli.py"
      provides: "cmd_ui with pickleable service targets"
      contains: "from functools import partial"
  key_links:
    - from: "cli.py"
      to: "process.manager.ProcessManager"
      via: "ServiceSpec with partial target"
      pattern: "ServiceSpec.*target=partial"
---

<objective>
Fix Windows multiprocessing pickle issue by replacing lambdas with functools.partial.

Purpose: Lambda functions defined inside cmd_ui close over args and cannot be pickled
using Windows' spawn method. functools.partial is pickleable and works correctly.

Output: Working cmd_ui command on Windows without AttributeError
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/quick/002-fix-lambda-pickle-issue

# Current issue in cli.py (lines 1573-1605):
```python
manager.add_service(ServiceSpec(
    name="dashboard",
    target=lambda: _run_dashboard_service(  # <- Not pickleable
        args.host,
        args.dashboard_port,
        args.db_url,
        args.mlflow_uri,
        args.verbose,
    ),
))

manager.add_service(ServiceSpec(
    name="chat",
    target=lambda: _run_chat_service(  # <- Not pickleable
        args.host,
        args.chat_port,
        args.host,
        args.dashboard_port,
        args.verbose,
    ),
))
```

# Solution: Use functools.partial
```python
from functools import partial

manager.add_service(ServiceSpec(
    name="dashboard",
    target=partial(_run_dashboard_service, args.host, args.dashboard_port, args.db_url, args.mlflow_uri, args.verbose),
))

manager.add_service(ServiceSpec(
    name="chat",
    target=partial(_run_chat_service, args.host, args.chat_port, args.host, args.dashboard_port, args.verbose),
))
```

functools.partial objects are pickleable and will work with spawn method.
</context>

<tasks>

<task type="auto">
  <name>Replace lambda with functools.partial for service targets</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
    In src/configurable_agents/cli.py:

    1. Add import at top of file (with other imports):
       ```python
       from functools import partial
       ```

    2. Replace the dashboard ServiceSpec (lines ~1573-1582):
       FROM:
       ```python
       manager.add_service(ServiceSpec(
           name="dashboard",
           target=lambda: _run_dashboard_service(
               args.host,
               args.dashboard_port,
               args.db_url,
               args.mlflow_uri,
               args.verbose,
           ),
       ))
       ```
       TO:
       ```python
       manager.add_service(ServiceSpec(
           name="dashboard",
           target=partial(_run_dashboard_service, args.host, args.dashboard_port, args.db_url, args.mlflow_uri, args.verbose),
       ))
       ```

    3. Replace the chat ServiceSpec (lines ~1596-1605):
       FROM:
       ```python
       manager.add_service(ServiceSpec(
           name="chat",
           target=lambda: _run_chat_service(
               args.host,
               args.chat_port,
               args.host,
               args.dashboard_port,
               args.verbose,
           ),
       ))
       ```
       TO:
       ```python
       manager.add_service(ServiceSpec(
           name="chat",
           target=partial(_run_chat_service, args.host, args.chat_port, args.host, args.dashboard_port, args.verbose),
       ))
       ```

    4. Remove the incorrect comment about lambda being pickleable (lines ~1565-1567) if it exists.
  </action>
  <verify>
    Run: python -c "from configurable_agents.cli import cmd_ui; import sys; sys.exit(0)"
    Or verify import works without error.
  </verify>
  <done>
    - functools.partial imported
    - Both ServiceSpec calls use partial instead of lambda
    - Code imports without pickle errors
  </done>
</task>

</tasks>

<verification>
Test the fix on Windows:
```bash
python -m configurable_agents ui
```

Should start without "AttributeError: Can't get local object" error.
</verification>

<success_criteria>
- cmd_ui command starts successfully on Windows
- No AttributeError about lambda objects when spawning processes
- Dashboard and Chat UI services launch in separate processes
</success_criteria>

<output>
After completion, create `.planning/quick/002-fix-lambda-pickle-issue/002-SUMMARY.md`
</output>
