"""Pytest configuration and shared fixtures"""

import os
from pathlib import Path

import pytest


# Load .env file for integration tests
def pytest_configure(config):
    """Load environment variables from .env file before running tests."""
    # Try to load .env from project root
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"\n[+] Loaded environment from: {env_file}")
    else:
        print(f"\n[!] No .env file found at: {env_file}")


@pytest.fixture
def sample_config():
    """Sample minimal workflow configuration for testing"""
    return {
        "schema_version": "1.0",
        "flow": {
            "name": "test_workflow",
            "description": "Test workflow",
        },
        "state": {
            "fields": {
                "input": {"type": "str", "required": True},
                "output": {"type": "str", "default": ""},
            }
        },
        "nodes": [
            {
                "id": "process",
                "prompt": "Process: {state.input}",
                "output_schema": {
                    "type": "object",
                    "fields": [
                        {"name": "output", "type": "str", "description": "Processed output"}
                    ],
                },
                "outputs": ["output"],
            }
        ],
        "edges": [
            {"from": "START", "to": "process"},
            {"from": "process", "to": "END"},
        ],
    }
