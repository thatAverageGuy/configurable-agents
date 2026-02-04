"""Data processing tools for SQL, CSV, JSON, and YAML operations.

Provides four main tools:
- sql_query: Execute SQL queries on in-memory SQLite database
- dataframe_to_csv: Convert data to CSV file
- json_parse: Parse JSON strings
- yaml_parse: Parse YAML strings

Example:
    >>> from configurable_agents.tools import get_tool
    >>> sql_tool = get_tool("sql_query")
    >>> result = sql_tool.func({"query": "SELECT * FROM users LIMIT 10"})
"""

import io
import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool

from configurable_agents.tools.registry import ToolConfigError

logger = logging.getLogger(__name__)


def sql_query(query: str, connection_string: Optional[str] = None) -> Dict[str, Any]:
    """Execute SQL query on SQLite database.

    Args:
        query: SQL query to execute (SELECT only for safety)
        connection_string: SQLite connection string (default: in-memory)

    Returns:
        Dict with rows, columns, row_count, error

    Example:
        >>> result = sql_query("SELECT 1 as num")
        >>> assert result["rows"] == [[1]]
        >>> assert result["columns"] == ["num"]
    """
    # Safety check: only allow SELECT queries
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": "Only SELECT queries are allowed for safety",
        }

    # Reject potentially dangerous keywords
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return {
                "rows": [],
                "columns": [],
                "row_count": 0,
                "error": f"Dangerous keyword '{keyword}' not allowed in query",
            }

    try:
        if connection_string:
            conn = sqlite3.connect(connection_string)
        else:
            conn = sqlite3.connect(":memory:")

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Convert rows to list of dicts
        result_rows = [dict(row) for row in rows]

        conn.close()

        return {
            "rows": result_rows,
            "columns": columns,
            "row_count": len(result_rows),
            "error": None,
        }

    except Exception as e:
        logger.error(f"SQL query error: {e}")
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": str(e),
        }


def dataframe_to_csv(data: Any, path: str, index: bool = False) -> Dict[str, Any]:
    """Convert data to CSV file.

    Args:
        data: Data to convert (list of dicts or dict of lists)
        path: Output file path
        index: Whether to include index column (default: False)

    Returns:
        Dict with path, rows_written, error

    Example:
        >>> result = dataframe_to_csv(
        ...     [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        ...     "output.csv"
        ... )
    """
    try:
        import pandas as pd
    except ImportError:
        return {
            "path": path,
            "rows_written": 0,
            "error": "pandas package not installed. Install with: pip install pandas",
        }

    try:
        # Convert input to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            return {
                "path": path,
                "rows_written": 0,
                "error": f"Unsupported data type: {type(data)}. Use list of dicts or dict of lists.",
            }

        # Write to CSV
        df.to_csv(path, index=index)

        return {
            "path": path,
            "rows_written": len(df),
            "error": None,
        }

    except Exception as e:
        logger.error(f"DataFrame to CSV error: {e}")
        return {
            "path": path,
            "rows_written": 0,
            "error": str(e),
        }


def json_parse(json_string: str) -> Dict[str, Any]:
    """Parse JSON string.

    Args:
        json_string: JSON string to parse

    Returns:
        Dict with parsed, error fields

    Example:
        >>> result = json_parse('{"name": "Alice"}')
        >>> assert result["parsed"]["name"] == "Alice"
    """
    try:
        parsed = json.loads(json_string)
        return {
            "parsed": parsed,
            "error": None,
        }
    except json.JSONDecodeError as e:
        return {
            "parsed": None,
            "error": f"Invalid JSON: {e}",
        }
    except Exception as e:
        return {
            "parsed": None,
            "error": str(e),
        }


def yaml_parse(yaml_string: str) -> Dict[str, Any]:
    """Parse YAML string.

    Args:
        yaml_string: YAML string to parse

    Returns:
        Dict with parsed, error fields

    Example:
        >>> result = yaml_parse("name: Alice\\nage: 30")
        >>> assert result["parsed"]["name"] == "Alice"
    """
    try:
        import yaml

        parsed = yaml.safe_load(yaml_string)
        return {
            "parsed": parsed,
            "error": None,
        }
    except ImportError:
        return {
            "parsed": None,
            "error": "PyYAML package not installed. Install with: pip install pyyaml",
        }
    except yaml.YAMLError as e:
        return {
            "parsed": None,
            "error": f"Invalid YAML: {e}",
        }
    except Exception as e:
        return {
            "parsed": None,
            "error": str(e),
        }


# Tool factory functions

def create_sql_query() -> Tool:
    """Create SQL query tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="sql_query",
        description=(
            "Execute SQL SELECT query on in-memory SQLite database. "
            "Input should be a dict with 'query' (required) and optional 'connection_string'. "
            "Returns rows, columns, row_count, and error if any. "
            "Only SELECT queries are allowed for safety."
        ),
        func=lambda x: sql_query(**x) if isinstance(x, dict) else sql_query(x),
    )


def create_dataframe_to_csv() -> Tool:
    """Create dataframe_to_csv tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="dataframe_to_csv",
        description=(
            "Convert data to CSV file. "
            "Input should be a dict with 'data' (required, list of dicts or dict of lists), "
            "'path' (required), and optional 'index' (default: False). "
            "Returns path, rows_written, and error if any."
        ),
        func=dataframe_to_csv,
    )


def create_json_parse() -> Tool:
    """Create JSON parse tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="json_parse",
        description=(
            "Parse JSON string into Python object. "
            "Input should be a JSON string. "
            "Returns parsed object and error if any."
        ),
        func=lambda x: json_parse(x) if isinstance(x, str) else json_parse(**x) if isinstance(x, dict) else json_parse(str(x)),
    )


def create_yaml_parse() -> Tool:
    """Create YAML parse tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="yaml_parse",
        description=(
            "Parse YAML string into Python object. "
            "Input should be a YAML string. "
            "Returns parsed object and error if any."
        ),
        func=lambda x: yaml_parse(x) if isinstance(x, str) else yaml_parse(**x) if isinstance(x, dict) else yaml_parse(str(x)),
    )


# Register tools
def register_tools(registry: Any) -> None:
    """Register all data tools.

    Args:
        registry: ToolRegistry instance
    """
    registry.register_tool("sql_query", create_sql_query)
    registry.register_tool("dataframe_to_csv", create_dataframe_to_csv)
    registry.register_tool("json_parse", create_json_parse)
    registry.register_tool("yaml_parse", create_yaml_parse)


__all__ = [
    "sql_query",
    "dataframe_to_csv",
    "json_parse",
    "yaml_parse",
    "create_sql_query",
    "create_dataframe_to_csv",
    "create_json_parse",
    "create_yaml_parse",
    "register_tools",
]
