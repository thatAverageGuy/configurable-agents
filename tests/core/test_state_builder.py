"""Tests for state builder (dynamic Pydantic model generation)."""

import pytest
from pydantic import ValidationError

from configurable_agents.config.schema import StateFieldConfig, StateSchema
from configurable_agents.core.state_builder import StateBuilderError, build_state_model


class TestBasicTypes:
    """Test state models with basic types."""

    def test_single_string_field(self):
        state_config = StateSchema(
            fields={"topic": StateFieldConfig(type="str", required=True)}
        )
        StateModel = build_state_model(state_config)

        # Create instance
        state = StateModel(topic="AI Safety")
        assert state.topic == "AI Safety"

    def test_multiple_basic_types(self):
        state_config = StateSchema(
            fields={
                "name": StateFieldConfig(type="str", required=True),
                "age": StateFieldConfig(type="int", required=True),
                "score": StateFieldConfig(type="float", required=True),
                "active": StateFieldConfig(type="bool", required=True),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(name="Alice", age=30, score=95.5, active=True)
        assert state.name == "Alice"
        assert state.age == 30
        assert state.score == 95.5
        assert state.active is True

    def test_string_validation(self):
        state_config = StateSchema(
            fields={"name": StateFieldConfig(type="str", required=True)}
        )
        StateModel = build_state_model(state_config)

        # Wrong type should fail
        with pytest.raises(ValidationError):
            StateModel(name=123)

    def test_int_validation(self):
        state_config = StateSchema(
            fields={"count": StateFieldConfig(type="int", required=True)}
        )
        StateModel = build_state_model(state_config)

        # Wrong type should fail
        with pytest.raises(ValidationError):
            StateModel(count="not_an_int")


class TestCollectionTypes:
    """Test state models with collection types."""

    def test_generic_list(self):
        state_config = StateSchema(
            fields={"items": StateFieldConfig(type="list", required=True)}
        )
        StateModel = build_state_model(state_config)

        state = StateModel(items=[1, 2, "three", True])
        assert state.items == [1, 2, "three", True]

    def test_typed_list_str(self):
        state_config = StateSchema(
            fields={"tags": StateFieldConfig(type="list[str]", required=True)}
        )
        StateModel = build_state_model(state_config)

        state = StateModel(tags=["python", "ai", "ml"])
        assert state.tags == ["python", "ai", "ml"]

    def test_typed_list_int(self):
        state_config = StateSchema(
            fields={"numbers": StateFieldConfig(type="list[int]", required=True)}
        )
        StateModel = build_state_model(state_config)

        state = StateModel(numbers=[1, 2, 3, 4, 5])
        assert state.numbers == [1, 2, 3, 4, 5]

    def test_generic_dict(self):
        state_config = StateSchema(
            fields={"data": StateFieldConfig(type="dict", required=True)}
        )
        StateModel = build_state_model(state_config)

        state = StateModel(data={"key": "value", "count": 42})
        assert state.data == {"key": "value", "count": 42}

    def test_typed_dict(self):
        state_config = StateSchema(
            fields={"scores": StateFieldConfig(type="dict[str, int]", required=True)}
        )
        StateModel = build_state_model(state_config)

        state = StateModel(scores={"math": 95, "science": 88})
        assert state.scores == {"math": 95, "science": 88}


class TestRequiredFields:
    """Test required field validation."""

    def test_required_field_must_be_provided(self):
        state_config = StateSchema(
            fields={"topic": StateFieldConfig(type="str", required=True)}
        )
        StateModel = build_state_model(state_config)

        # Missing required field should fail
        with pytest.raises(ValidationError):
            StateModel()

    def test_multiple_required_fields(self):
        state_config = StateSchema(
            fields={
                "field1": StateFieldConfig(type="str", required=True),
                "field2": StateFieldConfig(type="int", required=True),
            }
        )
        StateModel = build_state_model(state_config)

        # Missing any required field should fail
        with pytest.raises(ValidationError):
            StateModel(field1="value")

        # All required fields provided should work
        state = StateModel(field1="value", field2=42)
        assert state.field1 == "value"
        assert state.field2 == 42


class TestOptionalFields:
    """Test optional field behavior."""

    def test_optional_field_defaults_to_none(self):
        state_config = StateSchema(
            fields={
                "required_field": StateFieldConfig(type="str", required=True),
                "optional_field": StateFieldConfig(type="str", required=False),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(required_field="value")
        assert state.required_field == "value"
        assert state.optional_field is None

    def test_optional_field_can_be_provided(self):
        state_config = StateSchema(
            fields={
                "required_field": StateFieldConfig(type="str", required=True),
                "optional_field": StateFieldConfig(type="int", required=False),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(required_field="value", optional_field=42)
        assert state.required_field == "value"
        assert state.optional_field == 42


class TestDefaultValues:
    """Test default value behavior."""

    def test_default_value_used_when_not_provided(self):
        state_config = StateSchema(
            fields={
                "name": StateFieldConfig(type="str", required=True),
                "score": StateFieldConfig(type="int", default=0),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(name="Alice")
        assert state.name == "Alice"
        assert state.score == 0

    def test_default_value_can_be_overridden(self):
        state_config = StateSchema(
            fields={
                "name": StateFieldConfig(type="str", required=True),
                "score": StateFieldConfig(type="int", default=0),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(name="Alice", score=95)
        assert state.name == "Alice"
        assert state.score == 95

    def test_multiple_defaults(self):
        state_config = StateSchema(
            fields={
                "name": StateFieldConfig(type="str", required=True),
                "score": StateFieldConfig(type="int", default=0),
                "active": StateFieldConfig(type="bool", default=True),
                "tags": StateFieldConfig(type="list", default=[]),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(name="Alice")
        assert state.score == 0
        assert state.active is True
        assert state.tags == []


class TestFieldDescriptions:
    """Test field descriptions are preserved."""

    def test_field_with_description(self):
        state_config = StateSchema(
            fields={
                "topic": StateFieldConfig(
                    type="str", required=True, description="The research topic"
                )
            }
        )
        StateModel = build_state_model(state_config)

        # Check description is in model schema
        schema = StateModel.model_json_schema()
        assert "topic" in schema["properties"]
        assert schema["properties"]["topic"]["description"] == "The research topic"

    def test_multiple_field_descriptions(self):
        state_config = StateSchema(
            fields={
                "name": StateFieldConfig(
                    type="str", required=True, description="User name"
                ),
                "age": StateFieldConfig(
                    type="int", required=True, description="User age in years"
                ),
            }
        )
        StateModel = build_state_model(state_config)

        schema = StateModel.model_json_schema()
        assert schema["properties"]["name"]["description"] == "User name"
        assert schema["properties"]["age"]["description"] == "User age in years"


class TestNestedObjects:
    """Test nested object types (1 level deep)."""

    def test_simple_nested_object(self):
        state_config = StateSchema(
            fields={
                "user": StateFieldConfig(
                    type="object",
                    required=True,
                    schema={"name": "str", "age": "int"},
                )
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(user={"name": "Alice", "age": 30})
        assert state.user.name == "Alice"
        assert state.user.age == 30

    def test_nested_object_with_field_configs(self):
        """Test nested schema with full StateFieldConfig format."""
        state_config = StateSchema(
            fields={
                "metadata": StateFieldConfig(
                    type="object",
                    required=True,
                    schema={
                        "author": {"type": "str", "required": True},
                        "version": {"type": "int", "default": 1},
                    },
                )
            }
        )
        StateModel = build_state_model(state_config)

        # With all fields
        state = StateModel(metadata={"author": "Bob", "version": 2})
        assert state.metadata.author == "Bob"
        assert state.metadata.version == 2

        # With only required field (version should default to 1)
        state2 = StateModel(metadata={"author": "Alice"})
        assert state2.metadata.author == "Alice"
        assert state2.metadata.version == 1

    def test_mixed_flat_and_nested(self):
        state_config = StateSchema(
            fields={
                "title": StateFieldConfig(type="str", required=True),
                "metadata": StateFieldConfig(
                    type="object",
                    required=True,
                    schema={"author": "str", "timestamp": "int"},
                ),
                "score": StateFieldConfig(type="int", default=0),
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(
            title="Article",
            metadata={"author": "Alice", "timestamp": 1234567890},
        )
        assert state.title == "Article"
        assert state.metadata.author == "Alice"
        assert state.metadata.timestamp == 1234567890
        assert state.score == 0


class TestDeeplyNestedObjects:
    """Test deeply nested objects (3+ levels)."""

    def test_three_level_nesting(self):
        state_config = StateSchema(
            fields={
                "data": StateFieldConfig(
                    type="object",
                    required=True,
                    schema={
                        "level1": {
                            "type": "object",
                            "required": True,
                            "schema": {
                                "level2": {
                                    "type": "object",
                                    "required": True,
                                    "schema": {"value": "str"},
                                }
                            },
                        }
                    },
                )
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(
            data={"level1": {"level2": {"value": "deep"}}}
        )
        assert state.data.level1.level2.value == "deep"

    def test_deeply_nested_with_mixed_types(self):
        state_config = StateSchema(
            fields={
                "config": StateFieldConfig(
                    type="object",
                    required=True,
                    schema={
                        "name": "str",
                        "settings": {
                            "type": "object",
                            "required": True,
                            "schema": {
                                "enabled": "bool",
                                "params": {
                                    "type": "object",
                                    "required": True,
                                    "schema": {
                                        "timeout": "int",
                                        "retries": "int",
                                    },
                                },
                            },
                        },
                    },
                )
            }
        )
        StateModel = build_state_model(state_config)

        state = StateModel(
            config={
                "name": "test",
                "settings": {
                    "enabled": True,
                    "params": {"timeout": 30, "retries": 3},
                },
            }
        )
        assert state.config.name == "test"
        assert state.config.settings.enabled is True
        assert state.config.settings.params.timeout == 30
        assert state.config.settings.params.retries == 3


class TestComplexCombinations:
    """Test complex combinations of all features."""

    def test_all_features_combined(self):
        """Kitchen sink test with all type system features."""
        state_config = StateSchema(
            fields={
                # Basic required
                "topic": StateFieldConfig(type="str", required=True),
                # Basic with default
                "score": StateFieldConfig(type="int", default=0),
                # Optional
                "notes": StateFieldConfig(type="str", required=False),
                # Collections
                "tags": StateFieldConfig(type="list[str]", default=[]),
                "metrics": StateFieldConfig(type="dict[str, int]", default={}),
                # Nested object
                "metadata": StateFieldConfig(
                    type="object",
                    required=False,
                    schema={
                        "author": "str",
                        "created": "int",
                        "flags": {
                            "type": "object",
                            "required": False,
                            "schema": {
                                "reviewed": "bool",
                                "priority": "int",
                            },
                        },
                    },
                ),
            }
        )
        StateModel = build_state_model(state_config)

        # Minimal valid state
        state1 = StateModel(topic="AI Safety")
        assert state1.topic == "AI Safety"
        assert state1.score == 0
        assert state1.notes is None
        assert state1.tags == []
        assert state1.metrics == {}
        assert state1.metadata is None

        # Full state
        state2 = StateModel(
            topic="AI Safety",
            score=95,
            notes="Important research",
            tags=["ai", "safety"],
            metrics={"citations": 42, "views": 1000},
            metadata={
                "author": "Alice",
                "created": 1234567890,
                "flags": {"reviewed": True, "priority": 1},
            },
        )
        assert state2.topic == "AI Safety"
        assert state2.score == 95
        assert state2.notes == "Important research"
        assert state2.tags == ["ai", "safety"]
        assert state2.metrics == {"citations": 42, "views": 1000}
        assert state2.metadata.author == "Alice"
        assert state2.metadata.created == 1234567890
        assert state2.metadata.flags.reviewed is True
        assert state2.metadata.flags.priority == 1


class TestErrorHandling:
    """Test error handling and validation."""

    def test_empty_state_fails(self):
        """Test that empty state is caught by Pydantic validation (no redundancy)."""
        with pytest.raises(ValidationError):
            # StateSchema itself validates empty fields, so Pydantic catches it
            StateSchema(fields={})

    def test_object_without_schema_fails(self):
        state_config = StateSchema(
            fields={"data": StateFieldConfig(type="object", required=True)}
        )
        with pytest.raises(StateBuilderError) as exc_info:
            build_state_model(state_config)
        assert "no 'schema' defined" in str(exc_info.value)

    def test_invalid_type_fails(self):
        """Test that invalid types are caught."""
        state_config = StateSchema(
            fields={"data": StateFieldConfig(type="invalid_type", required=True)}
        )
        with pytest.raises(StateBuilderError) as exc_info:
            build_state_model(state_config)
        assert "Invalid type" in str(exc_info.value)

    def test_nested_empty_schema_fails(self):
        state_config = StateSchema(
            fields={
                "data": StateFieldConfig(type="object", required=True, schema={})
            }
        )
        with pytest.raises(StateBuilderError) as exc_info:
            build_state_model(state_config)
        assert "empty schema" in str(exc_info.value).lower()


class TestModelReuse:
    """Test that models can be created multiple times."""

    def test_multiple_models_from_same_config(self):
        """Test that we can create multiple models from the same config."""
        state_config = StateSchema(
            fields={"topic": StateFieldConfig(type="str", required=True)}
        )

        StateModel1 = build_state_model(state_config)
        StateModel2 = build_state_model(state_config)

        # They should be different class instances
        assert StateModel1 is not StateModel2

        # But both should work the same way
        state1 = StateModel1(topic="AI")
        state2 = StateModel2(topic="Safety")

        assert state1.topic == "AI"
        assert state2.topic == "Safety"

    def test_different_configs_create_different_models(self):
        """Test that different configs create different models."""
        config1 = StateSchema(
            fields={"field1": StateFieldConfig(type="str", required=True)}
        )
        config2 = StateSchema(
            fields={"field2": StateFieldConfig(type="int", required=True)}
        )

        Model1 = build_state_model(config1)
        Model2 = build_state_model(config2)

        # Different structures
        state1 = Model1(field1="value")
        state2 = Model2(field2=42)

        assert state1.field1 == "value"
        assert state2.field2 == 42
