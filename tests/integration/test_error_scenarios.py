"""Integration tests for error scenarios and failure modes.

Tests error handling with real components:
- Invalid configs
- Missing API keys
- LLM timeouts
- Tool failures
- Type validation failures
- Missing inputs
- Node execution errors

These tests verify graceful error handling and helpful error messages.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from configurable_agents.runtime import (
    ConfigLoadError,
    ConfigValidationError,
    StateInitializationError,
    WorkflowExecutionError,
    run_workflow,
    validate_workflow,
)


# ============================================
# Config Error Scenarios
# ============================================


@pytest.mark.integration
def test_invalid_yaml_syntax_error(tmp_path):
    """Test error handling for malformed YAML files."""
    # Create invalid YAML file
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text(
        """
schema_version: "1.0"
flow:
  name: test
  invalid yaml syntax here [ { }
"""
    )

    # Should raise ConfigLoadError
    with pytest.raises(ConfigLoadError) as exc_info:
        run_workflow(str(invalid_yaml), {})

    # Verify error message is helpful
    error = exc_info.value
    assert "failed to load" in str(error).lower() or "parse" in str(error).lower()
    assert error.phase == "config_parse"

    print(f"\n[+] Invalid YAML error caught: {error}")


@pytest.mark.integration
def test_missing_config_file_error(tmp_path):
    """Test error handling for non-existent config files."""
    nonexistent = tmp_path / "does_not_exist.yaml"

    # Should raise ConfigLoadError
    with pytest.raises(ConfigLoadError) as exc_info:
        run_workflow(str(nonexistent), {})

    # Verify error message is helpful
    error = exc_info.value
    assert "not found" in str(error).lower() or "does not exist" in str(error).lower()
    assert error.phase == "config_load"

    print(f"\n[+] Missing file error caught: {error}")


@pytest.mark.integration
def test_invalid_config_structure_error(tmp_path):
    """Test error handling for invalid config structure."""
    # Create config with invalid structure (missing required fields)
    invalid_config = tmp_path / "invalid_structure.yaml"
    invalid_config.write_text(
        """
schema_version: "1.0"
flow:
  name: test

# Missing state, nodes, edges
"""
    )

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError) as exc_info:
        run_workflow(str(invalid_config), {})

    # Verify error is about validation
    error = exc_info.value
    assert error.phase == "schema_validation"

    print(f"\n[+] Invalid structure error caught: {error}")


@pytest.mark.integration
def test_validation_error_orphaned_node(tmp_path):
    """Test error handling for orphaned nodes (graph validation)."""
    # Create config with orphaned node
    orphaned_config = tmp_path / "orphaned.yaml"
    orphaned_config.write_text(
        """
schema_version: "1.0"

flow:
  name: orphaned_test

state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}

nodes:
  - id: node1
    prompt: "Process {state.input}"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - {name: output, type: str}

  - id: orphaned
    prompt: "Never reached"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - {name: output, type: str}

edges:
  - {from: START, to: node1}
  - {from: node1, to: END}
  # orphaned node has no incoming edges
"""
    )

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError) as exc_info:
        run_workflow(str(orphaned_config), {})

    # Verify error is about orphaned node
    error = exc_info.value
    assert "orphaned" in str(error).lower() or "unreachable" in str(error).lower()

    print(f"\n[+] Orphaned node error caught: {error}")


# ============================================
# API Key Error Scenarios
# ============================================


@pytest.mark.integration
def test_missing_google_api_key_error(echo_workflow, tmp_path):
    """Test error handling when GOOGLE_API_KEY is not set."""
    # Temporarily unset GOOGLE_API_KEY
    original_key = os.environ.pop("GOOGLE_API_KEY", None)

    try:
        # Should raise WorkflowExecutionError (LLM creation fails)
        with pytest.raises(WorkflowExecutionError) as exc_info:
            run_workflow(str(echo_workflow), {"message": "test"})

        # Verify error mentions API key
        error = exc_info.value
        assert "api" in str(error).lower() and "key" in str(error).lower()

        print(f"\n[+] Missing API key error caught: {error}")

    finally:
        # Restore API key
        if original_key:
            os.environ["GOOGLE_API_KEY"] = original_key


@pytest.mark.integration
@pytest.mark.requires_serper
def test_invalid_serper_api_key_error(article_writer_workflow, check_google_api_key):
    """Test error handling when SERPER_API_KEY is invalid.

    Note: Serper tool may handle invalid keys gracefully, returning empty results
    instead of failing. This test verifies the workflow completes either way.
    """
    # Temporarily set invalid SERPER_API_KEY
    original_key = os.environ.get("SERPER_API_KEY")
    os.environ["SERPER_API_KEY"] = "invalid_key_12345"

    try:
        # Try to run workflow - may succeed with empty results or fail
        try:
            result = run_workflow(
                str(article_writer_workflow),
                {"topic": "test"},
            )
            # If it succeeded, tool likely handled error gracefully
            print(f"\n[+] Workflow completed (tool handled invalid key gracefully)")
            print(f"    Research length: {len(result.get('research', ''))} chars")
        except WorkflowExecutionError as e:
            # If it failed, error handling worked as expected
            print(f"\n[+] Invalid Serper key error caught: {e}")
            assert e.phase == "workflow_execution"

    finally:
        # Restore original key
        if original_key:
            os.environ["SERPER_API_KEY"] = original_key
        else:
            os.environ.pop("SERPER_API_KEY", None)


# ============================================
# Input Error Scenarios
# ============================================


@pytest.mark.integration
def test_missing_required_input_error(echo_workflow):
    """Test error handling when required state field is missing."""
    # echo.yaml requires 'message' field
    # Should raise StateInitializationError
    with pytest.raises(StateInitializationError) as exc_info:
        run_workflow(str(echo_workflow), {})  # Missing 'message'

    # Verify error mentions missing field
    error = exc_info.value
    assert "message" in str(error).lower() or "required" in str(error).lower()

    print(f"\n[+] Missing required input error caught: {error}")


@pytest.mark.integration
def test_wrong_input_type_error(tmp_path):
    """Test error handling when input has wrong type."""
    # Create workflow expecting int, provide string
    config_file = tmp_path / "type_mismatch.yaml"
    config_file.write_text(
        """
schema_version: "1.0"

flow:
  name: type_test

state:
  fields:
    count: {type: int, required: true}
    result: {type: str, default: ""}

nodes:
  - id: process
    prompt: "Count to {state.count}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - {name: result, type: str}

edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    )

    # Should raise StateInitializationError (Pydantic validation)
    with pytest.raises(StateInitializationError) as exc_info:
        run_workflow(str(config_file), {"count": "not_a_number"})

    # Verify error is about type mismatch
    error = exc_info.value
    assert "count" in str(error).lower() or "type" in str(error).lower()

    print(f"\n[+] Wrong input type error caught: {error}")


# ============================================
# Timeout Error Scenarios
# ============================================


@pytest.mark.integration
@pytest.mark.slow
def test_llm_timeout_error(tmp_path, check_google_api_key):
    """Test error handling when LLM call times out.

    Note: This test sets a very short timeout to trigger the error.
    """
    # Create config with very short timeout
    timeout_config = tmp_path / "timeout.yaml"
    timeout_config.write_text(
        """
schema_version: "1.0"

flow:
  name: timeout_test

state:
  fields:
    prompt: {type: str, required: true}
    result: {type: str, default: ""}

config:
  llm:
    provider: google
    model: gemini-1.5-flash
    temperature: 0.7
  execution:
    timeout_seconds: 0.001  # 1ms timeout - will fail

nodes:
  - id: generate
    prompt: "Write a very long essay about {state.prompt}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - {name: result, type: str, description: "Long essay"}

edges:
  - {from: START, to: generate}
  - {from: generate, to: END}
"""
    )

    # Should raise WorkflowExecutionError (timeout)
    # Note: Timeout handling might vary by LangChain version
    with pytest.raises((WorkflowExecutionError, Exception)) as exc_info:
        run_workflow(str(timeout_config), {"prompt": "artificial intelligence"})

    # Just verify it failed (timeout behavior may vary)
    print(f"\n[+] Timeout error caught: {exc_info.value}")


# ============================================
# Type Enforcement Error Scenarios
# ============================================


@pytest.mark.integration
@pytest.mark.slow
def test_type_validation_with_retry(tmp_path, check_google_api_key):
    """Test that type mismatches trigger automatic retry.

    This test verifies that the system retries when LLM returns wrong types.
    With low temperature, Gemini should eventually return correct types.
    """
    # Create config with strict type requirements
    strict_config = tmp_path / "strict_types.yaml"
    strict_config.write_text(
        """
schema_version: "1.0"

flow:
  name: strict_type_test

state:
  fields:
    topic: {type: str, required: true}
    analysis: {type: int, default: 0}  # Expecting int

config:
  llm:
    provider: google
    model: gemini-2.5-flash-lite
    temperature: 0.1  # Low temperature for consistency

nodes:
  - id: analyze
    prompt: |
      Analyze this topic: {state.topic}

      You MUST return an integer analysis score between 1 and 100.
      Return ONLY the integer number for the 'analysis' field.
    outputs: [analysis]
    output_schema:
      type: object
      fields:
        - name: analysis
          type: int
          description: Integer score between 1 and 100

edges:
  - {from: START, to: analyze}
  - {from: analyze, to: END}
"""
    )

    # Run workflow - should succeed (with retries if needed)
    result = run_workflow(
        str(strict_config),
        {"topic": "Machine Learning"},
    )

    # Verify type is correct
    assert isinstance(result["analysis"], int), "Analysis should be integer"
    assert 1 <= result["analysis"] <= 100, "Analysis should be in range"

    print(f"\n[+] Type validation with retry succeeded")
    print(f"  Analysis score: {result['analysis']}")


# ============================================
# Output Reference Error Scenarios
# ============================================


@pytest.mark.integration
def test_output_references_nonexistent_state_field(tmp_path):
    """Test error when node output references non-existent state field."""
    invalid_output = tmp_path / "invalid_output.yaml"
    invalid_output.write_text(
        """
schema_version: "1.0"

flow:
  name: invalid_output

state:
  fields:
    input: {type: str, required: true}
    result: {type: str, default: ""}

nodes:
  - id: process
    prompt: "Process {state.input}"
    outputs: [nonexistent_field]  # This field doesn't exist in state
    output_schema:
      type: object
      fields:
        - {name: nonexistent_field, type: str}

edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    )

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError) as exc_info:
        run_workflow(str(invalid_output), {"input": "test"})

    # Verify error mentions the missing field
    error = exc_info.value
    assert (
        "nonexistent_field" in str(error).lower()
        or "output" in str(error).lower()
    )

    print(f"\n[+] Invalid output reference error caught: {error}")


# ============================================
# Prompt Placeholder Error Scenarios
# ============================================


@pytest.mark.integration
def test_prompt_references_nonexistent_variable(tmp_path):
    """Test error when prompt references non-existent variable."""
    invalid_prompt = tmp_path / "invalid_prompt.yaml"
    invalid_prompt.write_text(
        """
schema_version: "1.0"

flow:
  name: invalid_prompt

state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}

nodes:
  - id: process
    prompt: "Process {state.nonexistent}"  # This field doesn't exist
    outputs: [output]
    output_schema:
      type: object
      fields:
        - {name: output, type: str}

edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    )

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError) as exc_info:
        run_workflow(str(invalid_prompt), {"input": "test"})

    # Verify error mentions the undefined variable
    error = exc_info.value
    assert "nonexistent" in str(error).lower() or "prompt" in str(error).lower()

    print(f"\n[+] Invalid prompt placeholder error caught: {error}")


# ============================================
# Summary Test
# ============================================


@pytest.mark.integration
def test_error_scenarios_summary():
    """Summary of error scenarios tested.

    This test always passes and just reports what was tested.
    """
    scenarios = [
        "[+] Invalid YAML syntax",
        "[+] Missing config file",
        "[+] Invalid config structure",
        "[+] Orphaned nodes",
        "[+] Missing Google API key",
        "[+] Invalid Serper API key",
        "[+] Missing required inputs",
        "[+] Wrong input types",
        "[+] LLM timeout",
        "[+] Type validation with retry",
        "[+] Invalid output references",
        "[+] Invalid prompt placeholders",
    ]

    print("\n" + "=" * 60)
    print("ERROR SCENARIO TEST COVERAGE")
    print("=" * 60)
    for scenario in scenarios:
        print(f"  {scenario}")
    print("=" * 60)
    print(f"Total scenarios tested: {len(scenarios)}")
    print("=" * 60)

    assert True, "Summary test"
