"""
Tests for prompt template resolution.
"""

import pytest
from pydantic import BaseModel

from configurable_agents.core import (
    TemplateResolutionError,
    resolve_prompt,
    extract_variables,
)
from configurable_agents.core.template import (
    resolve_variable,
    get_nested_value,
    _suggest_variable,
    _edit_distance,
)


# Test fixtures - State models


class SimpleState(BaseModel):
    """Simple state with flat fields"""

    topic: str
    score: int


class NestedMetadata(BaseModel):
    """Nested metadata"""

    author: str
    timestamp: int


class NestedState(BaseModel):
    """State with nested objects"""

    topic: str
    metadata: NestedMetadata


class DeeplyNestedFlags(BaseModel):
    """Deeply nested flags"""

    enabled: bool
    level: int


class DeeplyNestedMetadata(BaseModel):
    """Deeply nested metadata"""

    author: str
    flags: DeeplyNestedFlags


class DeeplyNestedState(BaseModel):
    """State with 3+ levels of nesting"""

    topic: str
    metadata: DeeplyNestedMetadata


# Test: resolve_prompt - Basic functionality


def test_resolve_prompt_simple_from_inputs():
    """Should resolve simple variable from inputs"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {"name": "Alice"}

    result = resolve_prompt("Hello {name}", inputs, state)

    assert result == "Hello Alice"


def test_resolve_prompt_simple_from_state():
    """Should resolve simple variable from state"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {}

    result = resolve_prompt("Topic: {topic}", inputs, state)

    assert result == "Topic: AI Safety"


def test_resolve_prompt_multiple_variables():
    """Should resolve multiple variables in template"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {"name": "Alice"}

    result = resolve_prompt(
        "Hello {name}, let's discuss {topic} (score: {score})",
        inputs,
        state,
    )

    assert result == "Hello Alice, let's discuss AI Safety (score: 95)"


def test_resolve_prompt_input_overrides_state():
    """Should prioritize inputs over state"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {"topic": "Robotics"}  # Override state.topic

    result = resolve_prompt("Topic: {topic}", inputs, state)

    assert result == "Topic: Robotics"


def test_resolve_prompt_nested_state_access():
    """Should resolve nested state variables"""
    state = NestedState(
        topic="AI Safety",
        metadata=NestedMetadata(author="Alice", timestamp=1234567890),
    )
    inputs = {}

    result = resolve_prompt("Author: {metadata.author}", inputs, state)

    assert result == "Author: Alice"


def test_resolve_prompt_deeply_nested_state():
    """Should resolve deeply nested state variables (3+ levels)"""
    state = DeeplyNestedState(
        topic="AI",
        metadata=DeeplyNestedMetadata(
            author="Bob",
            flags=DeeplyNestedFlags(enabled=True, level=5),
        ),
    )
    inputs = {}

    result = resolve_prompt(
        "Level: {metadata.flags.level}, Enabled: {metadata.flags.enabled}",
        inputs,
        state,
    )

    assert result == "Level: 5, Enabled: True"


def test_resolve_prompt_empty_template():
    """Should return empty string for empty template"""
    state = SimpleState(topic="AI", score=0)
    inputs = {}

    result = resolve_prompt("", inputs, state)

    assert result == ""


def test_resolve_prompt_no_variables():
    """Should return template unchanged if no variables"""
    state = SimpleState(topic="AI", score=0)
    inputs = {}

    result = resolve_prompt("This is a static prompt", inputs, state)

    assert result == "This is a static prompt"


def test_resolve_prompt_mixed_sources():
    """Should resolve variables from mixed sources (inputs and state)"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {"name": "Alice", "action": "analyze"}

    result = resolve_prompt(
        "{name}, please {action} the {topic} topic (score: {score})",
        inputs,
        state,
    )

    assert result == "Alice, please analyze the AI Safety topic (score: 95)"


def test_resolve_prompt_type_conversion():
    """Should convert non-string values to strings"""
    state = SimpleState(topic="AI", score=95)
    inputs = {"count": 42, "enabled": True}

    result = resolve_prompt(
        "Count: {count}, Score: {score}, Enabled: {enabled}",
        inputs,
        state,
    )

    assert result == "Count: 42, Score: 95, Enabled: True"


# Test: resolve_prompt - Error cases


def test_resolve_prompt_missing_variable():
    """Should raise error for missing variable"""
    state = SimpleState(topic="AI", score=95)
    inputs = {}

    with pytest.raises(TemplateResolutionError) as exc_info:
        resolve_prompt("Missing: {unknown}", inputs, state)

    assert "Variable 'unknown' not found" in str(exc_info.value)
    assert "Available inputs" in str(exc_info.value)
    assert "Available state fields" in str(exc_info.value)


def test_resolve_prompt_missing_nested_variable():
    """Should raise error for missing nested variable"""
    state = SimpleState(topic="AI", score=95)
    inputs = {}

    with pytest.raises(TemplateResolutionError) as exc_info:
        resolve_prompt("Missing: {metadata.author}", inputs, state)

    assert "Variable 'metadata.author' not found" in str(exc_info.value)


def test_resolve_prompt_error_with_suggestion():
    """Should suggest similar variable for typos"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {}

    with pytest.raises(TemplateResolutionError) as exc_info:
        resolve_prompt("Typo: {topik}", inputs, state)  # Should suggest 'topic'

    error = exc_info.value
    assert error.variable == "topik"
    assert error.suggestion == "topic"
    assert "Did you mean 'topic'?" in str(error)


# Test: extract_variables


def test_extract_variables_single():
    """Should extract single variable"""
    variables = extract_variables("Hello {name}")

    assert variables == {"name"}


def test_extract_variables_multiple():
    """Should extract multiple variables"""
    variables = extract_variables("Hello {name}, topic: {topic}, score: {score}")

    assert variables == {"name", "topic", "score"}


def test_extract_variables_nested():
    """Should extract nested variables"""
    variables = extract_variables("Author: {metadata.author}")

    assert variables == {"metadata.author"}


def test_extract_variables_none():
    """Should return empty set if no variables"""
    variables = extract_variables("Static text with no variables")

    assert variables == set()


def test_extract_variables_duplicates():
    """Should deduplicate repeated variables"""
    variables = extract_variables("{name} says hello to {name}")

    assert variables == {"name"}


def test_extract_variables_invalid_names():
    """Should ignore invalid variable names"""
    # Variables must start with letter/underscore
    variables = extract_variables("Invalid: {123invalid} {-invalid}")

    assert variables == set()


# Test: resolve_variable


def test_resolve_variable_from_inputs():
    """Should resolve variable from inputs"""
    state = SimpleState(topic="AI", score=0)
    inputs = {"name": "Alice"}

    value = resolve_variable("name", inputs, state)

    assert value == "Alice"


def test_resolve_variable_from_state():
    """Should resolve variable from state"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {}

    value = resolve_variable("topic", inputs, state)

    assert value == "AI Safety"


def test_resolve_variable_inputs_override():
    """Should prioritize inputs over state"""
    state = SimpleState(topic="AI", score=95)
    inputs = {"topic": "Robotics"}

    value = resolve_variable("topic", inputs, state)

    assert value == "Robotics"


def test_resolve_variable_nested():
    """Should resolve nested state variable"""
    state = NestedState(
        topic="AI",
        metadata=NestedMetadata(author="Bob", timestamp=123),
    )
    inputs = {}

    value = resolve_variable("metadata.author", inputs, state)

    assert value == "Bob"


def test_resolve_variable_not_found():
    """Should raise error if variable not found"""
    state = SimpleState(topic="AI", score=0)
    inputs = {}

    with pytest.raises(TemplateResolutionError):
        resolve_variable("unknown", inputs, state)


# Test: get_nested_value


def test_get_nested_value_simple():
    """Should get simple field from state"""
    state = SimpleState(topic="AI Safety", score=95)

    value = get_nested_value(state, "topic")

    assert value == "AI Safety"


def test_get_nested_value_one_level():
    """Should get nested field (1 level)"""
    state = NestedState(
        topic="AI",
        metadata=NestedMetadata(author="Alice", timestamp=123),
    )

    value = get_nested_value(state, "metadata.author")

    assert value == "Alice"


def test_get_nested_value_multiple_levels():
    """Should get deeply nested field (3+ levels)"""
    state = DeeplyNestedState(
        topic="AI",
        metadata=DeeplyNestedMetadata(
            author="Bob",
            flags=DeeplyNestedFlags(enabled=True, level=5),
        ),
    )

    value = get_nested_value(state, "metadata.flags.level")

    assert value == 5


def test_get_nested_value_from_dict():
    """Should get nested value from dict"""
    data = {"metadata": {"author": "Charlie"}}

    value = get_nested_value(data, "metadata.author")

    assert value == "Charlie"


def test_get_nested_value_missing_field():
    """Should raise AttributeError for missing field"""
    state = SimpleState(topic="AI", score=0)

    with pytest.raises(AttributeError) as exc_info:
        get_nested_value(state, "metadata.author")

    assert "State has no field 'metadata'" in str(exc_info.value)


def test_get_nested_value_invalid_type():
    """Should raise TypeError if cannot access further"""
    state = SimpleState(topic="AI", score=95)

    with pytest.raises(TypeError) as exc_info:
        get_nested_value(state, "topic.invalid")  # topic is str, can't access .invalid

    assert "Cannot access 'invalid'" in str(exc_info.value)


# Test: _suggest_variable


def test_suggest_variable_exact_match():
    """Should suggest exact match with different case"""
    suggestion = _suggest_variable("Topic", [], ["topic"])

    assert suggestion == "topic"


def test_suggest_variable_one_edit():
    """Should suggest variable with 1 edit distance"""
    suggestion = _suggest_variable("topik", ["topic"], [])

    assert suggestion == "topic"


def test_suggest_variable_two_edits():
    """Should suggest variable with 2 edit distance"""
    suggestion = _suggest_variable("topicc", ["topic"], [])

    assert suggestion == "topic"


def test_suggest_variable_too_far():
    """Should return None if edit distance > 2"""
    suggestion = _suggest_variable("completely_different", ["topic"], [])

    assert suggestion is None


def test_suggest_variable_no_candidates():
    """Should return None if no candidates"""
    suggestion = _suggest_variable("topic", [], [])

    assert suggestion is None


def test_suggest_variable_multiple_candidates():
    """Should suggest closest match"""
    suggestion = _suggest_variable("topik", ["topic", "score", "author"], [])

    assert suggestion == "topic"  # Closest match


# Test: _edit_distance


def test_edit_distance_identical():
    """Should return 0 for identical strings"""
    distance = _edit_distance("hello", "hello")

    assert distance == 0


def test_edit_distance_one_substitution():
    """Should return 1 for one character difference"""
    distance = _edit_distance("hello", "hallo")

    assert distance == 1


def test_edit_distance_one_insertion():
    """Should return 1 for one insertion"""
    distance = _edit_distance("hello", "helllo")

    assert distance == 1


def test_edit_distance_one_deletion():
    """Should return 1 for one deletion"""
    distance = _edit_distance("hello", "helo")

    assert distance == 1


def test_edit_distance_multiple_edits():
    """Should calculate correct distance for multiple edits"""
    distance = _edit_distance("kitten", "sitting")

    assert distance == 3  # k→s, e→i, insert g


def test_edit_distance_empty_strings():
    """Should handle empty strings"""
    assert _edit_distance("", "") == 0
    assert _edit_distance("hello", "") == 5
    assert _edit_distance("", "hello") == 5


# Test: Integration scenarios


def test_full_integration_article_prompt():
    """Integration: Resolve complex article writing prompt"""

    class ArticleState(BaseModel):
        topic: str
        target_audience: str
        word_count: int
        metadata: NestedMetadata

    state = ArticleState(
        topic="Machine Learning",
        target_audience="beginners",
        word_count=1000,
        metadata=NestedMetadata(author="Alice", timestamp=1234567890),
    )
    inputs = {"style": "educational"}

    template = (
        "Write a {style} article about {topic} for {target_audience}. "
        "Target length: {word_count} words. Author: {metadata.author}."
    )

    result = resolve_prompt(template, inputs, state)

    expected = (
        "Write a educational article about Machine Learning for beginners. "
        "Target length: 1000 words. Author: Alice."
    )
    assert result == expected


def test_full_integration_error_recovery():
    """Integration: Error with helpful suggestions"""
    state = SimpleState(topic="AI Safety", score=95)
    inputs = {}

    # Typo: 'topik' should suggest 'topic'
    with pytest.raises(TemplateResolutionError) as exc_info:
        resolve_prompt("Analyze {topik}", inputs, state)

    error = exc_info.value
    assert "topik" in str(error)
    assert "Did you mean 'topic'?" in str(error)
    assert "Available inputs" in str(error)
    assert "Available state fields" in str(error)
