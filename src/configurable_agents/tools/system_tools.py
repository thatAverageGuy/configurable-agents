"""System tools for shell commands, process management, and environment variables.

Provides three main tools:
- shell: Execute shell commands with timeout
- process: Spawn and monitor background processes
- env_vars: Read environment variables

Security: Shell commands are restricted to ALLOWED_COMMANDS env var.

Example:
    >>> from configurable_agents.tools import get_tool
    >>> shell_tool = get_tool("shell")
    >>> result = shell_tool.func({"command": "ls -la"})
"""

import logging
import os
import subprocess
from typing import Any, Dict, List

from langchain_core.tools import Tool

from configurable_agents.tools.registry import ToolConfigError

logger = logging.getLogger(__name__)


def _get_allowed_commands() -> List[str]:
    """Get list of allowed shell commands.

    Reads from ALLOWED_COMMANDS env var (comma-separated).
    Returns empty list if not configured (all commands blocked).

    Returns:
        List of allowed command names
    """
    allowed_env = os.getenv("ALLOWED_COMMANDS", "")
    if not allowed_env or allowed_env == "*":
        return []  # Empty means no commands allowed unless explicitly configured
    return [cmd.strip() for cmd in allowed_env.split(",") if cmd.strip()]


def shell(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute shell command.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default: 30)

    Returns:
        Dict with stdout, stderr, returncode, error

    Example:
        >>> result = shell("echo hello")
        >>> assert result["stdout"].strip() == "hello"
    """
    allowed = _get_allowed_commands()

    # Extract command name
    command_parts = command.split()
    if not command_parts:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": 1,
            "error": "Empty command",
        }

    command_name = command_parts[0]

    # Check if command is allowed
    if allowed and command_name not in allowed:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": 1,
            "error": f"Command '{command_name}' not in allowed list. Set ALLOWED_COMMANDS env var.",
        }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Truncate large output
        stdout = result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout
        stderr = result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "returncode": -1,
            "error": f"Timeout after {timeout} seconds",
        }
    except Exception as e:
        logger.error(f"Shell command error: {e}")
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e),
        }


# Store for background processes
_background_processes: Dict[int, subprocess.Popen] = {}


def process(command: str, args: List[str] = None) -> Dict[str, Any]:
    """Spawn background process.

    Args:
        command: Command to execute
        args: Command arguments

    Returns:
        Dict with pid, status, error

    Example:
        >>> result = process("python", ["-c", "print('hello')"])
        >>> pid = result["pid"]
    """
    allowed = _get_allowed_commands()

    # Check if command is allowed
    if allowed and command not in allowed:
        return {
            "pid": 0,
            "status": "failed",
            "error": f"Command '{command}' not in allowed list. Set ALLOWED_COMMANDS env var.",
        }

    cmd_args = [command]
    if args:
        cmd_args.extend(args)

    try:
        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pid = proc.pid
        _background_processes[pid] = proc

        return {
            "pid": pid,
            "status": "running",
            "error": None,
        }

    except Exception as e:
        logger.error(f"Process spawn error: {e}")
        return {
            "pid": 0,
            "status": "failed",
            "error": str(e),
        }


def env_vars(pattern: str = None) -> Dict[str, Any]:
    """Read environment variables.

    Args:
        pattern: Optional pattern to filter variables (e.g., "PATH*")

    Returns:
        Dict with vars (filtered), error

    Example:
        >>> result = env_vars("PATH*")
        >>> print(result["vars"])
    """
    # Sensitive patterns to exclude
    sensitive_patterns = ["KEY", "SECRET", "PASSWORD", "TOKEN", "API"]

    try:
        vars_dict = {}

        for key, value in os.environ.items():
            # Filter by pattern if provided
            if pattern:
                import fnmatch
                if not fnmatch.fnmatch(key, pattern):
                    continue

            # Exclude sensitive variables
            if any(sens in key.upper() for sens in sensitive_patterns):
                continue

            vars_dict[key] = value

        return {
            "vars": vars_dict,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Environment vars error: {e}")
        return {
            "vars": {},
            "error": str(e),
        }


# Tool factory functions

def create_shell() -> Tool:
    """Create shell tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="shell",
        description=(
            "Execute shell command. "
            "Input should be a dict with 'command' (required) and optional 'timeout' (default 30 seconds). "
            "Returns stdout, stderr, returncode, and error if any. "
            "Commands must be in ALLOWED_COMMANDS env var for security."
        ),
        func=lambda x: shell(**x) if isinstance(x, dict) else shell(x),
    )


def create_process() -> Tool:
    """Create process tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="process",
        description=(
            "Spawn background process. "
            "Input should be a dict with 'command' (required) and optional 'args' (list). "
            "Returns pid, status, and error if any."
        ),
        func=process,
    )


def create_env_vars() -> Tool:
    """Create env_vars tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="env_vars",
        description=(
            "Read environment variables. "
            "Input should be a dict with optional 'pattern' to filter variable names. "
            "Returns vars dict and error if any. "
            "Excludes sensitive variables (KEY, SECRET, PASSWORD, TOKEN, API)."
        ),
        func=lambda x: env_vars(**x) if isinstance(x, dict) else env_vars(),
    )


# Register tools
def register_tools(registry: Any) -> None:
    """Register all system tools.

    Args:
        registry: ToolRegistry instance
    """
    registry.register_tool("shell", create_shell)
    registry.register_tool("process", create_process)
    registry.register_tool("env_vars", create_env_vars)


__all__ = [
    "shell",
    "process",
    "env_vars",
    "create_shell",
    "create_process",
    "create_env_vars",
    "register_tools",
]
