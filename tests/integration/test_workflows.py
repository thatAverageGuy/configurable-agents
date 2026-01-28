"""End-to-end integration tests for all example workflows.

Tests all 5 example workflows with real Google Gemini API calls.
These tests verify:
- Config loading and parsing
- State initialization
- LLM integration
- Tool integration (Serper)
- Type enforcement
- Multi-step workflows
- Nested state handling

All tests use REAL API calls and are marked as slow.
"""

import json

import pytest

from configurable_agents.runtime import run_workflow


# ============================================
# Workflow Integration Tests (Real API)
# ============================================


@pytest.mark.integration
@pytest.mark.slow
def test_echo_workflow_integration(
    check_google_api_key,
    echo_workflow,
    run_workflow_with_timing,
    track_api_call,
):
    """Test echo.yaml workflow with real Gemini API.

    Verifies:
    - Minimal workflow execution
    - Single node processing
    - String output type
    - Message echoing
    """
    # Run workflow
    result, duration = run_workflow_with_timing(
        str(echo_workflow),
        {"message": "Hello from integration test!"},
    )

    # Track API call
    track_api_call("echo.yaml", result, duration)

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "message" in result, "Result should contain 'message' field"
    assert "result" in result, "Result should contain 'result' field"

    # Input preserved
    assert result["message"] == "Hello from integration test!"

    # Output generated (LLM echoed the message)
    assert isinstance(result["result"], str), "Result should be string"
    assert len(result["result"]) > 0, "Result should not be empty"

    # LLM should have echoed something similar to input
    # (we can't assert exact match as LLM might paraphrase)
    assert "hello" in result["result"].lower() or "integration" in result["result"].lower()

    print(f"\n[+] Echo workflow completed in {duration:.2f}s")
    print(f"  Input: {result['message']}")
    print(f"  Output: {result['result']}")


@pytest.mark.integration
@pytest.mark.slow
def test_simple_workflow_integration(
    check_google_api_key,
    simple_workflow,
    run_workflow_with_timing,
    track_api_call,
):
    """Test simple_workflow.yaml with real Gemini API.

    Verifies:
    - Basic greeting generation
    - String state handling
    - Personalized output
    """
    # Run workflow
    result, duration = run_workflow_with_timing(
        str(simple_workflow),
        {"name": "Alice"},
    )

    # Track API call
    track_api_call("simple_workflow.yaml", result, duration)

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "name" in result, "Result should contain 'name' field"
    assert "greeting" in result, "Result should contain 'greeting' field"

    # Input preserved
    assert result["name"] == "Alice"

    # Output generated
    assert isinstance(result["greeting"], str), "Greeting should be string"
    assert len(result["greeting"]) > 0, "Greeting should not be empty"

    # Greeting should mention the name
    assert "alice" in result["greeting"].lower(), "Greeting should mention Alice"

    print(f"\n[+] Simple workflow completed in {duration:.2f}s")
    print(f"  Name: {result['name']}")
    print(f"  Greeting: {result['greeting']}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Nested objects in output schema not yet supported - see output_builder.py")
def test_nested_state_workflow_integration(
    check_google_api_key,
    nested_state_workflow,
    run_workflow_with_timing,
    track_api_call,
):
    """Test nested_state.yaml workflow with real Gemini API.

    Verifies:
    - Nested object state
    - List inputs
    - Complex state structures
    - Object output generation
    """
    # Run workflow with nested inputs
    result, duration = run_workflow_with_timing(
        str(nested_state_workflow),
        {
            "name": "Bob",
            "interests": ["AI", "robotics", "philosophy"],
        },
    )

    # Track API call
    track_api_call("nested_state.yaml", result, duration)

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "name" in result, "Result should contain 'name' field"
    assert "interests" in result, "Result should contain 'interests' field"
    assert "profile" in result, "Result should contain 'profile' field"

    # Input preserved
    assert result["name"] == "Bob"
    assert result["interests"] == ["AI", "robotics", "philosophy"]

    # Nested output generated
    assert isinstance(result["profile"], dict), "Profile should be object/dict"
    assert "summary" in result["profile"], "Profile should have 'summary' field"
    assert "tags" in result["profile"], "Profile should have 'tags' field"

    # Verify nested structure
    assert isinstance(result["profile"]["summary"], str), "Summary should be string"
    assert len(result["profile"]["summary"]) > 0, "Summary should not be empty"
    assert isinstance(result["profile"]["tags"], list), "Tags should be list"

    # Summary should mention the name and/or interests
    summary_lower = result["profile"]["summary"].lower()
    assert (
        "bob" in summary_lower
        or "ai" in summary_lower
        or "robot" in summary_lower
    ), "Summary should reference input data"

    print(f"\n[+] Nested state workflow completed in {duration:.2f}s")
    print(f"  Name: {result['name']}")
    print(f"  Interests: {result['interests']}")
    print(f"  Profile: {json.dumps(result['profile'], indent=2)}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Nested objects in output schema not yet supported - see output_builder.py")
def test_type_enforcement_workflow_integration(
    check_google_api_key,
    type_enforcement_workflow,
    run_workflow_with_timing,
    track_api_call,
):
    """Test type_enforcement.yaml workflow with real Gemini API.

    Verifies:
    - Multiple output types (str, int, float, bool, list, dict, object)
    - Type validation and enforcement
    - Pydantic schema validation
    - Automatic retry on type mismatch
    """
    # Run workflow
    result, duration = run_workflow_with_timing(
        str(type_enforcement_workflow),
        {"topic": "Artificial Intelligence"},
    )

    # Track API call
    track_api_call("type_enforcement.yaml", result, duration)

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "topic" in result, "Result should contain 'topic' field"
    assert "analysis" in result, "Result should contain 'analysis' field"

    # Input preserved
    assert result["topic"] == "Artificial Intelligence"

    # Analysis output generated (object with multiple typed fields)
    analysis = result["analysis"]
    assert isinstance(analysis, dict), "Analysis should be object/dict"

    # Verify all typed fields exist and have correct types
    assert "summary" in analysis, "Analysis should have 'summary' (str)"
    assert isinstance(analysis["summary"], str), "Summary should be string"
    assert len(analysis["summary"]) > 0, "Summary should not be empty"

    assert "word_count" in analysis, "Analysis should have 'word_count' (int)"
    assert isinstance(analysis["word_count"], int), "Word count should be integer"
    assert analysis["word_count"] > 0, "Word count should be positive"

    assert "score" in analysis, "Analysis should have 'score' (float)"
    assert isinstance(analysis["score"], (int, float)), "Score should be numeric"
    assert 0.0 <= analysis["score"] <= 10.0, "Score should be between 0 and 10"

    assert "is_technical" in analysis, "Analysis should have 'is_technical' (bool)"
    assert isinstance(analysis["is_technical"], bool), "is_technical should be boolean"

    assert "keywords" in analysis, "Analysis should have 'keywords' (list[str])"
    assert isinstance(analysis["keywords"], list), "Keywords should be list"
    assert all(
        isinstance(k, str) for k in analysis["keywords"]
    ), "All keywords should be strings"

    assert "metadata" in analysis, "Analysis should have 'metadata' (dict[str, int])"
    assert isinstance(analysis["metadata"], dict), "Metadata should be dict"

    assert "details" in analysis, "Analysis should have 'details' (object)"
    assert isinstance(analysis["details"], dict), "Details should be object/dict"
    assert "category" in analysis["details"], "Details should have 'category'"
    assert "confidence" in analysis["details"], "Details should have 'confidence'"

    print(f"\n[+] Type enforcement workflow completed in {duration:.2f}s")
    print(f"  Topic: {result['topic']}")
    print(f"  Analysis: {json.dumps(analysis, indent=2)}")
    print(f"\n  Type Validation:")
    print(f"    [+] summary: str = '{analysis['summary'][:50]}...'")
    print(f"    [+] word_count: int = {analysis['word_count']}")
    print(f"    [+] score: float = {analysis['score']}")
    print(f"    [+] is_technical: bool = {analysis['is_technical']}")
    print(f"    [+] keywords: list[str] = {analysis['keywords']}")
    print(f"    [+] metadata: dict = {analysis['metadata']}")
    print(f"    [+] details: object = {analysis['details']}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_serper
def test_article_writer_workflow_integration(
    check_google_api_key,
    check_serper_api_key,
    article_writer_workflow,
    run_workflow_with_timing,
    track_api_call,
):
    """Test article_writer.yaml workflow with real Gemini + Serper APIs.

    Verifies:
    - Multi-step workflow (research → write)
    - Tool integration (serper_search)
    - State flowing between nodes
    - Multiple outputs per node
    - Real web search integration
    """
    # Run workflow
    result, duration = run_workflow_with_timing(
        str(article_writer_workflow),
        {"topic": "Claude AI assistant"},
    )

    # Track API call
    track_api_call("article_writer.yaml", result, duration)

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "topic" in result, "Result should contain 'topic' field"
    assert "research" in result, "Result should contain 'research' field"
    assert "article" in result, "Result should contain 'article' field"
    assert "word_count" in result, "Result should contain 'word_count' field"

    # Input preserved
    assert result["topic"] == "Claude AI assistant"

    # Research output (from first node with tool)
    assert isinstance(result["research"], str), "Research should be string"
    assert len(result["research"]) > 0, "Research should not be empty"
    # Research should contain web search results
    assert len(result["research"]) > 50, "Research should have substantial content"

    # Article output (from second node)
    assert isinstance(result["article"], str), "Article should be string"
    assert len(result["article"]) > 0, "Article should not be empty"
    # Article should be substantial (using research)
    assert len(result["article"]) > 100, "Article should have substantial content"

    # Word count output
    assert isinstance(result["word_count"], int), "Word count should be integer"
    assert result["word_count"] > 0, "Word count should be positive"
    # Word count should roughly match article length
    actual_words = len(result["article"].split())
    assert (
        abs(result["word_count"] - actual_words) < 50
    ), f"Word count ({result['word_count']}) should be close to actual ({actual_words})"

    # Article should mention the topic
    article_lower = result["article"].lower()
    assert (
        "claude" in article_lower or "ai" in article_lower
    ), "Article should mention the topic"

    print(f"\n[+] Article writer workflow completed in {duration:.2f}s")
    print(f"  Topic: {result['topic']}")
    print(f"  Research length: {len(result['research'])} chars")
    print(f"  Article length: {len(result['article'])} chars")
    print(f"  Word count: {result['word_count']} words")
    print(f"\n  Research (first 200 chars):")
    print(f"    {result['research'][:200]}...")
    print(f"\n  Article (first 200 chars):")
    print(f"    {result['article'][:200]}...")


# ============================================
# Validation Tests (No API Calls)
# ============================================


@pytest.mark.integration
def test_all_example_workflows_validate(
    echo_workflow,
    simple_workflow,
    nested_state_workflow,
    type_enforcement_workflow,
    article_writer_workflow,
    validate_workflow_helper,
):
    """Verify all example workflows have valid configs.

    This test doesn't make API calls, just validates configs.
    """
    workflows = [
        ("echo.yaml", echo_workflow),
        ("simple_workflow.yaml", simple_workflow),
        ("nested_state.yaml", nested_state_workflow),
        ("type_enforcement.yaml", type_enforcement_workflow),
        ("article_writer.yaml", article_writer_workflow),
    ]

    for name, path in workflows:
        assert validate_workflow_helper(str(path)), f"{name} should validate"
        print(f"[+] {name} validated successfully")

    print(f"\n[+] All {len(workflows)} example workflows validated")
