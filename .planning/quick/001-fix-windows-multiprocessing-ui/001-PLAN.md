---
phase: quick-001-fix-windows-multiprocessing-ui
plan: 001
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/cli.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "UI command runs successfully on Windows without AttributeError"
    - "Dashboard process starts correctly"
    - "Chat UI process starts correctly"
    - "Processes can be spawned using multiprocessing spawn method"
  artifacts:
    - path: "src/configurable_agents/cli.py"
      provides: "Module-level functions for multiprocessing"
      contains: "def _run_dashboard_service"
      contains: "def _run_chat_service"
  key_links:
    - from: "cli.py"
      to: "multiprocessing.Process"
      via: "pickleable module-level functions"
      pattern: "Process\\(target=_run_dashboard_service\\)"
---

<objective>
Fix Windows multiprocessing bug when running `configurable-agents ui` command.

Purpose: The error `AttributeError: Can't get local object 'cmd_ui.<locals>.run_dashboard'` occurs because Python's multiprocessing spawn method (default on Windows) requires functions to be pickleable, but local/closure functions cannot be pickled.

Output: Module-level helper functions that can be pickled and passed to multiprocessing.Process
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/quick/001-fix-windows-multiprocessing-ui
@src/configurable_agents/cli.py
@src/configurable_agents/process/manager.py
</context>

<tasks>

<task type="auto">
  <name>Move run_dashboard and run_chat functions to module level</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
    The functions `run_dashboard` and `run_chat` are currently defined as nested local functions inside `cmd_ui` (lines 1512-1535). These must be moved to module level to be pickleable on Windows.

    Changes to make:

    1. Define module-level functions BEFORE `cmd_ui` function (around line 1469):
       - Rename to `_run_dashboard_service(host, port, db_url, mlflow_uri)` with underscore to indicate internal use
       - Rename to `_run_chat_service(host, chat_port, dashboard_host, dashboard_port, verbose)` with underscore
       - These functions accept their configuration as parameters instead of closing over `args`

    2. Update `cmd_ui` function (lines 1512-1563):
       - Remove the nested function definitions
       - Pass the module-level functions to `manager.add_service()`:
         - For dashboard: `target=lambda: _run_dashboard_service(args.host, args.dashboard_port, args.db_url, args.mlflow_uri)`
         - For chat: `target=lambda: _run_chat_service(args.host, args.chat_port, args.host, args.dashboard_port, args.verbose)`
       - Using lambda is safe because the lambda is defined at module level and only closes over simple values from args

    Example structure:
    ```python
    # Module-level functions (add before cmd_ui, around line 1427)

    def _run_dashboard_service(host: str, port: int, db_url: str, mlflow_uri: Optional[str]) -> None:
        """Run dashboard server - module level for pickle compatibility on Windows."""
        dashboard = create_dashboard_app(
            db_url=db_url,
            mlflow_tracking_uri=mlflow_uri,
        )
        uvicorn.run(
            dashboard.get_app(),
            host=host,
            port=port,
            log_level="info",  # Can be parameterized later if needed
        )

    def _run_chat_service(host: str, port: int, dashboard_host: str, dashboard_port: int, verbose: bool) -> None:
        """Run chat UI - module level for pickle compatibility on Windows."""
        dashboard_url = f"http://{dashboard_host}:{dashboard_port}"
        from configurable_agents.ui import create_gradio_chat_ui
        ui = create_gradio_chat_ui(dashboard_url=dashboard_url)
        ui.launch(
            server_name=host,
            server_port=port,
            share=False,
            quiet=not verbose,
        )
    ```

    Then in cmd_ui, replace lines 1537-1563 with:
    ```python
    # Add dashboard service
    if console:
        console.print(f"[bold blue]Starting Dashboard...[/bold blue]")
    else:
        print_info("Starting Dashboard...")

    manager.add_service(ServiceSpec(
        name="dashboard",
        target=lambda: _run_dashboard_service(args.host, args.dashboard_port, args.db_url, args.mlflow_uri),
    ))

    if console:
        console.print(f"[green]OK[/green] Dashboard configured on port {args.dashboard_port}")
    else:
        print_success(f"Dashboard configured on port {args.dashboard_port}")

    # Add chat UI service
    if not args.no_chat:
        if console:
            console.print(f"[bold blue]Starting Chat UI...[/bold blue]")
        else:
            print_info("Starting Chat UI...")

        manager.add_service(ServiceSpec(
            name="chat",
            target=lambda: _run_chat_service(args.host, args.chat_port, args.host, args.dashboard_port, args.verbose),
        ))

        if console:
            console.print(f"[green]OK[/green] Chat UI configured on port {args.chat_port}")
        else:
            print_success(f"Chat UI configured on port {args.chat_port}")
    ```

    Why lambda works here: The lambda closes over `args` which is an argparse.Namespace object. Namespaces are pickleable (they're just simple objects with __dict__). The key is that the lambda itself is defined at module level scope, not nested inside another function.
  </action>
  <verify>
    Test the fix on Windows or simulate the spawn behavior:
    ```bash
    python -c "from multiprocessing import Pool; from src.configurable_agents.cli import _run_dashboard_service, _run_chat_service; print('Functions are pickleable')"
    ```
    Then run:
    ```bash
    configurable-agents ui --help  # Should execute without import errors
    ```
  </verify>
  <done>
    The `configurable-agents ui` command starts successfully on Windows without `AttributeError: Can't get local object` error.
  </done>
</task>

</tasks>

<verification>
After completing the task, verify:
1. `configurable-agents ui` command executes without AttributeError on Windows
2. Both dashboard and chat UI processes spawn correctly
3. Services are accessible at their configured ports
</verification>

<success_criteria>
- Module-level helper functions `_run_dashboard_service` and `_run_chat_service` exist
- No local/closure functions are passed to multiprocessing.Process
- UI command works on Windows using spawn method
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-windows-multiprocessing-ui/001-SUMMARY.md`
</output>
