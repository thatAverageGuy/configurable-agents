"""Integration tests for configurable-agents.

These tests run end-to-end workflows with real API calls to Google Gemini and Serper.
They are marked with @pytest.mark.integration and @pytest.mark.slow.

Run with:
    pytest tests/integration/ -v -m integration

Skip with:
    pytest -v -m "not integration"

Requirements:
- GOOGLE_API_KEY environment variable must be set
- SERPER_API_KEY environment variable must be set (for tool tests)
"""
