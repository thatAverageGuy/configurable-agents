"""File I/O tools for reading, writing, and manipulating files.

Provides four main tools:
- file_read: Read file contents
- file_write: Write content to files
- file_glob: Find files matching a pattern
- file_move: Move/rename files

Security: All file operations are restricted to safe directories
(configured via ALLOWED_PATHS env var or current working directory).

Example:
    >>> from configurable_agents.tools import get_tool
    >>> read_tool = get_tool("file_read")
    >>> result = read_tool.run({"path": "data.txt"})
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool

from configurable_agents.tools.registry import ToolConfigError

logger = logging.getLogger(__name__)


def _get_allowed_paths() -> List[str]:
    """Get list of allowed directory paths for file operations.

    Reads from ALLOWED_PATHS env var (comma-separated), defaults to [cwd].

    Returns:
        List of allowed directory paths
    """
    allowed_env = os.getenv("ALLOWED_PATHS", "")
    if allowed_env:
        return [p.strip() for p in allowed_env.split(",")]
    return [os.getcwd()]


def _is_safe_path(path: str) -> bool:
    """Check if a path is safe for file operations.

    A path is safe if:
    - It's within an allowed directory

    We normalize paths first, so ".." components are resolved before
    the safety check.

    Args:
        path: Path to check

    Returns:
        True if path is safe, False otherwise
    """
    # Resolve to absolute path (this resolves .. components)
    abs_path = os.path.abspath(path)

    # Check if within allowed paths
    for allowed in _get_allowed_paths():
        allowed_abs = os.path.abspath(allowed)
        # Check if path is within allowed directory
        try:
            rel_path = os.path.relpath(abs_path, allowed_abs)
            # If rel_path doesn't start with .., it's within the allowed path
            if not rel_path.startswith(".."):
                return True
        except ValueError:
            # Different drives on Windows
            pass

    return False


def _normalize_path(path: str, base_path: str = ".") -> str:
    """Normalize a path relative to base path.

    Args:
        path: Path to normalize
        base_path: Base directory (default: current dir)

    Returns:
        Normalized absolute path
    """
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(base_path, path))


def file_read(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Read file contents.

    Args:
        path: File path to read
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with path, content, size, error

    Example:
        >>> result = file_read("data.txt")
        >>> content = result["content"]
    """
    # Normalize path
    norm_path = _normalize_path(path)

    # Security check
    if not _is_safe_path(norm_path):
        return {
            "path": path,
            "content": "",
            "size": 0,
            "error": f"Path not allowed or contains '..': {path}",
        }

    # Check if exists
    if not os.path.isfile(norm_path):
        return {
            "path": path,
            "content": "",
            "size": 0,
            "error": f"File not found: {path}",
        }

    try:
        with open(norm_path, "r", encoding=encoding) as f:
            content = f.read()

        size = os.path.getsize(norm_path)

        # Truncate large files
        if len(content) > 50000:
            content = content[:50000] + "\n... (truncated)"

        return {
            "path": path,
            "content": content,
            "size": size,
            "error": None,
        }

    except IOError as e:
        logger.error(f"Error reading file {path}: {e}")
        return {
            "path": path,
            "content": "",
            "size": 0,
            "error": str(e),
        }
    except UnicodeDecodeError:
        return {
            "path": path,
            "content": "",
            "size": 0,
            "error": f"Failed to decode file with encoding '{encoding}'",
        }


def file_write(path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Write content to a file.

    Args:
        path: File path to write
        content: Content to write
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with path, bytes_written, error

    Example:
        >>> result = file_write("output.txt", "Hello, World!")
        >>> bytes_written = result["bytes_written"]
    """
    # Normalize path
    norm_path = _normalize_path(path)

    # Security check
    if not _is_safe_path(norm_path):
        return {
            "path": path,
            "bytes_written": 0,
            "error": f"Path not allowed or contains '..': {path}",
        }

    try:
        # Create parent directories if needed
        parent_dir = os.path.dirname(norm_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Write file
        bytes_written = 0
        with open(norm_path, "w", encoding=encoding, newline="\n") as f:
            f.write(content)
            bytes_written = len(content.encode(encoding))

        return {
            "path": path,
            "bytes_written": bytes_written,
            "error": None,
        }

    except IOError as e:
        logger.error(f"Error writing file {path}: {e}")
        return {
            "path": path,
            "bytes_written": 0,
            "error": str(e),
        }


def file_glob(pattern: str, base_path: str = ".") -> Dict[str, Any]:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., "*.txt", "data/*.csv")
        base_path: Base directory for search (default: current dir)

    Returns:
        Dict with pattern, matches list

    Example:
        >>> result = file_glob("*.py")
        >>> for file in result["matches"]:
        ...     print(file)
    """
    # Normalize base path
    norm_base = _normalize_path(base_path)

    # Security check on base path
    if not _is_safe_path(norm_base):
        return {
            "pattern": pattern,
            "matches": [],
            "error": f"Base path not allowed: {base_path}",
        }

    try:
        base = Path(norm_base)
        matches = [str(p) for p in base.glob(pattern) if _is_safe_path(str(p))]

        # Filter to files only (not directories)
        files = [m for m in matches if os.path.isfile(m)]

        return {
            "pattern": pattern,
            "matches": sorted(files),
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error globbing pattern {pattern}: {e}")
        return {
            "pattern": pattern,
            "matches": [],
            "error": str(e),
        }


def file_move(source: str, dest: str) -> Dict[str, Any]:
    """Move or rename a file.

    Args:
        source: Source file path
        dest: Destination file path

    Returns:
        Dict with source, dest, success, error

    Example:
        >>> result = file_move("old.txt", "new.txt")
        >>> if result["success"]:
        ...     print("File moved successfully")
    """
    # Normalize paths
    norm_source = _normalize_path(source)
    norm_dest = _normalize_path(dest)

    # Security checks
    if not _is_safe_path(norm_source):
        return {
            "source": source,
            "dest": dest,
            "success": False,
            "error": f"Source path not allowed: {source}",
        }

    if not _is_safe_path(norm_dest):
        return {
            "source": source,
            "dest": dest,
            "success": False,
            "error": f"Destination path not allowed: {dest}",
        }

    # Check source exists
    if not os.path.isfile(norm_source):
        return {
            "source": source,
            "dest": dest,
            "success": False,
            "error": f"Source file not found: {source}",
        }

    try:
        # Create parent directories if needed
        parent_dir = os.path.dirname(norm_dest)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Move file
        os.rename(norm_source, norm_dest)

        return {
            "source": source,
            "dest": dest,
            "success": True,
            "error": None,
        }

    except IOError as e:
        logger.error(f"Error moving file {source} to {dest}: {e}")
        return {
            "source": source,
            "dest": dest,
            "success": False,
            "error": str(e),
        }


# Tool factory functions

def create_file_read() -> Tool:
    """Create file read tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="file_read",
        description=(
            "Read contents of a file. "
            "Input should be a dict with 'path' (required) and 'encoding' (optional, default utf-8). "
            "Returns file content, size, and error if any."
        ),
        func=lambda x: file_read(**x) if isinstance(x, dict) else file_read(x),
    )


def create_file_write() -> Tool:
    """Create file write tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="file_write",
        description=(
            "Write content to a file. Creates parent directories if needed. "
            "Input should be a dict with 'path' (required), 'content' (required), "
            "and 'encoding' (optional, default utf-8). "
            "Returns bytes written and error if any."
        ),
        func=file_write,
    )


def create_file_glob() -> Tool:
    """Create file glob tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="file_glob",
        description=(
            "Find files matching a glob pattern. "
            "Input should be a dict with 'pattern' (required) and 'base_path' (optional, default '.'). "
            "Returns list of matching file paths."
        ),
        func=lambda x: file_glob(**x) if isinstance(x, dict) else file_glob(x),
    )


def create_file_move() -> Tool:
    """Create file move tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="file_move",
        description=(
            "Move or rename a file. Creates parent directories if needed. "
            "Input should be a dict with 'source' (required) and 'dest' (required). "
            "Returns success status and error if any."
        ),
        func=file_move,
    )


# Register tools
def register_tools(registry: Any) -> None:
    """Register all file tools.

    Args:
        registry: ToolRegistry instance
    """
    registry.register_tool("file_read", create_file_read)
    registry.register_tool("file_write", create_file_write)
    registry.register_tool("file_glob", create_file_glob)
    registry.register_tool("file_move", create_file_move)


__all__ = [
    "file_read",
    "file_write",
    "file_glob",
    "file_move",
    "create_file_read",
    "create_file_write",
    "create_file_glob",
    "create_file_move",
    "register_tools",
]
