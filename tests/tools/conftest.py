"""Pytest configuration for tools tests."""

import os
import tempfile


def pytest_configure(config):
    """Configure temp directory as allowed for file tool tests."""
    # Add temp directory to allowed paths for tests
    temp_dir = tempfile.gettempdir()
    current_allowed = os.getenv("ALLOWED_PATHS", "")
    if current_allowed:
        os.environ["ALLOWED_PATHS"] = f"{current_allowed},{temp_dir},{os.getcwd()}"
    else:
        os.environ["ALLOWED_PATHS"] = f"{temp_dir},{os.getcwd()}"
