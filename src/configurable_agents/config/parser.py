"""Config file parser for YAML and JSON formats"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from configurable_agents.logging_config import get_logger

logger = get_logger(__name__)


class ConfigParseError(Exception):
    """Raised when config file cannot be parsed"""

    pass


class ConfigLoader:
    """Load workflow configurations from YAML or JSON files"""

    def load_file(self, path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML or JSON file.

        Auto-detects format from file extension:
        - .yaml, .yml → YAML
        - .json → JSON

        Args:
            path: Path to config file (absolute or relative to cwd)

        Returns:
            Parsed configuration as dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigParseError: If file has invalid YAML/JSON syntax
        """
        logger.info(f"Loading config from: {path}")
        return self._parse_file(path)

    def _parse_file(self, path: str) -> Dict[str, Any]:
        """
        Parse YAML or JSON file to dictionary.

        Args:
            path: Path to config file

        Returns:
            Parsed configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ConfigParseError: If parsing fails
        """
        file_path = Path(path)

        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        # Check file is actually a file
        if not file_path.is_file():
            raise ConfigParseError(f"Path is not a file: {path}")

        # Determine format from extension
        suffix = file_path.suffix.lower()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if suffix == ".json":
                    logger.debug(f"Parsing as JSON: {path}")
                    return json.load(f)
                elif suffix in [".yaml", ".yml"]:
                    logger.debug(f"Parsing as YAML: {path}")
                    return yaml.safe_load(f)
                else:
                    raise ConfigParseError(
                        f"Unsupported file extension: {suffix}. "
                        f"Supported formats: .yaml, .yml, .json"
                    )
        except json.JSONDecodeError as e:
            raise ConfigParseError(f"Invalid JSON syntax in {path}: {e}") from e
        except yaml.YAMLError as e:
            raise ConfigParseError(f"Invalid YAML syntax in {path}: {e}") from e
        except Exception as e:
            raise ConfigParseError(f"Failed to parse {path}: {e}") from e


# Convenience function for users
def parse_config_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file (convenience function).

    This is the recommended way to load configs for most use cases.

    Args:
        config_path: Path to config file (absolute or relative)

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigParseError: If file has invalid syntax

    Example:
        >>> config = parse_config_file("workflow.yaml")
        >>> print(config["flow"]["name"])
        article_writer
    """
    loader = ConfigLoader()
    return loader.load_file(config_path)
