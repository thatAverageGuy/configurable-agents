"""Pytest configuration and shared fixtures"""

import pytest


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
