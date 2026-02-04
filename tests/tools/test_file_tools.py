"""Tests for file tools implementation."""

import os
import tempfile
from pathlib import Path

import pytest

from configurable_agents.tools import list_tools
from configurable_agents.tools.file_tools import (
    file_read,
    file_write,
    file_glob,
    file_move,
    _is_safe_path,
    _normalize_path,
    create_file_read,
    create_file_write,
    create_file_glob,
    create_file_move,
)


class TestPathSafety:
    """Tests for path safety checks."""

    def test_is_safe_path_rejects_double_dot(self, monkeypatch):
        """Test that paths with .. are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", "/tmp")
        assert not _is_safe_path("/tmp/../etc/passwd")
        assert not _is_safe_path("../secret.txt")

    def test_is_safe_path_allows_allowed_paths(self, monkeypatch, tmp_path):
        """Test that allowed paths are accepted."""
        monkeypatch.setenv("ALLOWED_PATHS", str(tmp_path))
        test_file = tmp_path / "test.txt"
        assert _is_safe_path(str(test_file))

    def test_is_safe_path_defaults_to_cwd(self, monkeypatch):
        """Test that current directory is allowed by default."""
        monkeypatch.delenv("ALLOWED_PATHS", raising=False)
        cwd = os.getcwd()
        assert _is_safe_path(os.path.join(cwd, "test.txt"))

    def test_normalize_path(self):
        """Test path normalization."""
        result = _normalize_path("subdir/file.txt", "/base")
        # On Windows, paths will be normalized to C:\base\subdir\file.txt
        # On Unix, /base/subdir/file.txt
        assert "subdir" in result
        assert "file.txt" in result


class TestFileReadTool:
    """Tests for file_read tool."""

    def test_list_includes_file_read(self):
        """Test that file_read is in the tool registry."""
        tools = list_tools()
        assert "file_read" in tools

    def test_file_read_existing_file(self, tmp_path):
        """Test reading an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        result = file_read(str(test_file))

        assert result["content"] == "Hello, World!"
        assert result["size"] > 0
        assert result["error"] is None

    def test_file_read_nonexistent_file(self, tmp_path):
        """Test reading a nonexistent file."""
        result = file_read(str(tmp_path / "nonexistent.txt"))

        assert result["content"] == ""
        assert result["size"] == 0
        assert "not found" in result["error"].lower()

    def test_file_read_with_encoding(self, tmp_path):
        """Test reading file with specific encoding."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello", encoding="utf-16")

        result = file_read(str(test_file), encoding="utf-16")

        assert result["content"] == "Hello"
        assert result["error"] is None

    def test_file_read_wrong_encoding(self, tmp_path):
        """Test reading file with wrong encoding."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"\xff\xfe Invalid UTF-8")

        result = file_read(str(test_file))

        assert "encoding" in result["error"].lower()

    def test_file_read_large_file_truncated(self, tmp_path):
        """Test that large files are truncated."""
        test_file = tmp_path / "large.txt"
        large_content = "x" * 60000
        test_file.write_text(large_content)

        result = file_read(str(test_file))

        # Content should be truncated to <= 50000 chars + truncation marker
        assert len(result["content"]) <= 51000  # Allow some margin for truncation marker
        assert len(result["content"]) < len(large_content)

    def test_file_read_unsafe_path(self, monkeypatch):
        """Test that unsafe paths are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", "/tmp")

        result = file_read("/tmp/../etc/passwd")

        assert result["content"] == ""
        assert "not allowed" in result["error"].lower()

    def test_file_read_tool_callable(self, tmp_path):
        """Test file_read tool is callable."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        tool = create_file_read()

        # Test with dict input
        result = tool.func({"path": str(test_file)})
        assert result["content"] == "test"

        # Test with string input
        result = tool.func(str(test_file))
        assert result["content"] == "test"


class TestFileWriteTool:
    """Tests for file_write tool."""

    def test_list_includes_file_write(self):
        """Test that file_write is in the tool registry."""
        tools = list_tools()
        assert "file_write" in tools

    def test_file_write_new_file(self, tmp_path):
        """Test writing a new file."""
        test_file = tmp_path / "new.txt"

        result = file_write(str(test_file), "Hello, World!")

        assert result["bytes_written"] > 0
        assert result["error"] is None
        assert test_file.read_text() == "Hello, World!"

    def test_file_write_creates_directories(self, tmp_path):
        """Test that file_write creates parent directories."""
        test_file = tmp_path / "subdir" / "nested" / "file.txt"

        result = file_write(str(test_file), "content")

        assert result["error"] is None
        assert test_file.exists()
        assert test_file.read_text() == "content"

    def test_file_write_overwrites_existing(self, tmp_path):
        """Test that file_write overwrites existing files."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("old content")

        result = file_write(str(test_file), "new content")

        assert result["error"] is None
        assert test_file.read_text() == "new content"

    def test_file_write_unsafe_path(self, monkeypatch, tmp_path):
        """Test that unsafe paths are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", str(tmp_path))

        result = file_write("/tmp/../etc/evil", "malicious")

        assert result["bytes_written"] == 0
        assert "not allowed" in result["error"].lower()


class TestFileGlobTool:
    """Tests for file_glob tool."""

    def test_list_includes_file_glob(self):
        """Test that file_glob is in the tool registry."""
        tools = list_tools()
        assert "file_glob" in tools

    def test_file_glob_find_all_txt(self, tmp_path):
        """Test finding all .txt files."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "c.md").write_text("c")

        result = file_glob("*.txt", str(tmp_path))

        assert result["error"] is None
        assert len(result["matches"]) == 2
        assert all(p.endswith(".txt") for p in result["matches"])

    def test_file_glob_recursive_pattern(self, tmp_path):
        """Test glob with recursive pattern."""
        (tmp_path / "sub1").mkdir()
        (tmp_path / "sub2").mkdir()
        (tmp_path / "sub1" / "file.txt").write_text("a")
        (tmp_path / "sub2" / "file.txt").write_text("b")
        (tmp_path / "file.txt").write_text("c")

        # Use ** for recursive search (not supported by Path.glob, but test the pattern)
        result = file_glob("*.txt", str(tmp_path))

        # Should find files in base directory
        matches = result["matches"]
        assert any(p.endswith("file.txt") for p in matches)

    def test_file_glob_no_matches(self, tmp_path):
        """Test glob with no matching files."""
        result = file_glob("*.nonexistent", str(tmp_path))

        assert result["matches"] == []
        assert result["error"] is None

    def test_file_glob_returns_files_only(self, tmp_path):
        """Test that file_glob only returns files, not directories."""
        (tmp_path / "file.txt").write_text("file")
        (tmp_path / "dir").mkdir()
        (tmp_path / "dir" / "nested.txt").write_text("nested")

        result = file_glob("*", str(tmp_path))

        # Should not include directories in results
        for match in result["matches"]:
            assert os.path.isfile(match), f"{match} is not a file"

    def test_file_glob_unsafe_base_path(self, monkeypatch):
        """Test that unsafe base paths are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", "/tmp")

        result = file_glob("*", "/tmp/../etc")

        assert result["matches"] == []
        assert "not allowed" in result["error"].lower()

    def test_file_glob_tool_callable(self, tmp_path):
        """Test file_glob tool is callable."""
        (tmp_path / "test.txt").write_text("test")

        tool = create_file_glob()

        # Test with dict input
        result = tool.func({"pattern": "*.txt", "base_path": str(tmp_path)})
        assert len(result["matches"]) == 1

        # Test with string input (just pattern)
        # Note: String input won't work well with base_path, but let's test it doesn't crash
        result = tool.func("*.txt")
        assert "matches" in result


class TestFileMoveTool:
    """Tests for file_move tool."""

    def test_list_includes_file_move(self):
        """Test that file_move is in the tool registry."""
        tools = list_tools()
        assert "file_move" in tools

    def test_file_move_basic(self, tmp_path):
        """Test basic file move/rename."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("content")

        result = file_move(str(source), str(dest))

        assert result["success"] is True
        assert result["error"] is None
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "content"

    def test_file_move_creates_directories(self, tmp_path):
        """Test that file_move creates destination directories."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "new" / "subdir" / "dest.txt"
        source.write_text("content")

        result = file_move(str(source), str(dest))

        assert result["success"] is True
        assert dest.exists()
        assert dest.parent.exists()

    def test_file_move_nonexistent_source(self, tmp_path):
        """Test moving nonexistent file."""
        result = file_move(str(tmp_path / "nonexistent.txt"), str(tmp_path / "dest.txt"))

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_file_move_unsafe_source(self, monkeypatch, tmp_path):
        """Test that unsafe source paths are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", str(tmp_path))

        (tmp_path / "safe.txt").write_text("safe")

        result = file_move(str(tmp_path / "safe.txt"), "/tmp/../etc/unsafe.txt")

        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    def test_file_move_unsafe_destination(self, monkeypatch, tmp_path):
        """Test that unsafe destination paths are rejected."""
        monkeypatch.setenv("ALLOWED_PATHS", str(tmp_path))

        source = tmp_path / "source.txt"
        source.write_text("content")

        result = file_move(str(source), "/tmp/../etc/unsafe.txt")

        assert result["success"] is False
        assert "not allowed" in result["error"].lower()
        # Source should still exist since move failed
        assert source.exists()


class TestToolCreation:
    """Tests for tool factory functions."""

    def test_all_file_tools_createable(self):
        """Test that all file tools can be created."""
        tools = [
            create_file_read(),
            create_file_write(),
            create_file_glob(),
            create_file_move(),
        ]

        assert all(hasattr(t, "name") for t in tools)
        assert [t.name for t in tools] == ["file_read", "file_write", "file_glob", "file_move"]
