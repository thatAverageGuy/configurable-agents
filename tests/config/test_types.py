"""Tests for type system (type string parsing and validation)."""

import pytest

from configurable_agents.config.types import (
    TypeParseError,
    get_python_type,
    parse_type_string,
    validate_type_string,
)


class TestBasicTypes:
    """Test parsing of basic types."""

    def test_parse_str(self):
        result = parse_type_string("str")
        assert result["kind"] == "basic"
        assert result["type"] == str
        assert result["name"] == "str"

    def test_parse_int(self):
        result = parse_type_string("int")
        assert result["kind"] == "basic"
        assert result["type"] == int
        assert result["name"] == "int"

    def test_parse_float(self):
        result = parse_type_string("float")
        assert result["kind"] == "basic"
        assert result["type"] == float
        assert result["name"] == "float"

    def test_parse_bool(self):
        result = parse_type_string("bool")
        assert result["kind"] == "basic"
        assert result["type"] == bool
        assert result["name"] == "bool"


class TestCollectionTypes:
    """Test parsing of collection types."""

    def test_parse_generic_list(self):
        result = parse_type_string("list")
        assert result["kind"] == "list"
        assert result["item_type"] is None
        assert result["name"] == "list"

    def test_parse_generic_dict(self):
        result = parse_type_string("dict")
        assert result["kind"] == "dict"
        assert result["key_type"] is None
        assert result["value_type"] is None
        assert result["name"] == "dict"

    def test_parse_list_str(self):
        result = parse_type_string("list[str]")
        assert result["kind"] == "list"
        assert result["item_type"]["kind"] == "basic"
        assert result["item_type"]["type"] == str
        assert result["name"] == "list[str]"

    def test_parse_list_int(self):
        result = parse_type_string("list[int]")
        assert result["kind"] == "list"
        assert result["item_type"]["kind"] == "basic"
        assert result["item_type"]["type"] == int

    def test_parse_list_float(self):
        result = parse_type_string("list[float]")
        assert result["kind"] == "list"
        assert result["item_type"]["kind"] == "basic"
        assert result["item_type"]["type"] == float

    def test_parse_dict_str_int(self):
        result = parse_type_string("dict[str, int]")
        assert result["kind"] == "dict"
        assert result["key_type"]["kind"] == "basic"
        assert result["key_type"]["type"] == str
        assert result["value_type"]["kind"] == "basic"
        assert result["value_type"]["type"] == int
        assert result["name"] == "dict[str, int]"

    def test_parse_dict_str_str(self):
        result = parse_type_string("dict[str, str]")
        assert result["kind"] == "dict"
        assert result["key_type"]["type"] == str
        assert result["value_type"]["type"] == str

    def test_parse_dict_with_spaces(self):
        """Test that spaces around types are handled correctly."""
        result = parse_type_string("dict[str,  int]")
        assert result["kind"] == "dict"
        assert result["key_type"]["type"] == str
        assert result["value_type"]["type"] == int


class TestObjectType:
    """Test parsing of object type."""

    def test_parse_object(self):
        result = parse_type_string("object")
        assert result["kind"] == "object"
        assert result["name"] == "object"


class TestInvalidTypes:
    """Test error handling for invalid type strings."""

    def test_empty_string(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("")
        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("   ")
        assert "empty" in str(exc_info.value).lower()

    def test_unknown_type(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("string")
        assert "Unknown type" in str(exc_info.value)

    def test_malformed_list(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("list[")
        assert "Unknown type" in str(exc_info.value)

    def test_malformed_dict(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("dict[str")
        assert "Unknown type" in str(exc_info.value)

    def test_dict_missing_value_type(self):
        with pytest.raises(TypeParseError) as exc_info:
            parse_type_string("dict[str,]")
        assert "Unknown type" in str(exc_info.value) or "empty" in str(
            exc_info.value
        ).lower()

    def test_invalid_nested_type(self):
        with pytest.raises(TypeParseError):
            parse_type_string("list[unknown]")


class TestValidateTypeString:
    """Test validate_type_string function."""

    def test_valid_basic_types(self):
        assert validate_type_string("str") is True
        assert validate_type_string("int") is True
        assert validate_type_string("float") is True
        assert validate_type_string("bool") is True

    def test_valid_collection_types(self):
        assert validate_type_string("list") is True
        assert validate_type_string("dict") is True
        assert validate_type_string("list[str]") is True
        assert validate_type_string("dict[str, int]") is True

    def test_valid_object_type(self):
        assert validate_type_string("object") is True

    def test_invalid_types(self):
        assert validate_type_string("") is False
        assert validate_type_string("unknown") is False
        assert validate_type_string("list[") is False
        assert validate_type_string("dict[str") is False


class TestGetPythonType:
    """Test get_python_type function."""

    def test_basic_types(self):
        assert get_python_type("str") == str
        assert get_python_type("int") == int
        assert get_python_type("float") == float
        assert get_python_type("bool") == bool

    def test_collection_types(self):
        assert get_python_type("list") == list
        assert get_python_type("list[str]") == list
        assert get_python_type("dict") == dict
        assert get_python_type("dict[str, int]") == dict

    def test_object_type(self):
        assert get_python_type("object") == dict

    def test_invalid_type(self):
        with pytest.raises(TypeParseError):
            get_python_type("unknown")


class TestWhitespaceHandling:
    """Test that whitespace is handled correctly."""

    def test_leading_trailing_spaces(self):
        result = parse_type_string("  str  ")
        assert result["kind"] == "basic"
        assert result["type"] == str

    def test_spaces_in_list(self):
        result = parse_type_string("list[ str ]")
        assert result["kind"] == "list"
        assert result["item_type"]["type"] == str

    def test_spaces_in_dict(self):
        result = parse_type_string("dict[ str , int ]")
        assert result["kind"] == "dict"
        assert result["key_type"]["type"] == str
        assert result["value_type"]["type"] == int
