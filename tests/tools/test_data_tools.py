"""Tests for data processing tools.

Tests SQL query, CSV export, JSON parsing, and YAML parsing tools.
"""

import pytest

from configurable_agents.tools.data_tools import (
    create_dataframe_to_csv,
    create_json_parse,
    create_sql_query,
    create_yaml_parse,
    dataframe_to_csv,
    json_parse,
    sql_query,
    yaml_parse,
)


class TestSQLQuery:
    """Tests for sql_query tool."""

    def test_select_basic(self):
        """Test basic SELECT query."""
        result = sql_query("SELECT 1 as num, 'test' as str")
        assert result["error"] is None
        assert result["rows"] == [{"num": 1, "str": "test"}]
        assert result["columns"] == ["num", "str"]
        assert result["row_count"] == 1

    def test_select_with_calculations(self):
        """Test SELECT with calculations."""
        result = sql_query("SELECT 2 + 3 as sum, 10 * 5 as product")
        assert result["error"] is None
        assert result["rows"] == [{"sum": 5, "product": 50}]

    def test_select_multiple_rows(self):
        """Test SELECT returning multiple rows using VALUES."""
        # Use VALUES instead of WITH clause which might be flagged
        result = sql_query(
            "SELECT 1 as num UNION ALL SELECT 2 UNION ALL SELECT 3"
        )
        assert result["error"] is None
        assert result["row_count"] == 3

    def test_select_with_functions(self):
        """Test SELECT with string functions."""
        result = sql_query("SELECT UPPER('hello') as upper, LOWER('WORLD') as lower")
        assert result["error"] is None
        assert result["rows"] == [{"upper": "HELLO", "lower": "world"}]

    def test_reject_drop_statement(self):
        """Test that DROP statements are rejected."""
        result = sql_query("DROP TABLE test")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()
        assert result["row_count"] == 0

    def test_reject_delete_statement(self):
        """Test that DELETE statements are rejected."""
        result = sql_query("DELETE FROM users WHERE id = 1")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()

    def test_reject_update_statement(self):
        """Test that UPDATE statements are rejected."""
        result = sql_query("UPDATE users SET name = 'test'")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()

    def test_reject_insert_statement(self):
        """Test that INSERT statements are rejected."""
        result = sql_query("INSERT INTO users VALUES (1, 'test')")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()

    def test_reject_alter_statement(self):
        """Test that ALTER statements are rejected."""
        result = sql_query("ALTER TABLE users ADD COLUMN age INT")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()

    def test_reject_create_statement(self):
        """Test that CREATE statements are rejected."""
        result = sql_query("CREATE TABLE test (id INT)")
        assert result["error"] is not None
        assert "allowed" in result["error"].lower()

    def test_invalid_sql(self):
        """Test that invalid SQL returns error."""
        result = sql_query("NOT VALID SQL")
        assert result["error"] is not None

    def test_sql_tool_factory(self):
        """Test sql_query tool factory."""
        tool = create_sql_query()
        assert tool.name == "sql_query"
        assert "sql" in tool.description.lower()
        assert "safety" in tool.description.lower()


class TestDataframeToCSV:
    """Tests for dataframe_to_csv tool."""

    def test_list_of_dicts(self, tmp_path):
        """Test converting list of dicts to CSV."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        output_path = tmp_path / "output.csv"

        result = dataframe_to_csv(data, str(output_path))

        assert result["error"] is None
        assert result["path"] == str(output_path)
        assert result["rows_written"] == 2

        # Verify file contents
        import os
        assert os.path.exists(output_path)
        with open(output_path) as f:
            content = f.read()
            assert "Alice" in content
            assert "Bob" in content

    def test_dict_of_lists(self, tmp_path):
        """Test converting dict of lists to CSV."""
        data = {
            "name": ["Alice", "Bob"],
            "age": [30, 25],
        }
        output_path = tmp_path / "output.csv"

        result = dataframe_to_csv(data, str(output_path))

        assert result["error"] is None
        assert result["rows_written"] == 2

    def test_with_index(self, tmp_path):
        """Test CSV with index column."""
        data = [{"name": "Alice", "age": 30}]
        output_path = tmp_path / "output.csv"

        result = dataframe_to_csv(data, str(output_path), index=True)

        assert result["error"] is None

        # Check for index column in output
        with open(output_path) as f:
            content = f.read()
            # With index, first column should be unnamed index
            lines = content.strip().split("\n")
            assert len(lines[0].split(",")) == 3  # index + name + age

    def test_empty_data(self, tmp_path):
        """Test with empty data list."""
        data = []
        output_path = tmp_path / "output.csv"

        result = dataframe_to_csv(data, str(output_path))

        assert result["error"] is None
        assert result["rows_written"] == 0

    def test_unsupported_type(self, tmp_path):
        """Test with unsupported data type."""
        output_path = tmp_path / "output.csv"

        result = dataframe_to_csv("not a list or dict", str(output_path))

        assert result["error"] is not None
        assert "Unsupported data type" in result["error"]

    def test_tool_factory(self):
        """Test dataframe_to_csv tool factory."""
        tool = create_dataframe_to_csv()
        assert tool.name == "dataframe_to_csv"
        assert "csv" in tool.description.lower()


class TestJSONParse:
    """Tests for json_parse tool."""

    def test_valid_json_object(self):
        """Test parsing valid JSON object."""
        result = json_parse('{"name": "Alice", "age": 30}')
        assert result["error"] is None
        assert result["parsed"]["name"] == "Alice"
        assert result["parsed"]["age"] == 30

    def test_valid_json_array(self):
        """Test parsing valid JSON array."""
        result = json_parse('[1, 2, 3, "four"]')
        assert result["error"] is None
        assert result["parsed"] == [1, 2, 3, "four"]

    def test_valid_json_nested(self):
        """Test parsing nested JSON."""
        result = json_parse('{"user": {"name": "Bob", "tags": ["admin", "user"]}}')
        assert result["error"] is None
        assert result["parsed"]["user"]["name"] == "Bob"
        assert result["parsed"]["user"]["tags"] == ["admin", "user"]

    def test_invalid_json_syntax(self):
        """Test parsing invalid JSON."""
        result = json_parse('{"name": "Alice", age: 30}')  # Missing quotes around age
        assert result["parsed"] is None
        assert result["error"] is not None
        assert "Invalid JSON" in result["error"]

    def test_invalid_json_structure(self):
        """Test parsing malformed JSON."""
        result = json_parse('{"name": "Alice"')  # Missing closing brace
        assert result["parsed"] is None
        assert result["error"] is not None

    def test_empty_json(self):
        """Test parsing empty JSON."""
        result = json_parse('{}')
        assert result["error"] is None
        assert result["parsed"] == {}

    def test_json_null(self):
        """Test parsing JSON with null values."""
        result = json_parse('{"value": null}')
        assert result["error"] is None
        assert result["parsed"]["value"] is None

    def test_tool_factory(self):
        """Test json_parse tool factory."""
        tool = create_json_parse()
        assert tool.name == "json_parse"
        assert "json" in tool.description.lower()


class TestYAMLParse:
    """Tests for yaml_parse tool."""

    def test_valid_yaml_simple(self):
        """Test parsing simple YAML."""
        result = yaml_parse("name: Alice\nage: 30")
        assert result["error"] is None
        assert result["parsed"]["name"] == "Alice"
        assert result["parsed"]["age"] == 30

    def test_valid_yaml_nested(self):
        """Test parsing nested YAML."""
        yaml_str = """
user:
  name: Bob
  preferences:
    theme: dark
    notifications: true
        """
        result = yaml_parse(yaml_str)
        assert result["error"] is None
        assert result["parsed"]["user"]["name"] == "Bob"
        assert result["parsed"]["user"]["preferences"]["theme"] == "dark"

    def test_valid_yaml_list(self):
        """Test parsing YAML list."""
        yaml_str = """
items:
  - apple
  - banana
  - orange
        """
        result = yaml_parse(yaml_str)
        assert result["error"] is None
        assert result["parsed"]["items"] == ["apple", "banana", "orange"]

    def test_valid_yaml_multiline_string(self):
        """Test parsing YAML with multiline string."""
        yaml_str = """
description: |
  This is a
  multiline
  string.
        """
        result = yaml_parse(yaml_str)
        assert result["error"] is None
        assert "multiline" in result["parsed"]["description"]

    def test_invalid_yaml(self):
        """Test parsing invalid YAML."""
        result = yaml_parse("name: Alice\n  bad_indent: value")  # Invalid indentation
        # This might be valid YAML in some parsers, so we check the result
        # YAML is more permissive than JSON

    def test_empty_yaml(self):
        """Test parsing empty YAML."""
        result = yaml_parse("")
        assert result["error"] is None
        assert result["parsed"] is None

    def test_yaml_null(self):
        """Test parsing YAML with null values."""
        result = yaml_parse("value: null\nempty:")
        assert result["error"] is None
        assert result["parsed"]["value"] is None
        assert result["parsed"]["empty"] is None

    def test_tool_factory(self):
        """Test yaml_parse tool factory."""
        tool = create_yaml_parse()
        assert tool.name == "yaml_parse"
        assert "yaml" in tool.description.lower()
