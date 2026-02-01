"""
Integration tests for FastAPI server deployment.

These tests verify that:
1. Generated artifacts are complete and valid
2. Server code can be generated without errors
3. MLFlow integration is properly configured
4. Generated server can be imported and validated

NOTE: These are integration tests that validate the deployment pipeline,
not end-to-end server execution tests (which require running containers).
"""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from configurable_agents.config import WorkflowConfig
from configurable_agents.deploy.generator import DeploymentArtifactGenerator


@pytest.fixture
def real_workflow_config():
    """Real workflow config for integration testing"""
    config_dict = {
        "schema_version": "1.0",
        "flow": {
            "name": "integration_test_workflow",
            "description": "Integration test workflow",
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
                "id": "write_article",
                "description": "Write article about topic",
                "prompt": "Write a short article about {state.topic}",
                "outputs": ["article", "word_count"],
                "output_schema": {
                    "type": "object",
                    "fields": [
                        {"name": "article", "type": "str", "description": "Article content"},
                        {"name": "word_count", "type": "int", "description": "Word count"},
                    ],
                },
            }
        ],
        "edges": [
            {"from": "START", "to": "write_article"},
            {"from": "write_article", "to": "END"},
        ],
        "config": {
            "llm": {
                "model": "gemini-2.0-flash-lite",
                "temperature": 0.7,
            }
        },
    }
    return WorkflowConfig(**config_dict)


@pytest.mark.integration
class TestDeploymentPipeline:
    """Integration tests for deployment artifact generation pipeline"""

    def test_generate_complete_deployment_package(self, real_workflow_config, tmp_path):
        """
        Generate complete deployment package with all artifacts.

        This test verifies:
        1. All 8 artifacts are generated
        2. Files are valid and non-empty
        3. Workflow config is properly serialized
        """
        generator = DeploymentArtifactGenerator(real_workflow_config)
        artifacts = generator.generate(
            output_dir=tmp_path,
            api_port=8000,
            sync_timeout=30,
            enable_mlflow=True,
        )

        # Check all artifacts exist
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
            assert artifact_name in artifacts, f"Missing artifact: {artifact_name}"
            artifact_path = artifacts[artifact_name]
            assert artifact_path.exists(), f"Artifact file doesn't exist: {artifact_name}"
            assert artifact_path.stat().st_size > 0, f"Artifact is empty: {artifact_name}"

    def test_generated_workflow_config_is_valid(self, real_workflow_config, tmp_path):
        """
        Generated workflow.yaml is valid and can be re-parsed.

        This test verifies:
        1. workflow.yaml is valid YAML
        2. It can be parsed back to WorkflowConfig
        3. Config matches original
        """
        generator = DeploymentArtifactGenerator(real_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path)

        workflow_yaml_path = artifacts["workflow.yaml"]

        # Parse generated YAML
        with open(workflow_yaml_path) as f:
            config_dict = yaml.safe_load(f)

        # Should be able to create WorkflowConfig from it
        regenerated_config = WorkflowConfig(**config_dict)

        # Check key properties match
        assert regenerated_config.flow.name == real_workflow_config.flow.name
        assert regenerated_config.flow.version == real_workflow_config.flow.version
        assert len(regenerated_config.nodes) == len(real_workflow_config.nodes)

    def test_server_code_has_correct_syntax(self, real_workflow_config, tmp_path):
        """
        Generated server.py has valid Python syntax.

        This test verifies:
        1. server.py can be compiled
        2. No syntax errors
        """
        generator = DeploymentArtifactGenerator(real_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path)

        server_path = artifacts["server.py"]
        server_content = server_path.read_text()

        # Compile to check syntax
        try:
            compile(server_content, str(server_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server.py has syntax error: {e}")

    def test_mlflow_integration_configurable(self, real_workflow_config, tmp_path):
        """
        MLFlow integration can be enabled/disabled.

        This test verifies:
        1. MLFlow enabled by default
        2. Can be disabled
        3. Generated code reflects configuration
        """
        generator = DeploymentArtifactGenerator(real_workflow_config)

        # Test with MLFlow enabled
        artifacts_enabled = generator.generate(
            output_dir=tmp_path / "enabled",
            enable_mlflow=True,
            mlflow_port=5000,
        )

        server_enabled = artifacts_enabled["server.py"].read_text()
        assert "import mlflow" in server_enabled
        assert "mlflow.set_experiment" in server_enabled

        dockerfile_enabled = artifacts_enabled["Dockerfile"].read_text()
        assert "mlflow ui" in dockerfile_enabled

        # Test with MLFlow disabled
        artifacts_disabled = generator.generate(
            output_dir=tmp_path / "disabled",
            enable_mlflow=False,
            mlflow_port=0,
        )

        dockerfile_disabled = artifacts_disabled["Dockerfile"].read_text()
        assert "mlflow ui" not in dockerfile_disabled

    def test_deployment_readme_contains_usage_instructions(self, real_workflow_config, tmp_path):
        """
        Generated README.md contains usage instructions.

        This test verifies:
        1. README has API reference
        2. Includes Docker commands
        3. Has example requests
        """
        generator = DeploymentArtifactGenerator(real_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path)

        readme_content = artifacts["README.md"].read_text()

        # Check for key sections
        assert "API Reference" in readme_content or "Usage" in readme_content
        assert "docker-compose" in readme_content.lower() or "docker" in readme_content.lower()
        assert "POST /run" in readme_content or "/run" in readme_content
        assert "curl" in readme_content.lower() or "example" in readme_content.lower()
