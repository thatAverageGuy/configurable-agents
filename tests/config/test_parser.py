"""Tests for config parser"""

import json
from pathlib import Path

import pytest
import yaml

from configurable_agents.config.parser import (
    ConfigLoader,
    ConfigParseError,
    parse_config_file,
)


class TestConfigLoader:
    """Test ConfigLoader class"""

    @pytest.fixture
    def loader(self):
        """Create ConfigLoader instance"""
        return ConfigLoader()

    @pytest.fixture
    def fixtures_dir(self):
        """Path to test fixtures directory"""
        return Path(__file__).parent / "fixtures"

    def test_load_valid_yaml(self, loader, fixtures_dir):
        """Test loading valid YAML file"""
        config_path = fixtures_dir / "valid_config.yaml"
        config = loader.load_file(str(config_path))

        assert isinstance(config, dict)
        assert config["schema_version"] == "1.0"
        assert config["flow"]["name"] == "test_workflow"
        assert "state" in config
        assert "nodes" in config
        assert "edges" in config

    def test_load_valid_json(self, loader, fixtures_dir):
        """Test loading valid JSON file"""
        config_path = fixtures_dir / "valid_config.json"
        config = loader.load_file(str(config_path))

        assert isinstance(config, dict)
        assert config["schema_version"] == "1.0"
        assert config["flow"]["name"] == "test_workflow"
        assert "state" in config
        assert "nodes" in config
        assert "edges" in config

    def test_yaml_json_equivalence(self, loader, fixtures_dir):
        """Test that YAML and JSON produce equivalent structures"""
        yaml_config = loader.load_file(str(fixtures_dir / "valid_config.yaml"))
        json_config = loader.load_file(str(fixtures_dir / "valid_config.json"))

        # Should have same top-level keys
        assert yaml_config.keys() == json_config.keys()
        assert yaml_config["flow"]["name"] == json_config["flow"]["name"]

    def test_load_file_not_found(self, loader):
        """Test loading non-existent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_file("nonexistent.yaml")

        assert "not found" in str(exc_info.value).lower()

    def test_load_invalid_yaml_syntax(self, loader, fixtures_dir):
        """Test loading YAML with syntax errors raises ConfigParseError"""
        config_path = fixtures_dir / "invalid_syntax.yaml"

        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(config_path))

        assert "invalid yaml syntax" in str(exc_info.value).lower()

    def test_load_invalid_json_syntax(self, loader, fixtures_dir):
        """Test loading JSON with syntax errors raises ConfigParseError"""
        config_path = fixtures_dir / "invalid_syntax.json"

        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(config_path))

        assert "invalid json syntax" in str(exc_info.value).lower()

    def test_load_unsupported_extension(self, loader, tmp_path):
        """Test loading file with unsupported extension raises ConfigParseError"""
        # Create a .txt file
        test_file = tmp_path / "config.txt"
        test_file.write_text("some content")

        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(test_file))

        assert "unsupported file extension" in str(exc_info.value).lower()
        assert ".txt" in str(exc_info.value)

    def test_load_directory_path(self, loader, tmp_path):
        """Test loading directory path raises ConfigParseError"""
        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(tmp_path))

        assert "not a file" in str(exc_info.value).lower()

    def test_load_relative_path(self, loader, fixtures_dir, tmp_path, monkeypatch):
        """Test loading with relative path"""
        # Change to fixtures directory
        monkeypatch.chdir(fixtures_dir)

        # Load with relative path
        config = loader.load_file("valid_config.yaml")

        assert isinstance(config, dict)
        assert config["flow"]["name"] == "test_workflow"

    def test_load_absolute_path(self, loader, fixtures_dir):
        """Test loading with absolute path"""
        config_path = (fixtures_dir / "valid_config.yaml").resolve()
        config = loader.load_file(str(config_path))

        assert isinstance(config, dict)
        assert config["flow"]["name"] == "test_workflow"

    def test_load_yml_extension(self, loader, tmp_path):
        """Test loading .yml extension (alternative YAML extension)"""
        # Create .yml file
        config_file = tmp_path / "config.yml"
        config_data = {"flow": {"name": "test"}, "nodes": [], "edges": []}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = loader.load_file(str(config_file))

        assert isinstance(config, dict)
        assert config["flow"]["name"] == "test"


class TestConvenienceFunction:
    """Test parse_config_file convenience function"""

    @pytest.fixture
    def fixtures_dir(self):
        """Path to test fixtures directory"""
        return Path(__file__).parent / "fixtures"

    def test_parse_config_file_yaml(self, fixtures_dir):
        """Test convenience function with YAML"""
        config_path = fixtures_dir / "valid_config.yaml"
        config = parse_config_file(str(config_path))

        assert isinstance(config, dict)
        assert config["schema_version"] == "1.0"

    def test_parse_config_file_json(self, fixtures_dir):
        """Test convenience function with JSON"""
        config_path = fixtures_dir / "valid_config.json"
        config = parse_config_file(str(config_path))

        assert isinstance(config, dict)
        assert config["schema_version"] == "1.0"

    def test_parse_config_file_not_found(self):
        """Test convenience function with non-existent file"""
        with pytest.raises(FileNotFoundError):
            parse_config_file("nonexistent.yaml")

    def test_parse_config_file_invalid_syntax(self, fixtures_dir):
        """Test convenience function with invalid syntax"""
        config_path = fixtures_dir / "invalid_syntax.yaml"

        with pytest.raises(ConfigParseError):
            parse_config_file(str(config_path))


class TestErrorMessages:
    """Test that error messages are helpful"""

    @pytest.fixture
    def loader(self):
        return ConfigLoader()

    def test_file_not_found_message_includes_path(self, loader):
        """Test FileNotFoundError includes the file path"""
        path = "missing_file.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_file(path)

        assert path in str(exc_info.value)

    def test_yaml_error_message_includes_filename(self, loader, tmp_path):
        """Test YAML parse error includes filename"""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("invalid: yaml: syntax:")

        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(bad_yaml))

        assert "bad.yaml" in str(exc_info.value)

    def test_json_error_message_includes_filename(self, loader, tmp_path):
        """Test JSON parse error includes filename"""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text('{"invalid": json}')

        with pytest.raises(ConfigParseError) as exc_info:
            loader.load_file(str(bad_json))

        assert "bad.json" in str(exc_info.value)
