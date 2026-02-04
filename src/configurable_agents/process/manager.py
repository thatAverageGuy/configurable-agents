"""Multi-process service orchestration manager.

Provides ProcessManager for spawning, monitoring, and gracefully shutting
down multiple services (Dashboard, Chat UI, etc.) as separate processes.
"""

import signal
import sys
from dataclasses import dataclass
from multiprocessing import Process
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ServiceSpec:
    """Specification for a service to run as a separate process.

    Attributes:
        name: Human-readable service name for logging
        target: Callable to run in the child process (must be pickleable)
        args: Positional arguments to pass to target
        kwargs: Keyword arguments to pass to target
    """

    name: str
    target: Callable[..., None]
    args: tuple = ()
    kwargs: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class ProcessManager:
    """Orchestrates multiple services as separate processes.

    Manages the complete lifecycle of child processes including spawning,
    monitoring signal-based shutdown, and graceful termination with timeout.

    Platform compatibility:
        - Windows: Uses spawn method (default), limited signal handling (SIGINT only)
        - Unix: Full signal support (SIGINT, SIGTERM)

    Example:
        >>> def run_dashboard():
        ...     # Start FastAPI dashboard
        ...     uvicorn.run(app, host="0.0.0.0", port=7861)
        >>> manager = ProcessManager()
        >>> manager.add_service(ServiceSpec("dashboard", run_dashboard))
        >>> manager.start_all()
        >>> manager.wait()  # Blocks until Ctrl+C
        >>> manager.shutdown()  # Called by signal handler
    """

    def __init__(self, verbose: bool = False):
        """Initialize the ProcessManager.

        Args:
            verbose: Enable verbose logging to stderr
        """
        self._services: List[ServiceSpec] = []
        self._processes: Dict[str, Process] = {}
        self._verbose = verbose
        self._shutdown_flag = False

    def add_service(self, service: ServiceSpec) -> None:
        """Register a service to be started.

        Args:
            service: ServiceSpec describing the service to run
        """
        self._services.append(service)
        if self._verbose:
            print(f"[ProcessManager] Registered service: {service.name}")

    def start_all(self) -> None:
        """Spawn all registered services as separate processes.

        Each service runs in its own child process using multiprocessing.Process
        with daemon=False to ensure clean shutdown behavior.

        Raises:
            RuntimeError: If no services have been registered
        """
        if not self._services:
            raise RuntimeError("No services registered. Add services with add_service() first.")

        for service in self._services:
            process = Process(
                target=self._run_service,
                args=(service,),
                name=service.name,
                daemon=False,  # Don't use daemon to ensure clean shutdown
            )
            process.start()
            self._processes[service.name] = process

            if self._verbose:
                print(f"[ProcessManager] Started {service.name} (PID: {process.pid})")

        # Register signal handlers after spawning processes
        self._register_signal_handlers()

    def _run_service(self, service: ServiceSpec) -> None:
        """Run a service target with error handling.

        This method runs in the child process. It wraps the service target
        to catch and log any exceptions before the process exits.

        Args:
            service: ServiceSpec describing the service to run
        """
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

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown.

        On Windows: Only SIGINT (Ctrl+C) is supported
        On Unix: SIGINT and SIGTERM are supported
        """
        # Only register handlers in the main process
        if sys.platform == "win32":
            # Windows has limited signal support
            signal.signal(signal.SIGINT, self._signal_handler)
        else:
            # Unix-like systems have full signal support
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals (SIGINT, SIGTERM).

        Sets the shutdown flag and initiates graceful shutdown.
        This handler must be fast - it just sets a flag and calls shutdown.

        Args:
            signum: Signal number received
            frame: Current stack frame (unused)
        """
        # Avoid multiple shutdown attempts
        if self._shutdown_flag:
            return

        self._shutdown_flag = True

        if self._verbose:
            signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else signum
            print(f"[ProcessManager] Received signal {signal_name}, shutting down...")

        # Initiate shutdown (don't block in signal handler)
        self.shutdown()

    def wait(self) -> None:
        """Wait for all processes to complete.

        Blocks until all child processes exit or a shutdown signal is received.
        This method monitors process health and returns on first failure.

        Returns immediately if shutdown_flag is set (e.g., by signal handler).
        """
        # Check if already shutting down
        if self._shutdown_flag:
            return

        try:
            # Wait for processes with periodic checks
            while self._processes and not self._shutdown_flag:
                for name, process in list(self._processes.items()):
                    process.join(timeout=0.1)

                    # Check if process exited
                    if not process.is_alive():
                        exit_code = process.exitcode
                        if exit_code != 0:
                            if self._verbose:
                                print(
                                    f"[ProcessManager] {name} exited with code {exit_code}",
                                    file=sys.stderr
                                )
                            # One process failed, trigger shutdown
                            self.shutdown()
                            return

                        # Process exited cleanly, remove from tracking
                        del self._processes[name]

                # Check shutdown flag again after the loop
                if self._shutdown_flag:
                    break

        except KeyboardInterrupt:
            # Handle Ctrl+C directly
            if self._verbose:
                print("[ProcessManager] KeyboardInterrupt in wait()")
            self.shutdown()

    def shutdown(self) -> None:
        """Terminate all processes gracefully with timeout.

        Shutdown sequence:
        1. Save session state (marks clean shutdown) - no-op until Task 4
        2. Send terminate() to all alive processes (SIGTERM)
        3. Wait up to 5 seconds for graceful exit
        4. Kill any remaining processes (SIGKILL)

        This method is idempotent - multiple calls are safe.
        """
        if self._shutdown_flag and not self._processes:
            # Already shut down
            return

        # Note: save_session will be implemented in Task 4
        # For now, this is a no-op that will be enhanced later
        self._save_session_noop(active_workflows=[])

        if self._verbose:
            print(f"[ProcessManager] Shutting down {len(self._processes)} processes...")

        # Terminate all processes
        for name, process in self._processes.items():
            if process.is_alive():
                if self._verbose:
                    print(f"[ProcessManager] Terminating {name}...")
                process.terminate()

        # Wait with timeout for graceful shutdown
        for name, process in self._processes.items():
            process.join(timeout=5)

            if process.is_alive():
                # Force kill if didn't shut down gracefully
                if self._verbose:
                    print(f"[ProcessManager] Killing {name} (did not shut down gracefully)")
                process.kill()
                process.join(timeout=1)

        self._processes.clear()
        self._shutdown_flag = True

    # Session state persistence methods (no-op stubs for Task 1)
    # These will be fully implemented in Task 4 after SessionState model exists

    def _save_session_noop(
        self,
        active_workflows: Optional[List[str]] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save session state - no-op stub (implemented in Task 4).

        Args:
            active_workflows: List of workflow IDs currently running
            session_data: Optional dict with additional session state

        Returns:
            True (stub always returns True)
        """
        # Session persistence will be added in Task 4
        # This is a placeholder to maintain the API signature
        return True

    def save_session(
        self,
        active_workflows: Optional[List[str]] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save session state - no-op stub (implemented in Task 4).

        Call this during shutdown to save active workflows and mark clean shutdown.

        Args:
            active_workflows: List of workflow IDs currently running
            session_data: Optional dict with additional session state

        Returns:
            True (stub always returns True)
        """
        # Session persistence will be added in Task 4
        return True

    def check_restore_session(self) -> Optional[Dict[str, Any]]:
        """Check for dirty shutdown - no-op stub (implemented in Task 4).

        Returns:
            None (stub always returns None)
        """
        # Session restoration will be added in Task 4
        return None

    def mark_session_dirty(self) -> None:
        """Mark session as dirty - no-op stub (implemented in Task 4).

        Call this at startup so that any crash will be detected next time.
        """
        # Session marking will be added in Task 4
        pass
