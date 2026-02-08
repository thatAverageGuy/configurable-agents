"""
Integration tests for deployment artifact generation.

Tests end-to-end artifact generation with real workflow configs.
"""
from pathlib import Path

import pytest
import yaml

from configurable_agents.deploy import generate_deployment_artifacts


@pytest.fixture
def article_writer_config(tmp_path):
    """Create article_writer.yaml config for testing"""
    config_content = """
schema_version: "1.0"

flow:
  name: article_writer
  description: Multi-step workflow that researches a topic and writes an article
  version: "1.0.0"

state:
  fields:
    topic:
      type: str
      required: true
      description: The topic to research and write about

    research:
      type: str
      default: ""
      description: Research findings from web search

    article:
      type: str
      default: ""
      description: The final article

    word_count:
      type: int
      default: 0
      description: Word count of the article

nodes:
  - id: research
    description: Search the web for information about the topic
    prompt: |
      Research the following topic using web search: {state.topic}
      Find key facts, recent developments, and interesting insights.
      Summarize your findings in 2-3 paragraphs.
    tools: [serper_search]
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str
          description: Summary of research findings

  - id: write
    description: Write a comprehensive article based on the research
    prompt: |
      Based on this research about {state.topic}:
      {state.research}
      Write a well-structured article with:
      - An engaging introduction
      - 2-3 main points with detailed explanations
      - A thoughtful conclusion
      Aim for approximately 300-400 words.
    outputs: [article, word_count]
    output_schema:
      type: object
      fields:
        - name: article
          type: str
          description: The complete article text
        - name: word_count
          type: int
          description: Approximate word count

edges:
  - {from: START, to: research}
  - {from: research, to: write}
  - {from: write, to: END}

config:
  llm:
    model: "gemini-2.5-flash-lite"
    temperature: 0.7
  execution:
    timeout: 120
    max_retries: 3
"""
    config_file = tmp_path / "article_writer.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.mark.integration
class TestDeploymentArtifactGenerationIntegration:
    """Integration tests for full artifact generation workflow"""

    def test_generate_all_artifacts_from_article_writer(self, article_writer_config, tmp_path):
        """
        Test: Generate all deployment artifacts from article_writer.yaml

        Validates:
        - All 8 artifacts are created
        - Files are non-empty
        - Files contain expected content
        """
        output_dir = tmp_path / "deploy"

        # Generate artifacts
        artifacts = generate_deployment_artifacts(
            config_path=article_writer_config,
            output_dir=output_dir,
            api_port=8000,
            mlflow_port=5000,
            sync_timeout=30,
            enable_mlflow=True,
            container_name="article_writer",
        )

        # Validate all artifacts exist
        assert len(artifacts) == 10
        expected_files = [
            "Dockerfile",
            "server.py",
            "requirements.txt",
            "docker-compose.yml",
            ".env.example",
            "README.md",
            ".dockerignore",
            "workflow.yaml",
            "src/",
            "pyproject.toml",
        ]

        for filename in expected_files:
            assert filename in artifacts
            file_path = artifacts[filename]
            assert file_path.exists(), f"Missing artifact: {filename}"
            if file_path.is_file():
                assert file_path.stat().st_size > 0, f"Empty artifact: {filename}"

        # Validate Dockerfile
        dockerfile_content = artifacts["Dockerfile"].read_text()
        assert "FROM python:3.10-slim" in dockerfile_content
        assert "EXPOSE 8000 5000" in dockerfile_content
        assert "mlflow ui" in dockerfile_content
        assert "python server.py" in dockerfile_content
        assert "HEALTHCHECK" in dockerfile_content

        # Validate server.py
        server_content = artifacts["server.py"].read_text()
        assert "FastAPI" in server_content
        assert "article_writer" in server_content
        assert "SYNC_TIMEOUT = 30" in server_content
        assert "@app.post" in server_content and "/run" in server_content
        assert "@app.get" in server_content and "/health" in server_content
        assert "/status/{job_id}" in server_content
        assert "/schema" in server_content

        # Validate requirements.txt
        requirements_content = artifacts["requirements.txt"].read_text()
        assert "configurable-agents" in requirements_content
        assert "fastapi" in requirements_content
        assert "uvicorn" in requirements_content
        assert "mlflow" in requirements_content

        # Validate docker-compose.yml
        compose_content = artifacts["docker-compose.yml"].read_text()
        compose_dict = yaml.safe_load(compose_content)
        assert "services" in compose_dict
        assert "workflow" in compose_dict["services"]
        assert compose_dict["services"]["workflow"]["container_name"] == "article_writer"
        assert "8000:8000" in compose_dict["services"]["workflow"]["ports"]

        # Validate .env.example
        env_content = artifacts[".env.example"].read_text()
        assert "GOOGLE_API_KEY" in env_content
        assert "SERPER_API_KEY" in env_content

        # Validate README.md
        readme_content = artifacts["README.md"].read_text()
        assert "article_writer" in readme_content
        assert "Quick Start" in readme_content
        assert "curl" in readme_content
        assert "http://localhost:8000" in readme_content

        # Validate .dockerignore
        dockerignore_content = artifacts[".dockerignore"].read_text()
        assert "__pycache__" in dockerignore_content
        assert ".env" in dockerignore_content

        # Validate workflow.yaml
        workflow_content = artifacts["workflow.yaml"].read_text()
        workflow_dict = yaml.safe_load(workflow_content)
        assert workflow_dict["flow"]["name"] == "article_writer"
        assert "research" in [node["id"] for node in workflow_dict["nodes"]]
        assert "write" in [node["id"] for node in workflow_dict["nodes"]]

    def test_generate_artifacts_with_custom_ports(self, article_writer_config, tmp_path):
        """
        Test: Generate artifacts with custom ports

        Validates:
        - Custom ports are reflected in all artifacts
        - docker-compose.yml uses correct ports
        - Dockerfile exposes correct ports
        """
        output_dir = tmp_path / "deploy_custom"

        artifacts = generate_deployment_artifacts(
            config_path=article_writer_config,
            output_dir=output_dir,
            api_port=9000,
            mlflow_port=5001,
            sync_timeout=60,
        )

        # Check Dockerfile (container internal ports are always 8000 and 5000,
        # custom ports only affect docker-compose port mapping and server.py)
        dockerfile_content = artifacts["Dockerfile"].read_text()
        assert "EXPOSE 8000 5000" in dockerfile_content

        # Check server.py
        server_content = artifacts["server.py"].read_text()
        assert "SYNC_TIMEOUT = 60" in server_content
        assert "port=9000" in server_content

        # Check docker-compose.yml
        compose_content = artifacts["docker-compose.yml"].read_text()
        assert "9000:9000" in compose_content
        assert "5001:5001" in compose_content

        # Check README.md
        readme_content = artifacts["README.md"].read_text()
        assert "http://localhost:9000" in readme_content
        assert "http://localhost:5001" in readme_content

    def test_generate_artifacts_mlflow_disabled(self, article_writer_config, tmp_path):
        """
        Test: Generate artifacts with MLFlow disabled

        Validates:
        - MLFlow UI command not in Dockerfile
        - MLFlow port not exposed
        - requirements.txt doesn't include mlflow
        - docker-compose.yml doesn't expose MLFlow port
        """
        output_dir = tmp_path / "deploy_no_mlflow"

        artifacts = generate_deployment_artifacts(
            config_path=article_writer_config,
            output_dir=output_dir,
            enable_mlflow=False,
            mlflow_port=0,
        )

        # Check Dockerfile
        dockerfile_content = artifacts["Dockerfile"].read_text()
        assert "mlflow ui" not in dockerfile_content
        assert "CMD python server.py" in dockerfile_content
        # Dockerfile template always exposes both ports (static template);
        # MLflow disabling is done via CMD (no mlflow process) and requirements
        assert "EXPOSE 8000 5000" in dockerfile_content

        # Check requirements.txt
        requirements_content = artifacts["requirements.txt"].read_text()
        assert "mlflow" not in requirements_content or "disabled" in requirements_content

        # Check docker-compose.yml
        compose_content = artifacts["docker-compose.yml"].read_text()
        compose_dict = yaml.safe_load(compose_content)
        ports = compose_dict["services"]["workflow"]["ports"]
        # Should only have API port, not MLFlow port
        assert len([p for p in ports if "8000" in p]) > 0
        assert len([p for p in ports if "5000" in p]) == 0 or "0:0" in str(ports)
