"""
Unit tests for deployment artifact generator.

Tests cover:
- Template variable building
- File generation from templates
- Error handling
- Edge cases
"""
import json
from pathlib import Path

import pytest

from configurable_agents.config import WorkflowConfig
from configurable_agents.deploy.generator import (
    DeploymentArtifactGenerator,
    generate_deployment_artifacts,
)


@pytest.fixture
def sample_workflow_config():
    """Sample workflow config for testing"""
    config_dict = {
        "schema_version": "1.0",
        "flow": {
            "name": "test_workflow",
            "description": "Test workflow",
            "version": "1.0.0",
        },
        "state": {
            "fields": {
                "topic": {"type": "str", "required": True, "description": "Topic to write about"},
                "article": {"type": "str", "default": "", "description": "Generated article"},
                "word_count": {"type": "int", "default": 0, "description": "Word count"},
            }
        },
        "nodes": [
            {
                "id": "write",
                "description": "Write article",
                "prompt": "Write about {state.topic}",
                "outputs": ["article", "word_count"],
                "output_schema": {
                    "type": "object",
                    "fields": [
                        {"name": "article", "type": "str"},
                        {"name": "word_count", "type": "int"},
                    ],
                },
            }
        ],
        "edges": [
            {"from": "START", "to": "write"},
            {"from": "write", "to": "END"},
        ],
        "config": {"llm": {"model": "gemini-2.5-flash-lite", "temperature": 0.7}},
    }
    return WorkflowConfig(**config_dict)


@pytest.fixture
def generator(sample_workflow_config):
    """Generator instance with sample config"""
    return DeploymentArtifactGenerator(sample_workflow_config)


class TestDeploymentArtifactGenerator:
    """Tests for DeploymentArtifactGenerator class"""

    def test_init(self, sample_workflow_config):
        """Test generator initialization"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        assert generator.config == sample_workflow_config
        assert generator.templates_dir.exists()
        assert generator.templates_dir.is_dir()

    def test_templates_dir_exists(self, generator):
        """Test that templates directory exists and contains expected files"""
        templates_dir = generator.templates_dir
        assert templates_dir.exists()

        # Check required template files exist
        required_templates = [
            "Dockerfile.template",
            "server.py.template",
            "requirements.txt.template",
            "docker-compose.yml.template",
            ".env.example.template",
            "README.md.template",
            ".dockerignore",
        ]

        for template in required_templates:
            template_path = templates_dir / template
            assert template_path.exists(), f"Template missing: {template}"

    def test_build_template_variables_defaults(self, generator):
        """Test template variable building with default values"""
        variables = generator._build_template_variables(
            api_port=8000,
            mlflow_port=5000,
            sync_timeout=30,
            enable_mlflow=True,
            container_name="test_workflow",
        )

        assert variables["workflow_name"] == "test_workflow"
        assert variables["workflow_version"] == "1.0.0"
        assert variables["container_name"] == "test_workflow"
        assert variables["api_port"] == "8000"
        assert variables["mlflow_port"] == "5000"
        assert variables["sync_timeout"] == "30"
        assert "mlflow ui" in variables["cmd_line"]
        assert "mlflow" in variables["mlflow_requirement"]
        assert "example_input" in variables
        assert "package_version" in variables
        assert "generated_at" in variables

    def test_build_template_variables_mlflow_disabled(self, generator):
        """Test template variables with MLFlow disabled"""
        variables = generator._build_template_variables(
            api_port=8000,
            mlflow_port=0,
            sync_timeout=30,
            enable_mlflow=False,
            container_name="test_workflow",
        )

        assert "mlflow ui" not in variables["cmd_line"]
        assert "python server.py" in variables["cmd_line"]
        assert "disabled" in variables["mlflow_requirement"]

    def test_build_template_variables_custom_ports(self, generator):
        """Test template variables with custom ports"""
        variables = generator._build_template_variables(
            api_port=9000,
            mlflow_port=5001,
            sync_timeout=60,
            enable_mlflow=True,
            container_name="custom_workflow",
        )

        assert variables["api_port"] == "9000"
        assert variables["mlflow_port"] == "5001"
        assert variables["sync_timeout"] == "60"
        assert variables["container_name"] == "custom_workflow"

    def test_build_example_input(self, generator):
        """Test example input generation from state schema"""
        example_json = generator._build_example_input()
        example = json.loads(example_json)

        # Should include required fields
        assert "topic" in example
        assert isinstance(example["topic"], str)

    def test_build_example_input_various_types(self):
        """Test example input with various field types"""
        config_dict = {
            "schema_version": "1.0",
            "flow": {"name": "test", "description": "Test"},
            "state": {
                "fields": {
                    "str_field": {"type": "str", "required": True},
                    "int_field": {"type": "int", "required": True},
                    "float_field": {"type": "float", "required": True},
                    "bool_field": {"type": "bool", "required": True},
                    "list_field": {"type": "list[str]", "required": True},
                    "dict_field": {"type": "dict", "required": True},
                }
            },
            "nodes": [
                {
                    "id": "test",
                    "description": "Test",
                    "prompt": "Test",
                    "outputs": ["str_field"],
                    "output_schema": {
                        "type": "object",
                        "fields": [{"name": "str_field", "type": "str"}],
                    },
                }
            ],
            "edges": [{"from": "START", "to": "test"}, {"from": "test", "to": "END"}],
        }
        config = WorkflowConfig(**config_dict)
        generator = DeploymentArtifactGenerator(config)

        example_json = generator._build_example_input()
        example = json.loads(example_json)

        assert isinstance(example["str_field"], str)
        assert isinstance(example["int_field"], int)
        assert isinstance(example["float_field"], float)
        assert isinstance(example["bool_field"], bool)
        assert isinstance(example["list_field"], list)
        assert isinstance(example["dict_field"], dict)

    def test_get_package_version(self, generator):
        """Test package version detection"""
        version = generator._get_package_version()
        assert isinstance(version, str)
        assert len(version) > 0
        # Should match pattern like "0.1.0" or "0.1.0-dev"
        assert version[0].isdigit()

    def test_generate_from_template(self, generator, tmp_path):
        """Test template file generation with variable substitution"""
        variables = {
            "workflow_name": "test_workflow",
            "api_port": "8000",
            "sync_timeout": "30",
        }

        # Create simple test template
        template_content = "Workflow: ${workflow_name}\nPort: ${api_port}\nTimeout: ${sync_timeout}s"
        template_path = tmp_path / "test.template"
        template_path.write_text(template_content)

        # Temporarily replace templates_dir
        original_dir = generator.templates_dir
        generator.templates_dir = tmp_path

        output_path = tmp_path / "output.txt"
        result = generator._generate_from_template("test.template", output_path, variables)

        # Restore original
        generator.templates_dir = original_dir

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "Workflow: test_workflow" in content
        assert "Port: 8000" in content
        assert "Timeout: 30s" in content

    def test_generate_from_template_missing_variable(self, generator, tmp_path):
        """Test that missing template variables raise error"""
        variables = {"workflow_name": "test"}

        template_content = "${workflow_name} - ${missing_var}"
        template_path = tmp_path / "test.template"
        template_path.write_text(template_content)

        original_dir = generator.templates_dir
        generator.templates_dir = tmp_path

        with pytest.raises(ValueError, match="Missing template variable"):
            generator._generate_from_template(
                "test.template", tmp_path / "output.txt", variables
            )

        generator.templates_dir = original_dir

    def test_generate_from_template_missing_file(self, generator, tmp_path):
        """Test that missing template file raises error"""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            generator._generate_from_template(
                "nonexistent.template", tmp_path / "output.txt", {}
            )

    def test_copy_static_file(self, generator, tmp_path):
        """Test copying static files without substitution"""
        # Create test file
        static_content = "# Static content\nNo variables here"
        static_path = tmp_path / "static.txt"
        static_path.write_text(static_content)

        original_dir = generator.templates_dir
        generator.templates_dir = tmp_path

        output_path = tmp_path / "copied.txt"
        result = generator._copy_static_file("static.txt", output_path)

        generator.templates_dir = original_dir

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_text() == static_content

    def test_copy_static_file_missing(self, generator, tmp_path):
        """Test that missing static file raises error"""
        with pytest.raises(FileNotFoundError, match="Static file not found"):
            generator._copy_static_file("nonexistent.txt", tmp_path / "output.txt")

    def test_copy_workflow_config(self, generator, tmp_path):
        """Test workflow config serialization to YAML"""
        output_path = tmp_path / "workflow.yaml"
        result = generator._copy_workflow_config(output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify it's valid YAML
        import yaml

        with open(output_path) as f:
            config_dict = yaml.safe_load(f)

        assert config_dict["flow"]["name"] == "test_workflow"
        assert config_dict["schema_version"] == "1.0"

    def test_generate_creates_all_artifacts(self, generator, tmp_path):
        """Test that generate() creates all expected artifacts"""
        artifacts = generator.generate(
            output_dir=tmp_path,
            api_port=8000,
            mlflow_port=5000,
            sync_timeout=30,
            enable_mlflow=True,
            container_name="test_workflow",
        )

        # Check all expected artifacts are present
        expected_artifacts = [
            "Dockerfile",
            "server.py",
            "requirements.txt",
            "docker-compose.yml",
            ".env.example",
            "README.md",
            ".dockerignore",
            "workflow.yaml",
        ]

        for artifact_name in expected_artifacts:
            assert artifact_name in artifacts
            assert artifacts[artifact_name].exists()

    def test_generate_creates_output_directory(self, generator, tmp_path):
        """Test that generate() creates output directory if it doesn't exist"""
        output_dir = tmp_path / "new_dir" / "nested"
        assert not output_dir.exists()

        artifacts = generator.generate(output_dir=output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()
        assert len(artifacts) == 8  # All artifacts created

    def test_generate_with_custom_container_name(self, generator, tmp_path):
        """Test generate() with custom container name"""
        artifacts = generator.generate(
            output_dir=tmp_path, container_name="custom_container_name"
        )

        # Check that docker-compose.yml uses custom name
        compose_content = artifacts["docker-compose.yml"].read_text()
        assert "custom_container_name" in compose_content

    def test_generate_mlflow_disabled(self, generator, tmp_path):
        """Test generate() with MLFlow disabled"""
        artifacts = generator.generate(
            output_dir=tmp_path, enable_mlflow=False, mlflow_port=0
        )

        # Check Dockerfile doesn't include mlflow command
        dockerfile_content = artifacts["Dockerfile"].read_text()
        assert "mlflow ui" not in dockerfile_content
        assert "python server.py" in dockerfile_content

        # Check requirements.txt doesn't include mlflow
        requirements_content = artifacts["requirements.txt"].read_text()
        assert "disabled" in requirements_content or "mlflow" not in requirements_content


class TestConvenienceFunction:
    """Tests for generate_deployment_artifacts() convenience function"""

    def test_generate_deployment_artifacts_from_file(self, tmp_path):
        """Test convenience function with file path"""
        # Create sample workflow file
        config_content = """
schema_version: "1.0"
flow:
  name: test_workflow
  description: Test
state:
  fields:
    topic: {type: str, required: true}
nodes:
  - id: test
    description: Test
    prompt: Test {state.topic}
    outputs: [topic]
    output_schema:
      type: object
      fields:
        - {name: topic, type: str}
edges:
  - {from: START, to: test}
  - {from: test, to: END}
"""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text(config_content)

        output_dir = tmp_path / "deploy"

        artifacts = generate_deployment_artifacts(
            config_path=config_file,
            output_dir=output_dir,
            api_port=9000,
            mlflow_port=5001,
        )

        assert len(artifacts) == 8
        assert all(path.exists() for path in artifacts.values())
        assert (output_dir / "Dockerfile").exists()
        assert (output_dir / "server.py").exists()

    def test_generate_deployment_artifacts_invalid_config(self, tmp_path):
        """Test convenience function with invalid config"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")

        with pytest.raises(Exception):  # Will raise validation error
            generate_deployment_artifacts(config_file, tmp_path / "deploy")

    def test_generate_deployment_artifacts_missing_file(self, tmp_path):
        """Test convenience function with missing config file"""
        with pytest.raises(Exception):  # FileNotFoundError or similar
            generate_deployment_artifacts(tmp_path / "nonexistent.yaml", tmp_path / "deploy")
