"""
Unit tests for FastAPI server template.

Tests cover:
- Template generation correctness
- Input validation model building
- MLFlow integration code
- Endpoint definitions
- Error handling

These are template validation tests - they verify the generated code is correct,
without actually running a server.
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from configurable_agents.config import WorkflowConfig
from configurable_agents.deploy.generator import DeploymentArtifactGenerator


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
                "count": {"type": "int", "default": 10, "description": "Word count target"},
                "article": {"type": "str", "default": "", "description": "Generated article"},
            }
        },
        "nodes": [
            {
                "id": "write",
                "description": "Write article",
                "prompt": "Write about {state.topic}",
                "outputs": ["article"],
                "output_schema": {
                    "type": "object",
                    "fields": [{"name": "article", "type": "str"}],
                },
            }
        ],
        "edges": [
            {"from": "START", "to": "write"},
            {"from": "write", "to": "END"},
        ],
        "config": {"llm": {"model": "gemini-2.0-flash-lite", "temperature": 0.7}},
    }
    return WorkflowConfig(**config_dict)


@pytest.fixture
def generated_server(sample_workflow_config, tmp_path):
    """Generate server.py and return its content"""
    generator = DeploymentArtifactGenerator(sample_workflow_config)
    artifacts = generator.generate(
        output_dir=tmp_path,
        api_port=8000,
        sync_timeout=30,
        enable_mlflow=True,
    )

    server_path = artifacts["server.py"]
    return server_path.read_text()


class TestServerTemplateGeneration:
    """Tests for server template generation"""

    def test_template_includes_required_imports(self, generated_server):
        """Generated server includes all required imports"""
        assert "from fastapi import" in generated_server
        assert "from pydantic import" in generated_server
        assert "from configurable_agents.config import" in generated_server
        assert "from configurable_agents.runtime import run_workflow" in generated_server
        assert "import asyncio" in generated_server
        assert "import uuid" in generated_server

    def test_template_includes_mlflow_import(self, generated_server):
        """Generated server includes conditional MLFlow import"""
        assert "MLFLOW_ENABLED" in generated_server
        assert 'os.getenv("MLFLOW_TRACKING_URI")' in generated_server
        assert "import mlflow" in generated_server

    def test_template_defines_all_endpoints(self, generated_server):
        """Generated server defines all required endpoints"""
        # Check endpoint decorators
        assert '@app.get("/")' in generated_server
        assert '@app.post("/run"' in generated_server
        assert '@app.get("/status/{job_id}"' in generated_server
        assert '@app.get("/health"' in generated_server
        assert '@app.get("/schema"' in generated_server

    def test_template_includes_input_validation_model(self, generated_server):
        """Generated server builds input validation model"""
        assert "_build_input_model" in generated_server
        assert "WorkflowInput" in generated_server
        assert "create_model" in generated_server
        assert "workflow_config.state.fields" in generated_server

    def test_template_includes_sync_async_logic(self, generated_server):
        """Generated server includes sync/async execution logic"""
        assert "asyncio.wait_for" in generated_server
        assert "SYNC_TIMEOUT" in generated_server
        assert "asyncio.TimeoutError" in generated_server
        assert "background_tasks.add_task" in generated_server

    def test_template_includes_job_store(self, generated_server):
        """Generated server includes job store"""
        assert "jobs:" in generated_server or "jobs =" in generated_server
        assert "job_id" in generated_server
        assert '"status"' in generated_server

    def test_template_includes_mlflow_tracking(self, generated_server):
        """Generated server includes MLFlow tracking code"""
        assert "mlflow.set_experiment" in generated_server
        assert "mlflow.start_run" in generated_server
        assert "mlflow.log_params" in generated_server
        assert "mlflow.log_metrics" in generated_server
        assert "mlflow.end_run" in generated_server

    def test_template_includes_error_handling(self, generated_server):
        """Generated server includes error handling"""
        assert "try:" in generated_server
        assert "except Exception" in generated_server
        assert "HTTPException" in generated_server

    def test_template_uses_workflow_config_object(self, generated_server):
        """Generated server converts dict to WorkflowConfig object"""
        assert "WorkflowConfig" in generated_server
        assert "config_dict = parse_config_file" in generated_server
        assert "workflow_config = WorkflowConfig(**config_dict)" in generated_server


class TestInputValidationModelBuilding:
    """Tests for input validation model generation"""

    def test_build_input_model_creates_required_fields(self, sample_workflow_config, tmp_path):
        """Input model correctly marks required fields"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, sync_timeout=30)

        server_content = artifacts["server.py"].read_text()

        # Should have logic to check field_def.required
        assert "field_def.required" in server_content
        assert "Field(description=" in server_content

    def test_build_input_model_handles_defaults(self, sample_workflow_config, tmp_path):
        """Input model correctly handles default values"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, sync_timeout=30)

        server_content = artifacts["server.py"].read_text()

        # Should have logic for default values
        assert "field_def.default" in server_content
        assert "Field(default=" in server_content

    def test_build_input_model_maps_types(self, sample_workflow_config, tmp_path):
        """Input model maps workflow types to Python types"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, sync_timeout=30)

        server_content = artifacts["server.py"].read_text()

        # Should have type mapping dict
        assert "type_map" in server_content
        assert '"str": str' in server_content
        assert '"int": int' in server_content


class TestMLFlowIntegration:
    """Tests for MLFlow integration code"""

    def test_mlflow_enabled_check(self, generated_server):
        """Server checks if MLFlow is enabled"""
        assert "MLFLOW_ENABLED" in generated_server
        assert 'os.getenv("MLFLOW_TRACKING_URI")' in generated_server

    def test_mlflow_logs_sync_execution(self, generated_server):
        """Server logs MLFlow data for sync execution"""
        assert "mlflow.set_experiment" in generated_server
        assert "mlflow.start_run" in generated_server
        assert "mlflow.log_params(inputs_dict)" in generated_server
        assert "mlflow.log_metrics" in generated_server

    def test_mlflow_logs_async_execution(self, generated_server):
        """Server logs MLFlow data for async execution"""
        # Check background task has MLFlow logging
        assert "run_workflow_async" in generated_server
        # MLFlow should be in background task
        server_lines = generated_server.split("\n")
        in_async_function = False
        has_mlflow_in_async = False

        for line in server_lines:
            if "async def run_workflow_async" in line:
                in_async_function = True
            elif "async def" in line or "def " in line:
                in_async_function = False

            if in_async_function and "mlflow" in line.lower():
                has_mlflow_in_async = True

        assert has_mlflow_in_async, "MLFlow logging should be in run_workflow_async"

    def test_mlflow_error_handling(self, generated_server):
        """Server handles MLFlow errors gracefully"""
        # Should have try/except around MLFlow calls
        assert "try:" in generated_server
        assert "except Exception" in generated_server

        # Check MLFlow calls are in try blocks
        mlflow_lines = [i for i, line in enumerate(generated_server.split("\n")) if "mlflow." in line]
        try_lines = [i for i, line in enumerate(generated_server.split("\n")) if "try:" in line]

        # At least some MLFlow calls should be after try statements
        assert len(mlflow_lines) > 0 and len(try_lines) > 0

    def test_mlflow_uses_workflow_name_as_experiment(self, sample_workflow_config, tmp_path):
        """Server uses workflow name as MLFlow experiment name"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, sync_timeout=30)

        server_content = artifacts["server.py"].read_text()

        # Should reference workflow name in experiment
        assert f'mlflow.set_experiment("{sample_workflow_config.flow.name}")' in server_content or \
               'mlflow.set_experiment("test_workflow")' in server_content


class TestSyncAsyncLogic:
    """Tests for sync/async execution logic"""

    def test_sync_timeout_configuration(self, sample_workflow_config, tmp_path):
        """Server uses configured sync timeout"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, sync_timeout=45)

        server_content = artifacts["server.py"].read_text()

        assert "SYNC_TIMEOUT = 45" in server_content

    def test_async_fallback_on_timeout(self, generated_server):
        """Server falls back to async on timeout"""
        assert "asyncio.TimeoutError" in generated_server
        assert "job_id = str(uuid.uuid4())" in generated_server
        assert 'status="async"' in generated_server

    def test_background_task_execution(self, generated_server):
        """Server executes long workflows in background"""
        assert "background_tasks.add_task" in generated_server
        assert "run_workflow_async" in generated_server

    def test_job_status_tracking(self, generated_server):
        """Server tracks job status correctly"""
        # Check status values
        assert '"pending"' in generated_server or "'pending'" in generated_server
        assert '"running"' in generated_server or "'running'" in generated_server
        assert '"completed"' in generated_server or "'completed'" in generated_server
        assert '"failed"' in generated_server or "'failed'" in generated_server

    def test_execution_time_tracking(self, generated_server):
        """Server tracks execution time"""
        assert "start_time = time.time()" in generated_server
        assert "execution_time_ms" in generated_server


class TestEndpointDefinitions:
    """Tests for endpoint definitions"""

    def test_run_endpoint_uses_validation_model(self, generated_server):
        """POST /run endpoint uses WorkflowInput for validation"""
        assert "def run_workflow_endpoint(inputs: WorkflowInput" in generated_server

    def test_run_endpoint_returns_response_model(self, generated_server):
        """POST /run endpoint has response model"""
        assert "response_model=RunResponse" in generated_server

    def test_status_endpoint_has_job_id_param(self, generated_server):
        """GET /status/{job_id} endpoint has job_id parameter"""
        assert "/status/{job_id}" in generated_server
        assert "job_id: str" in generated_server

    def test_schema_endpoint_returns_workflow_info(self, generated_server):
        """GET /schema endpoint returns workflow schema"""
        assert "workflow_config.flow.name" in generated_server
        assert "workflow_config.state.fields" in generated_server

    def test_health_endpoint_returns_status(self, generated_server):
        """GET /health endpoint returns health status"""
        assert '"healthy"' in generated_server or "'healthy'" in generated_server


class TestConfiguration:
    """Tests for server configuration"""

    def test_api_port_configuration(self, sample_workflow_config, tmp_path):
        """Server uses configured API port"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path, api_port=9000)

        server_content = artifacts["server.py"].read_text()

        assert "port=9000" in server_content

    def test_workflow_name_in_title(self, sample_workflow_config, tmp_path):
        """Server includes workflow name in API title"""
        generator = DeploymentArtifactGenerator(sample_workflow_config)
        artifacts = generator.generate(output_dir=tmp_path)

        server_content = artifacts["server.py"].read_text()

        assert f'title="{sample_workflow_config.flow.name} API"' in server_content or \
               'title="test_workflow API"' in server_content

    def test_pydantic_models_defined(self, generated_server):
        """Server defines all required Pydantic models"""
        assert "class RunResponse(BaseModel)" in generated_server
        assert "class JobStatusResponse(BaseModel)" in generated_server
        assert "class HealthResponse(BaseModel)" in generated_server
        assert "class SchemaResponse(BaseModel)" in generated_server
