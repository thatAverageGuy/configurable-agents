---
phase: quick
plan: 004
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/process/manager.py
autonomous: true

must_haves:
  truths:
    - "ProcessManager.start_all() no longer uses bound instance method as Process target"
    - "Windows multiprocessing starts without pickle errors"
    - "Service target execution works correctly with module-level wrapper"
  artifacts:
    - path: "src/configurable_agents/process/manager.py"
      provides: "ProcessManager with pickleable Process target"
      contains: "def _run_service_wrapper"
  key_links:
    - from: "ProcessManager.start_all()"
      to: "multiprocessing.Process"
      via: "Module-level _run_service_wrapper function"
      pattern: "Process\\(target=_run_service_wrapper"
    - from: "_run_service_wrapper"
      to: "service.target"
      via: "Direct call with unpacked args/kwargs"
      pattern: "service\\.target\\(\\*service\\.args"
---

<objective>
Fix Windows multiprocessing pickle issue by removing bound method from ProcessManager.

Purpose: The root cause of the pickle error is in manager.py line 99 where `target=self._run_service`
is a bound instance method of ProcessManager. When Windows' spawn method pickles the Process,
it must pickle the entire ProcessManager instance which contains unpickleable state
(signal handlers, database connections, etc.).

The solution: Use a module-level function instead of an instance method, passing only
primitive values (strings, tuples, bools) to the child process.

Output: ProcessManager works correctly on Windows without TypeError about weakref.ReferenceType
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/quick/004-fix-bound-method-pickle
@src/configurable_agents/process/manager.py

# Root Cause Analysis

The ACTUAL source of the pickle error is in manager.py at line 99:
```python
process = Process(
    target=self._run_service,  # <-- BOUND METHOD - CANNOT BE PICKLED
    args=(service,),
    ...
)
```

When Windows multiprocessing tries to pickle the Process object to send to the child process:
1. It pickles `self._run_service` (a bound method)
2. Bound methods include a reference to `self` (the ProcessManager instance)
3. ProcessManager contains unpickleable state:
   - Signal handlers (line 144: `signal.signal(signal.SIGINT, self._signal_handler)`)
   - Database connections/engines (via SQLAlchemy)
   - File handles and other objects with weakrefs

# Previous Attempts Were Incomplete

Attempts 001, 002, 003 fixed the SERVICE targets (what users pass to ServiceSpec),
but did NOT fix the ProcessManager's own use of a bound method for the Process target.

# The Correct Solution

Replace the bound method `self._run_service` with a module-level function:

```python
# MODULE LEVEL (at top of file, outside class)
def _run_service_wrapper(
    service_name: str,
    target_func: Callable,
    target_args: tuple,
    target_kwargs: dict,
    verbose: bool,
) -> None:
    """Wrapper to run a service target in child process - module level for pickle compatibility.

    On Windows, multiprocessing uses spawn method which requires all Process targets
    and their arguments to be pickleable. Instance methods (bound methods) cannot be
    pickled because they contain references to the entire instance.

    Args:
        service_name: Human-readable service name for logging
        target_func: The actual callable to invoke (must be module-level for pickle)
        target_args: Positional arguments to pass to target
        target_kwargs: Keyword arguments to pass to target
        verbose: Enable verbose logging
    """
    try:
        target_func(*target_args, **target_kwargs)
    except KeyboardInterrupt:
        if verbose:
            print(f"[ProcessManager] {service_name} received KeyboardInterrupt")
        sys.exit(0)
    except Exception as e:
        if verbose:
            print(f"[ProcessManager] {service_name} error: {e}", file=sys.stderr)
        sys.exit(1)
```

Then update ProcessManager.start_all() to pass primitive values:

```python
# In ProcessManager.start_all(), line ~98-103
for service in self._services:
    process = Process(
        target=_run_service_wrapper,  # MODULE-LEVEL FUNCTION (pickleable)
        args=(service.name, service.target, service.args, service.kwargs or {}, self._verbose),
        name=service.name,
        daemon=False,
    )
    ...
```

And REMOVE the _run_service() instance method (no longer needed).
</context>

<tasks>

<task type="auto">
  <name>Replace bound method with module-level wrapper function</name>
  <files>src/configurable_agents/process/manager.py</files>
  <action>
    In src/configurable_agents/process/manager.py:

    1. Add a new MODULE-LEVEL function after the imports (after line 20, before @dataclass):

       ```python
       def _run_service_wrapper(
           service_name: str,
           target_func: Callable,
           target_args: tuple,
           target_kwargs: dict,
           verbose: bool,
       ) -> None:
           """Wrapper to run a service target in child process - module level for pickle compatibility.

           On Windows, multiprocessing uses the 'spawn' method which requires all Process
           targets and their arguments to be pickleable. Instance methods (bound methods)
           cannot be pickled because they contain references to the entire instance.

           This function is defined at module level (not as a class method) specifically
           to avoid pickle issues on Windows.

           Args:
               service_name: Human-readable service name for logging
               target_func: The actual callable to invoke (must be module-level for pickle)
               target_args: Positional arguments to pass to target
               target_kwargs: Keyword arguments to pass to target
               verbose: Enable verbose logging
           """
           try:
               target_func(*target_args, **target_kwargs)
           except KeyboardInterrupt:
               if verbose:
                   print(f"[ProcessManager] {service_name} received KeyboardInterrupt")
               sys.exit(0)
           except Exception as e:
               if verbose:
                   print(f"[ProcessManager] {service_name} error: {e}", file=sys.stderr)
               sys.exit(1)
       ```

    2. Update ProcessManager.start_all() method (lines 97-103):
       FROM:
       ```python
       for service in self._services:
           process = Process(
               target=self._run_service,
               args=(service,),
               name=service.name,
               daemon=False,
           )
       ```
       TO:
       ```python
       for service in self._services:
           process = Process(
               target=_run_service_wrapper,
               args=(service.name, service.target, service.args, service.kwargs or {}, self._verbose),
               name=service.name,
               daemon=False,
           )
       ```

    3. DELETE the _run_service() instance method entirely (lines 113-133).
       This method is no longer needed since the module-level wrapper handles it.

       Delete this entire block:
       ```python
       def _run_service(self, service: ServiceSpec) -> None:
           \"\"\"Run a service target with error handling.

           This method runs in the child process. It wraps the service target
           to catch and log any exceptions before the process exits.

           Args:
               service: ServiceSpec describing the service to run
           \"\"\"
           try:
               service.target(*service.args, **(service.kwargs or {}))
           except KeyboardInterrupt:
               # Graceful exit on Ctrl+C
               if self._verbose:
                   print(f"[ProcessManager] {service.name} received KeyboardInterrupt")
               sys.exit(0)
           except Exception as e:
               # Log error but don't crash
               if self._verbose:
                   print(f"[ProcessManager] {service.name} error: {e}", file=sys.stderr)
               sys.exit(1)
       ```

    4. Update the docstring for start_all() method to reflect the change:
       Find line ~85 and update the docstring to mention the module-level wrapper:

       Change the existing docstring to include:
       "Each service runs in its own child process using the module-level
       _run_service_wrapper function (required for Windows pickle compatibility)."
  </action>
  <verify>
    Run: python -c "from configurable_agents.process.manager import ProcessManager; print('Import OK')"
  </verify>
  <done>
    - Module-level _run_service_wrapper function added (after imports)
    - ProcessManager.start_all() uses _run_service_wrapper instead of self._run_service
    - Old _run_service() instance method deleted
    - Process target is now fully pickleable (no bound methods)
  </done>
</task>

</tasks>

<verification>
Test the fix:
```bash
python -c "from configurable_agents.cli import cmd_ui; print('Import OK - no pickle errors')"
```

Should import without "TypeError: cannot pickle 'weakref.ReferenceType' object" error.

Actual test (if on Windows):
```bash
python -m configurable_agents ui
```

Should start Dashboard and Chat UI without pickle errors.
</verification>

<success_criteria>
- ProcessManager.start_all() no longer uses bound method as Process target
- Module-level _run_service_wrapper function exists and is used
- Old _run_service() instance method removed
- Services launch correctly on Windows without pickle errors
- Error handling still works (KeyboardInterrupt, generic exceptions)
</success_criteria>

<output>
After completion, create `.planning/quick/004-fix-bound-method-pickle/004-SUMMARY.md`
</output>
