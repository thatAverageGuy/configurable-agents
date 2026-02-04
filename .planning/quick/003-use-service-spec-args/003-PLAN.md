---
phase: quick
plan: 003
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
    - "No TypeError about weakref.ReferenceType pickle failures"
  artifacts:
    - path: "src/configurable_agents/cli.py"
      provides: "cmd_ui with pickleable service targets using args"
      contains: "ServiceSpec.*args=\\("
  key_links:
    - from: "cli.py"
      to: "process.manager.ProcessManager"
      via: "ServiceSpec with simple module-level target and args tuple"
      pattern: "ServiceSpec.*args=\\("
---

<objective>
Fix Windows multiprocessing pickle issue by using ServiceSpec args instead of functools.partial.

Purpose: functools.partial contains weakrefs that cannot be pickled. The solution is to
use ServiceSpec's built-in args field to pass configuration as a simple dict/tuple.

Output: Working cmd_ui command on Windows without TypeError about weakref.ReferenceType
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/quick/003-use-service-spec-args
@src/configurable_agents/cli.py
@src/configurable_agents/process/manager.py

# Root Cause Analysis
The error `TypeError: cannot pickle 'weakref.ReferenceType' object` occurs because:

1. ProcessManager creates Process with `target=self._run_service, args=(service,)` (manager.py:98)
2. The ServiceSpec contains a `functools.partial` object in the `target` field
3. When multiprocessing pickles the Process, it pickles the entire ServiceSpec with the partial inside
4. `functools.partial` objects contain weakrefs that cannot be pickled on Windows

# Current Broken Implementation (cli.py lines 1571-1591)
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

# Solution: Use ServiceSpec args field
ServiceSpec already has `args` and `kwargs` fields. We should:
1. Create new module-level wrapper functions that take a config dict
2. Pass configuration via ServiceSpec.args tuple
3. The wrapper function unpacks args and calls the actual service function

```python
# Module-level wrapper (takes a config dict/tuple)
def _run_dashboard_with_config(config: dict) -> None:
    """Run dashboard with configuration dict - module level for pickle compatibility."""
    _run_dashboard_service(
        host=config['host'],
        port=config['port'],
        db_url=config['db_url'],
        mlflow_uri=config['mlflow_uri'],
        verbose=config['verbose'],
    )

# In cmd_ui:
config = {
    'host': args.host,
    'port': args.dashboard_port,
    'db_url': args.db_url,
    'mlflow_uri': args.mlflow_uri,
    'verbose': args.verbose,
}
manager.add_service(ServiceSpec(
    name="dashboard",
    target=_run_dashboard_with_config,
    args=(config,),
))
```

This way:
- ServiceSpec.target is a simple module-level function (pickleable)
- ServiceSpec.args is a simple dict (pickleable)
- No functools.partial needed
- No weakrefs involved
</context>

<tasks>

<task type="auto">
  <name>Replace functools.partial with ServiceSpec.args for service configuration</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
    In src/configurable_agents/cli.py:

    1. Remove the `from functools import partial` import (line ~17)

    2. Add two new module-level wrapper functions BEFORE the existing `_run_dashboard_service` function (around line 1468):

       ```python
       def _run_dashboard_with_config(config: dict) -> None:
           """Run dashboard with configuration dict - module level for pickle compatibility.

           On Windows, multiprocessing uses the 'spawn' method which requires
           functions passed to Process() to be pickleable. functools.partial
           contains weakrefs that cannot be pickled, so we use a simple
           module-level function that unpacks a config dict.

           Args:
               config: Dict with keys: host, port, db_url, mlflow_uri, verbose
           """
           _run_dashboard_service(
               host=config['host'],
               port=config['port'],
               db_url=config['db_url'],
               mlflow_uri=config['mlflow_uri'],
               verbose=config['verbose'],
           )


       def _run_chat_with_config(config: dict) -> None:
           """Run chat UI with configuration dict - module level for pickle compatibility.

           On Windows, multiprocessing uses the 'spawn' method which requires
           functions passed to Process() to be pickleable. functools.partial
           contains weakrefs that cannot be pickled, so we use a simple
           module-level function that unpacks a config dict.

           Args:
               config: Dict with keys: host, port, dashboard_host, dashboard_port, verbose
           """
           _run_chat_service(
               host=config['host'],
               port=config['port'],
               dashboard_host=config['dashboard_host'],
               dashboard_port=config['dashboard_port'],
               verbose=config['verbose'],
           )
       ```

    3. Replace the dashboard ServiceSpec (lines ~1571-1574):
       FROM:
       ```python
       manager.add_service(ServiceSpec(
           name="dashboard",
           target=partial(_run_dashboard_service, args.host, args.dashboard_port, args.db_url, args.mlflow_uri, args.verbose),
       ))
       ```
       TO:
       ```python
       dashboard_config = {
           'host': args.host,
           'port': args.dashboard_port,
           'db_url': args.db_url,
           'mlflow_uri': args.mlflow_uri,
           'verbose': args.verbose,
       }
       manager.add_service(ServiceSpec(
           name="dashboard",
           target=_run_dashboard_with_config,
           args=(dashboard_config,),
       ))
       ```

    4. Replace the chat ServiceSpec (lines ~1588-1591):
       FROM:
       ```python
       manager.add_service(ServiceSpec(
           name="chat",
           target=partial(_run_chat_service, args.host, args.chat_port, args.host, args.dashboard_port, args.verbose),
       ))
       ```
       TO:
       ```python
       chat_config = {
           'host': args.host,
           'port': args.chat_port,
           'dashboard_host': args.host,
           'dashboard_port': args.dashboard_port,
           'verbose': args.verbose,
       }
       manager.add_service(ServiceSpec(
           name="chat",
           target=_run_chat_with_config,
           args=(chat_config,),
       ))
       ```

    5. Update the docstring for `_run_dashboard_service` (line ~1472) to clarify it's called by the wrapper:
       Change:
       "Run dashboard server - module level for pickle compatibility on Windows."
       To:
       "Run dashboard server - module level for pickle compatibility on Windows.

       Called by _run_dashboard_with_config wrapper which handles config unpacking."

    6. Update the docstring for `_run_chat_service` similarly.
  </action>
  <verify>
    Run: python -c "from configurable_agents.cli import cmd_ui; import sys; sys.exit(0)"
    Or verify import works without error.
  </verify>
  <done>
    - functools.partial import removed
    - Two new wrapper functions added (_run_dashboard_with_config, _run_chat_with_config)
    - Both ServiceSpec calls use simple module-level targets with args=(config,)
    - Code imports without pickle errors
  </done>
</task>

</tasks>

<verification>
Test the fix on Windows:
```bash
python -m configurable_agents ui
```

Should start without "TypeError: cannot pickle 'weakref.ReferenceType' object" error.
</verification>

<success_criteria>
- cmd_ui command starts successfully on Windows
- No TypeError about weakref.ReferenceType when spawning processes
- Dashboard and Chat UI services launch in separate processes
- functools.partial no longer used for service targets
</success_criteria>

<output>
After completion, create `.planning/quick/003-use-service-spec-args/003-SUMMARY.md`
</output>
