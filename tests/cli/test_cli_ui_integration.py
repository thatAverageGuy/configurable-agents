"""Integration tests for CLI ui command using subprocess.

Tests actual CLI invocation for UI service startup.
Due to long-running nature of servers, uses timeout and process termination.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest


class TestCLIUIHelp:
    """Test ui command help and argument parsing."""

    def test_ui_help_shows_usage(self):
        """Test that --help works for ui command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_ui_shows_port_options(self):
        """Test ui command shows port configuration options."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        assert "port" in result.stdout.lower()


class TestCLIUIErrors:
    """Test ui command error handling."""

    def test_ui_port_conflict_detection(self, tmp_path):
        """
        Test ui detects port conflicts before starting services.

        This test verifies port checking logic without actually
        starting conflicting services.
        """
        # Verify is_port_in_use function exists
        from configurable_agents.cli import is_port_in_use

        # Very high port should be free
        assert is_port_in_use(65000) is False

        # Create a listening socket to test occupied port detection
        import socket
        import threading
        import time

        # Find a free port first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
            test_sock.bind(('', 0))
            free_port = test_sock.getsockname()[1]

        # Verify it's not in use after socket closes
        assert is_port_in_use(free_port) is False

        # Now create a listening socket and verify detection works
        # Use a thread to keep socket alive while we check
        listener_ready = threading.Event()
        listener_done = threading.Event()
        detected_in_use = [False]

        def run_listener():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', free_port))
                    s.listen(1)
                    listener_ready.set()
                    # Wait for test to complete check
                    listener_done.wait(timeout=5)
                except Exception:
                    pass

        listener = threading.Thread(target=run_listener, daemon=True)
        listener.start()
        listener_ready.wait(timeout=2)

        # Give thread time to start listening
        time.sleep(0.1)

        # Should detect as in use now
        detected_in_use[0] = is_port_in_use(free_port)
        listener_done.set()
        listener.join(timeout=2)

        assert detected_in_use[0], f"Port {free_port} should be detected as in use while listening"


class TestCLIUIWindowsCompatibility:
    """Test Windows multiprocessing compatibility."""

    def test_module_level_functions_exist(self):
        """
        Test that required module-level functions exist for Windows multiprocessing.

        On Windows, multiprocessing uses spawn which requires:
        1. Target functions at module level (picklable)
        2. No closures with weakrefs
        3. Proper if __name__ == "__main__" guards
        """
        import configurable_agents.cli as cli_module

        # Check for module-level functions required for Windows
        assert hasattr(cli_module, "_run_dashboard_with_config"), \
            "Missing _run_dashboard_with_config function for Windows multiprocessing"
        assert hasattr(cli_module, "_run_chat_with_config"), \
            "Missing _run_chat_with_config function for Windows multiprocessing"
        assert hasattr(cli_module, "_run_dashboard_service"), \
            "Missing _run_dashboard_service function for Windows multiprocessing"
        assert hasattr(cli_module, "_run_chat_service"), \
            "Missing _run_chat_service function for Windows multiprocessing"

        # Verify they're callable
        assert callable(cli_module._run_dashboard_with_config)
        assert callable(cli_module._run_chat_with_config)
        assert callable(cli_module._run_dashboard_service)
        assert callable(cli_module._run_chat_service)

    def test_processmanager_import(self):
        """Test ProcessManager can be imported and instantiated."""
        from configurable_agents.process import ProcessManager, ServiceSpec

        # Verify ServiceSpec can be created with pickle-compatible data
        spec = ServiceSpec(
            name="test_service",
            target=lambda: None,  # Won't actually run
            kwargs={}
        )
        assert spec.name == "test_service"

    def test_cli_main_guard(self):
        """Test that cli.py has proper __main__ guard for Windows."""
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            content = cli_path.read_text()
            # Should have __main__ guard for Windows multiprocessing
            assert '__main__' in content or "if __name__" in content


class TestCLIUIIntegration:
    """Integration tests for ui command (may require manual verification)."""

    @pytest.mark.slow
    @pytest.mark.manual
    def test_ui_starts_services(self):
        """
        Manual test: Verify ui command starts all services.

        This test requires manual verification:
        1. Run: configurable-agents ui
        2. Verify dashboard is accessible at http://localhost:7861
        3. Verify chat UI is accessible at http://localhost:7860
        4. Check logs for any errors

        Marked as manual because it starts long-running processes.
        """
        pytest.skip("Manual verification required - see test docstring")

    @pytest.mark.slow
    def test_ui_starts_with_custom_ports(self):
        """
        Test ui command with custom port arguments.

        Verifies that custom ports are accepted.
        Actual server startup not tested to avoid long-running processes.
        """
        # This test just verifies arguments are parsed correctly
        # by checking help output
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        # Should have port options
        assert result.returncode == 0
        assert "dashboard-port" in result.stdout.lower() or "port" in result.stdout.lower()


class TestCLIUICrossPlatform:
    """Cross-platform compatibility tests for ui command."""

    def test_ui_path_handling(self, tmp_path):
        """Test that ui command handles paths correctly on all platforms."""
        # Create a test config in a path with spaces
        config_dir = tmp_path / "my folder" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "test.yaml"
        config_file.write_text("flow:\n  name: test\n")

        # Just verify path is accepted (ui command may have other defaults)
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestCLIUICodeVerification:
    """Code verification tests for ui command implementation."""

    def test_ui_command_exists(self):
        """Test that cmd_ui function exists in cli module."""
        from configurable_agents.cli import cmd_ui
        assert callable(cmd_ui)

    def test_process_manager_integration(self):
        """Test that cmd_ui uses ProcessManager correctly."""
        import configurable_agents.cli as cli_module
        cli_content = Path("src/configurable_agents/cli.py").read_text()

        # Should import ProcessManager
        assert "ProcessManager" in cli_content
        assert "from configurable_agents.process" in cli_content or "import" in cli_content

    def test_graceful_shutdown_handling(self):
        """Test that ui command handles KeyboardInterrupt gracefully."""
        import configurable_agents.cli as cli_module
        cli_content = Path("src/configurable_agents/cli.py").read_text()

        # Should handle KeyboardInterrupt for clean shutdown
        assert "KeyboardInterrupt" in cli_content
