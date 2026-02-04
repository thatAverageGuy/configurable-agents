"""Multi-process service orchestration manager.

Provides ProcessManager for spawning, monitoring, and gracefully shutting
down multiple services (Dashboard, Chat UI, etc.) as separate processes.
"""

import json
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Process
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage.models import SessionState


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
        self.save_session(active_workflows=[])

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

    # Session state persistence methods

    def _get_session_state(self) -> Optional[SessionState]:
        """Get or create the session state record from database.

        Returns:
            SessionState object or None if database not available
        """
        try:
            engine = create_engine(
                f"sqlite:///{StorageConfig().path}",
                connect_args={"check_same_thread": False}
            )

            with Session(engine) as session:
                # Try to get existing session state
                stmt = select(SessionState).where(SessionState.id == "default")
                result = session.scalar(stmt)

                if result:
                    return result

                # Create new session state (default is dirty=True for crash detection)
                new_state = SessionState(id="default", dirty_shutdown=1)
                session.add(new_state)
                session.commit()
                return new_state

        except Exception as e:
            if self._verbose:
                print(f"[ProcessManager] Warning: Could not access session state: {e}")
            return None

    def save_session(
        self,
        active_workflows: Optional[List[str]] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save current session state to database.

        Call this during shutdown to save active workflows and mark clean shutdown.

        Args:
            active_workflows: List of workflow IDs currently running
            session_data: Optional dict with additional session state

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            engine = create_engine(
                f"sqlite:///{StorageConfig().path}",
                connect_args={"check_same_thread": False}
            )

            with Session(engine) as session:
                # Get or create session state
                stmt = select(SessionState).where(SessionState.id == "default")
                state_obj = session.scalar(stmt)

                if state_obj is None:
                    state_obj = SessionState(id="default", dirty_shutdown=1)
                    session.add(state_obj)

                # Mark clean shutdown and save state
                state_obj.dirty_shutdown = 0
                state_obj.active_workflows = json.dumps(active_workflows or [])
                state_obj.session_data = json.dumps(session_data or {})
                state_obj.last_updated = datetime.utcnow()

                session.merge(state_obj)
                session.commit()
                return True

        except Exception as e:
            if self._verbose:
                print(f"[ProcessManager] Warning: Could not save session state: {e}")
            return False

    def check_restore_session(self) -> Optional[Dict[str, Any]]:
        """Check if previous session had a dirty shutdown and get restoration data.

        Call this during startup to detect crashes and offer restoration.

        Returns:
            Dict with restoration data if dirty shutdown detected, None otherwise.
            Dict contains: {'active_workflows': [...], 'session_data': {...} }
        """
        try:
            state = self._get_session_state()
            if state is None or not state.is_dirty:
                return None

            # Parse saved state
            active_workflows = []
            session_data = {}

            if state.active_workflows:
                try:
                    active_workflows = json.loads(state.active_workflows)
                except json.JSONDecodeError:
                    pass

            if state.session_data:
                try:
                    session_data = json.loads(state.session_data)
                except json.JSONDecodeError:
                    pass

            return {
                "active_workflows": active_workflows,
                "session_data": session_data,
                "last_session_start": state.session_start.isoformat() if state.session_start else None,
            }

        except Exception as e:
            if self._verbose:
                print(f"[ProcessManager] Warning: Could not check session state: {e}")
            return None

    def mark_session_dirty(self) -> None:
        """Mark session as dirty (crash possible).

        Call this at startup so that any crash will be detected next time.
        """
        try:
            engine = create_engine(
                f"sqlite:///{StorageConfig().path}",
                connect_args={"check_same_thread": False}
            )

            with Session(engine) as session:
                stmt = select(SessionState).where(SessionState.id == "default")
                state_obj = session.scalar(stmt)

                if state_obj is None:
                    state_obj = SessionState(id="default", dirty_shutdown=1)
                    session.add(state_obj)
                else:
                    state_obj.dirty_shutdown = 1
                    state_obj.session_start = datetime.utcnow()

                session.commit()

        except Exception as e:
            if self._verbose:
                print(f"[ProcessManager] Warning: Could not mark session dirty: {e}")
