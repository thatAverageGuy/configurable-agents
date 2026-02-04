"""Tests for output builder (dynamic Pydantic output model generation)."""

import pytest
from pydantic import ValidationError

from configurable_agents.config.schema import OutputSchema, OutputSchemaField
from configurable_agents.core.output_builder import OutputBuilderError, build_output_model


class TestSimpleOutputs:
    """Test output models with simple (non-object) types."""

    def test_simple_string_output(self):
        """Test simple string output wrapped in 'result' field."""
        schema = OutputSchema(
            type="str",
            description="Generated article"
        )
        OutputModel = build_output_model(schema, "write")

        # Create instance
        output = OutputModel(result="Hello world")
        assert output.result == "Hello world"

    def test_simple_int_output(self):
        """Test simple int output."""
        schema = OutputSchema(type="int")
        OutputModel = build_output_model(schema, "count")

        output = OutputModel(result=42)
        assert output.result == 42

    def test_simple_float_output(self):
        """Test simple float output."""
        schema = OutputSchema(type="float")
        OutputModel = build_output_model(schema, "score")

        output = OutputModel(result=95.5)
        assert output.result == 95.5

    def test_simple_bool_output(self):
        """Test simple bool output."""
        schema = OutputSchema(type="bool")
        OutputModel = build_output_model(schema, "is_valid")

        output = OutputModel(result=True)
        assert output.result is True

    def test_simple_output_validation(self):
        """Test that simple outputs enforce type validation."""
        schema = OutputSchema(type="str")
        OutputModel = build_output_model(schema, "write")

        # Wrong type should fail
        with pytest.raises(ValidationError):
            OutputModel(result=123)

    def test_simple_output_required(self):
        """Test that result field is required for simple outputs."""
        schema = OutputSchema(type="str")
        OutputModel = build_output_model(schema, "write")

        # Missing result field should fail
        with pytest.raises(ValidationError):
            OutputModel()

    def test_simple_output_description_preserved(self):
        """Test that description is preserved in field metadata."""
        schema = OutputSchema(
            type="str",
            description="The generated article text"
        )
        OutputModel = build_output_model(schema, "write")

        # Check field metadata
        field_info = OutputModel.model_fields["result"]
        assert field_info.description == "The generated article text"


class TestObjectOutputs:
    """Test output models with object type (multiple fields)."""

    def test_object_output_simple(self):
        """Test object output with multiple basic fields."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="article", type="str"),
                OutputSchemaField(name="word_count", type="int"),
            ]
        )
        OutputModel = build_output_model(schema, "write")

        output = OutputModel(article="Test article", word_count=100)
        assert output.article == "Test article"
        assert output.word_count == 100

    def test_object_output_all_basic_types(self):
        """Test object output with all basic types."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="text", type="str"),
                OutputSchemaField(name="count", type="int"),
                OutputSchemaField(name="score", type="float"),
                OutputSchemaField(name="valid", type="bool"),
            ]
        )
        OutputModel = build_output_model(schema, "analyze")

        output = OutputModel(text="result", count=5, score=7.5, valid=True)
        assert output.text == "result"
        assert output.count == 5
        assert output.score == 7.5
        assert output.valid is True

    def test_object_output_with_descriptions(self):
        """Test that field descriptions are preserved."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(
                    name="article",
                    type="str",
                    description="The generated article text"
                ),
                OutputSchemaField(
                    name="word_count",
                    type="int",
                    description="Number of words in the article"
                ),
            ]
        )
        OutputModel = build_output_model(schema, "write")

        # Check field metadata
        assert OutputModel.model_fields["article"].description == "The generated article text"
        assert OutputModel.model_fields["word_count"].description == "Number of words in the article"

    def test_object_output_all_fields_required(self):
        """Test that all fields in object output are required."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="field1", type="str"),
                OutputSchemaField(name="field2", type="int"),
            ]
        )
        OutputModel = build_output_model(schema, "test")

        # Missing field should fail
        with pytest.raises(ValidationError):
            OutputModel(field1="test")

        # All fields required
        with pytest.raises(ValidationError):
            OutputModel(field2=42)

    def test_object_output_validation(self):
        """Test that object output fields enforce type validation."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="count", type="int"),
            ]
        )
        OutputModel = build_output_model(schema, "test")

        # Wrong type should fail
        with pytest.raises(ValidationError):
            OutputModel(count="not_an_int")


class TestCollectionOutputs:
    """Test output models with collection types."""

    def test_simple_list_output(self):
        """Test simple list output."""
        schema = OutputSchema(type="list")
        OutputModel = build_output_model(schema, "generate_list")

        output = OutputModel(result=[1, 2, 3, "four"])
        assert output.result == [1, 2, 3, "four"]

    def test_typed_list_output(self):
        """Test typed list output."""
        schema = OutputSchema(type="list[str]")
        OutputModel = build_output_model(schema, "generate_tags")

        output = OutputModel(result=["tag1", "tag2", "tag3"])
        assert output.result == ["tag1", "tag2", "tag3"]

    def test_dict_output(self):
        """Test dict output."""
        schema = OutputSchema(type="dict")
        OutputModel = build_output_model(schema, "generate_dict")

        output = OutputModel(result={"key": "value", "count": 42})
        assert output.result == {"key": "value", "count": 42}

    def test_typed_dict_output(self):
        """Test typed dict output."""
        schema = OutputSchema(type="dict[str, int]")
        OutputModel = build_output_model(schema, "word_counts")

        output = OutputModel(result={"hello": 5, "world": 3})
        assert output.result == {"hello": 5, "world": 3}

    def test_object_with_list_field(self):
        """Test object output with list field."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="tags", type="list[str]"),
                OutputSchemaField(name="count", type="int"),
            ]
        )
        OutputModel = build_output_model(schema, "analyze")

        output = OutputModel(tags=["ai", "ml", "nlp"], count=3)
        assert output.tags == ["ai", "ml", "nlp"]
        assert output.count == 3

    def test_object_with_dict_field(self):
        """Test object output with dict field."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="metadata", type="dict[str, str]"),
                OutputSchemaField(name="score", type="float"),
            ]
        )
        OutputModel = build_output_model(schema, "process")

        output = OutputModel(
            metadata={"author": "Alice", "version": "1.0"},
            score=8.5
        )
        assert output.metadata == {"author": "Alice", "version": "1.0"}
        assert output.score == 8.5


class TestModelNaming:
    """Test that models are named correctly."""

    def test_simple_output_model_name(self):
        """Test that simple output models have correct name."""
        schema = OutputSchema(type="str")
        OutputModel = build_output_model(schema, "my_node")

        assert OutputModel.__name__ == "Output_my_node"

    def test_object_output_model_name(self):
        """Test that object output models have correct name."""
        schema = OutputSchema(
            type="object",
            fields=[OutputSchemaField(name="result", type="str")]
        )
        OutputModel = build_output_model(schema, "another_node")

        assert OutputModel.__name__ == "Output_another_node"


class TestErrorHandling:
    """Test error handling and validation."""

    def test_missing_output_schema(self):
        """Test that missing output schema raises error."""
        with pytest.raises(OutputBuilderError, match="output_schema is required"):
            build_output_model(None, "test")

    def test_invalid_simple_type(self):
        """Test that invalid simple type raises error."""
        schema = OutputSchema(type="unknown_type")

        with pytest.raises(OutputBuilderError, match="Invalid output type"):
            build_output_model(schema, "test")

    def test_invalid_object_field_type(self):
        """Test that invalid field type in object raises error."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="field", type="bad_type")
            ]
        )

        with pytest.raises(OutputBuilderError, match="Invalid type"):
            build_output_model(schema, "test")

    def test_object_without_fields(self):
        """Test that object type without fields raises error."""
        # This should be caught by OutputSchema validator, but test anyway
        # We need to bypass Pydantic validation to test this
        schema = OutputSchema(type="str")  # Valid schema
        schema.type = "object"  # Change type after validation
        schema.fields = None

        with pytest.raises(OutputBuilderError, match="must have fields"):
            build_output_model(schema, "test")

    def test_nested_object_not_supported(self):
        """Test that nested objects in output schema raise helpful error."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="nested", type="object")
            ]
        )

        with pytest.raises(OutputBuilderError, match="Nested objects in output schema not yet supported"):
            build_output_model(schema, "test")

    def test_error_includes_node_id(self):
        """Test that errors include node ID for context."""
        schema = OutputSchema(type="invalid_type")

        with pytest.raises(OutputBuilderError, match="Node 'my_node'"):
            build_output_model(schema, "my_node")


class TestRoundTrip:
    """Test creating instances and serializing."""

    def test_simple_output_round_trip(self):
        """Test creating and serializing simple output."""
        schema = OutputSchema(type="str")
        OutputModel = build_output_model(schema, "write")

        output = OutputModel(result="Test text")
        data = output.model_dump()

        assert data == {"result": "Test text"}

    def test_object_output_round_trip(self):
        """Test creating and serializing object output."""
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="article", type="str"),
                OutputSchemaField(name="word_count", type="int"),
            ]
        )
        OutputModel = build_output_model(schema, "write")

        output = OutputModel(article="Test", word_count=10)
        data = output.model_dump()

        assert data == {"article": "Test", "word_count": 10}

    def test_model_reuse(self):
        """Test that the same schema produces consistent models."""
        schema = OutputSchema(
            type="object",
            fields=[OutputSchemaField(name="result", type="str")]
        )

        Model1 = build_output_model(schema, "node1")
        Model2 = build_output_model(schema, "node1")

        # Both should work identically
        out1 = Model1(result="test1")
        out2 = Model2(result="test2")

        assert out1.result == "test1"
        assert out2.result == "test2"
