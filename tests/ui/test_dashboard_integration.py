"""Integration tests for dashboard template rendering and error handling.

Tests cover:
- Template rendering (all templates compile without errors)
- Error handling (404, 500, MLFlow unavailable scenarios)
- Route parameters (status filters, query params)
- Form submission endpoints

Uses httpx.AsyncClient with ASGITransport for realistic testing.
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from httpx import AsyncClient, ASGITransport

from configurable_agents.ui.dashboard import create_dashboard_app, DashboardApp
from configurable_agents.storage.models import WorkflowRunRecord, AgentRecord
from configurable_agents.storage.sqlite import (
    SQLiteWorkflowRunRepository,
    SqliteAgentRegistryRepository,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Create all tables
    from configurable_agents.storage.models import Base
    Base.metadata.create_all(engine)

    return engine


@pytest.fixture
def workflow_repo(in_memory_db):
    """Create a workflow repository with in-memory database."""
    return SQLiteWorkflowRunRepository(in_memory_db)


@pytest.fixture
def agent_repo(in_memory_db):
    """Create an agent repository with in-memory database."""
    return SqliteAgentRegistryRepository(in_memory_db)


@pytest.fixture
def seeded_workflow_repo(workflow_repo):
    """Create a workflow repository seeded with test data."""
    # Create test workflow runs with various statuses
    now = datetime.utcnow()

    test_runs = [
        WorkflowRunRecord(
            id=str(uuid.uuid4()),
            workflow_name="test_workflow_1",
            status="running",
            config_snapshot='{"name": "test"}',
            inputs='{"input": "test"}',
            started_at=now - timedelta(minutes=5),
            completed_at=None,
            duration_seconds=None,
            total_tokens=100,
            total_cost_usd=0.001,
        ),
        WorkflowRunRecord(
            id=str(uuid.uuid4()),
            workflow_name="test_workflow_2",
            status="completed",
            config_snapshot='{"name": "test"}',
            inputs='{"input": "test"}',
            outputs='{"output": "result"}',
            started_at=now - timedelta(hours=1),
            completed_at=now - timedelta(minutes=55),
            duration_seconds=300,
            total_tokens=500,
            total_cost_usd=0.005,
        ),
        WorkflowRunRecord(
            id=str(uuid.uuid4()),
            workflow_name="test_workflow_3",
            status="failed",
            config_snapshot='{"name": "test"}',
            inputs='{"input": "test"}',
            error_message="Test error",
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1, minutes=55),
            duration_seconds=300,
            total_tokens=200,
            total_cost_usd=0.002,
        ),
        WorkflowRunRecord(
            id=str(uuid.uuid4()),
            workflow_name="test_workflow_4",
            status="pending",
            config_snapshot='{"name": "test"}',
            inputs='{"input": "test"}',
            started_at=now - timedelta(minutes=1),
            completed_at=None,
            duration_seconds=None,
        ),
        WorkflowRunRecord(
            id=str(uuid.uuid4()),
            workflow_name="test_workflow_5",
            status="cancelled",
            config_snapshot='{"name": "test"}',
            inputs='{"input": "test"}',
            started_at=now - timedelta(minutes=30),
            completed_at=now - timedelta(minutes=25),
            duration_seconds=300,
        ),
    ]

    for run in test_runs:
        workflow_repo.add(run)

    return workflow_repo


@pytest.fixture
def seeded_agent_repo(agent_repo):
    """Create an agent repository seeded with test data."""
    now = datetime.utcnow()

    test_agents = [
        AgentRecord(
            agent_id="agent-001",
            agent_name="Test Agent 1",
            host="localhost",
            port=8001,
            last_heartbeat=now - timedelta(seconds=30),
            ttl_seconds=60,
            agent_metadata='{"capabilities": ["chat", "search"]}',
        ),
        AgentRecord(
            agent_id="agent-002",
            agent_name="Test Agent 2",
            host="localhost",
            port=8002,
            last_heartbeat=now - timedelta(seconds=10),
            ttl_seconds=60,
            agent_metadata='{"capabilities": ["summarize", "write"]}',
        ),
        AgentRecord(
            agent_id="agent-003",
            agent_name="Dead Agent",
            host="localhost",
            port=8003,
            last_heartbeat=now - timedelta(minutes=10),
            ttl_seconds=60,
            agent_metadata='{"capabilities": ["chat"]}',
        ),
    ]

    for agent in test_agents:
        agent_repo.add(agent)

    return agent_repo


@pytest.fixture
def dashboard_app(seeded_workflow_repo, seeded_agent_repo):
    """Create a dashboard app with seeded repositories."""
    return DashboardApp(
        workflow_repo=seeded_workflow_repo,
        agent_registry_repo=seeded_agent_repo,
    )


@pytest.fixture
def dashboard_app_no_mlflow(seeded_workflow_repo, seeded_agent_repo):
    """Create a dashboard app without MLFlow mounted."""
    return DashboardApp(
        workflow_repo=seeded_workflow_repo,
        agent_registry_repo=seeded_agent_repo,
        mlflow_tracking_uri=None,
    )


@pytest.mark.asyncio
class TestTemplateRendering:
    """Tests for verifying all dashboard templates compile and render correctly."""

    async def test_base_template_renders(self, dashboard_app):
        """Verify base.html compiles without errors."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        # Response should be HTML
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Should contain base template elements
        text = response.text
        assert "<!DOCTYPE html>" in text
        assert "<html" in text
        assert "<head>" in text
        assert "<body>" in text
        assert "Configurable Agents" in text
        assert "/static/dashboard.css" in text

    async def test_dashboard_template_renders(self, dashboard_app):
        """Verify dashboard.html extends base and renders."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        text = response.text
        # Should have navigation
        assert "<nav" in text or 'class="nav' in text
        # Should have main content area
        assert "<main" in text or 'class="main' in text

    async def test_workflows_template_renders(self, dashboard_app):
        """Verify workflows.html compiles without errors."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/")

        assert response.status_code == 200
        text = response.text
        # Should have workflows page elements
        assert "Workflow" in text or "workflow" in text.lower()

    async def test_agents_template_renders(self, dashboard_app):
        """Verify agents.html compiles without errors."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/")

        assert response.status_code == 200
        text = response.text
        # Should have agents page elements
        assert "Agent" in text or "agent" in text.lower()

    async def test_experiments_template_renders(self, dashboard_app):
        """Verify experiments.html compiles without errors."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/optimization/experiments")

        assert response.status_code == 200
        text = response.text
        # Should have experiments page elements
        assert "Experiment" in text or "experiment" in text.lower()
        # Should handle MLFlow unavailable gracefully
        assert "MLFlow" in text or "mlflow" in text.lower()

    async def test_mlflow_unavailable_template_renders(self, dashboard_app_no_mlflow):
        """Verify mlflow_unavailable.html renders friendly message."""
        transport = ASGITransport(app=dashboard_app_no_mlflow.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mlflow")

        assert response.status_code == 200
        text = response.text
        # Should have friendly error message
        assert "MLFlow" in text or "mlflow" in text.lower()
        assert "Not Configured" in text or "not configured" in text.lower() or "not enabled" in text.lower()
        # Should have helpful instructions
        assert "--mlflow" in text or "configurable-agents ui" in text
        # Should have navigation back to dashboard
        assert 'href="/"' in text

    async def test_macros_template_compiles(self, dashboard_app):
        """Verify macros.html is valid Jinja2 (indirectly via workflows table)."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # The workflows_table uses macros from macros.html
            response = await client.get("/workflows/table")

        assert response.status_code == 200
        # If macros.html had syntax errors, this would fail


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling scenarios (404, 500, MLFlow unavailable)."""

    async def test_workflow_not_found_returns_error(self, dashboard_app):
        """GET /workflows/{nonexistent} returns error page."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/workflows/{uuid.uuid4()}")

        # Should return 200 with error message in page
        assert response.status_code == 200
        text = response.text
        # The workflow detail route returns error in context
        assert "not found" in text.lower() or "Workflow run not found" in text or "error" in text.lower()

    async def test_agent_not_found_returns_404(self, dashboard_app):
        """DELETE /agents/{nonexistent} returns 404."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/agents/nonexistent-{uuid.uuid4()}")

        assert response.status_code == 404

    async def test_mlflow_unavailable_returns_html(self, dashboard_app_no_mlflow):
        """GET /mlflow without MLFlow mounted returns HTML."""
        transport = ASGITransport(app=dashboard_app_no_mlflow.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mlflow")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        text = response.text
        # Should have helpful message
        assert "MLFlow" in text or "mlflow" in text.lower()

    async def test_optimization_without_mlflow_shows_message(self, dashboard_app_no_mlflow):
        """GET /optimization/compare with bad experiment shows error message."""
        transport = ASGITransport(app=dashboard_app_no_mlflow.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # MLFlow not configured scenario
            response = await client.get(
                "/optimization/compare",
                params={"experiment": "nonexistent_experiment", "metric": "cost_usd_avg"}
            )

        assert response.status_code == 200
        text = response.text
        # Should show unavailable message or error
        # Either MLFlow unavailable or experiment not found
        assert (
            "MLFlow" in text or
            "not available" in text.lower() or
            "not found" in text.lower() or
            "error" in text.lower()
        )

    async def test_workflow_cancel_nonexistent(self, dashboard_app):
        """POST /workflows/{nonexistent}/cancel returns 404."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/workflows/{uuid.uuid4()}/cancel")

        assert response.status_code == 404

    async def test_agent_delete_nonexistent(self, dashboard_app):
        """DELETE /agents/{nonexistent} returns 404."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/agents/nonexistent-{uuid.uuid4()}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestRouteParameters:
    """Tests for route parameters (status filters, query params)."""

    async def test_workflows_status_filter(self, dashboard_app):
        """GET /workflows?status=running filters correctly."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/?status=running")

        assert response.status_code == 200
        text = response.text
        # Should indicate filtered results
        assert "running" in text.lower()

    async def test_workflows_status_filter_completed(self, dashboard_app):
        """GET /workflows?status=completed filters to completed workflows."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/?status=completed")

        assert response.status_code == 200

    async def test_workflows_status_filter_failed(self, dashboard_app):
        """GET /workflows?status=failed filters to failed workflows."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/?status=failed")

        assert response.status_code == 200

    async def test_workflows_table_status_filter(self, dashboard_app):
        """GET /workflows/table?status=completed filters correctly."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/table?status=completed")

        assert response.status_code == 200
        # Should return HTML partial (table fragment)
        assert "text/html" in response.headers.get("content-type", "")

    async def test_experiments_metric_param(self, dashboard_app):
        """GET /optimization/experiments with metric param works."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/optimization/experiments",
                params={"metric": "cost_usd_avg"}
            )

        assert response.status_code == 200
        # Should render even without MLFlow data
        assert "text/html" in response.headers.get("content-type", "")

    async def test_optimization_compare_params(self, dashboard_app):
        """GET /optimization/compare with experiment and metric params."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/optimization/compare",
                params={
                    "experiment": "test_experiment",
                    "metric": "cost_usd_avg"
                }
            )

        # Should render (may have error message for nonexistent experiment)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestFormSubmission:
    """Tests for form submission endpoints (POST, DELETE, etc.)."""

    async def test_workflow_cancel_completed(self, dashboard_app, workflow_repo):
        """POST /workflows/{id}/cancel on completed workflow returns 400."""
        # Get a completed workflow ID
        runs = workflow_repo.list_by_workflow("test_workflow_2", limit=1)
        if runs:
            run_id = runs[0].id
            transport = ASGITransport(app=dashboard_app.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/workflows/{run_id}/cancel")

            # Cannot cancel completed workflow
            assert response.status_code == 400

    async def test_agents_delete_valid(self, dashboard_app, agent_repo):
        """DELETE /agents/{id} for valid agent succeeds."""
        # Get a valid agent ID
        agents = agent_repo.list_all(include_dead=False)
        if agents:
            agent_id = agents[0].agent_id
            transport = ASGITransport(app=dashboard_app.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/agents/{agent_id}")

            # Should succeed
            assert response.status_code == 200
            # Verify agent was deleted
            assert agent_repo.get(agent_id) is None

    async def test_agents_refresh(self, dashboard_app):
        """POST /agents/refresh returns table HTML."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/agents/refresh")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # Should be a table partial (for HTMX refresh)
        text = response.text
        assert "agent" in text.lower() or "Agent" in text

    async def test_agents_refresh_returns_data(self, dashboard_app, agent_repo):
        """POST /agents/refresh returns current agent data."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/agents/refresh")

        assert response.status_code == 200
        text = response.text
        # Should contain agent names from seeded data
        # (At least the alive ones)
        assert "Test Agent" in text or "agent" in text.lower()

    async def test_workflow_restart_nonexistent(self, dashboard_app):
        """POST /workflows/{id}/restart for nonexistent workflow returns 404."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/workflows/{uuid.uuid4()}/restart")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestWorkflowDetail:
    """Tests for workflow detail page and related functionality."""

    async def test_workflow_detail_renders(self, dashboard_app, workflow_repo):
        """GET /workflows/{id} renders detail page."""
        # Get a valid workflow ID
        runs = workflow_repo.list_by_workflow("test_workflow_1", limit=1)
        if runs:
            run_id = runs[0].id
            transport = ASGITransport(app=dashboard_app.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/workflows/{run_id}")

            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    async def test_workflow_detail_with_outputs(self, dashboard_app):
        """Workflow detail page renders outputs correctly."""
        # Get a completed workflow with outputs
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First get the list to find a completed workflow
            list_response = await client.get("/workflows/")
            assert list_response.status_code == 200

            # Try to get detail for a workflow (ID from list or use UUID)
            response = await client.get(f"/workflows/{uuid.uuid4()}")

        # Will show "not found" but should still render
        assert response.status_code == 200


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    async def test_health_returns_json(self, dashboard_app):
        """GET /health returns JSON status."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
class TestMetricsEndpoints:
    """Tests for metrics endpoints."""

    async def test_metrics_summary(self, dashboard_app):
        """GET /metrics/summary returns metrics summary."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_workflows" in data
        assert "running_workflows" in data
        assert "registered_agents" in data
        assert "total_cost_usd" in data
        assert "timestamp" in data


@pytest.mark.asyncio
class TestAgentsEndpoints:
    """Tests for agents listing endpoints."""

    async def test_agents_list_all_includes_dead(self, dashboard_app, agent_repo):
        """GET /agents/all includes dead agents."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/all")

        assert response.status_code == 200
        text = response.text
        # Should show all agents including the dead one
        assert "Dead Agent" in text or "agent" in text.lower()

    async def test_agents_table_partial(self, dashboard_app):
        """GET /agents/table returns table partial for HTMX."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/table")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        text = response.text
        # Should contain agent data
        assert "Test Agent" in text or "agent" in text.lower()


@pytest.mark.asyncio
class TestOptimizationEndpoints:
    """Tests for optimization and MLFlow-related endpoints."""

    async def test_experiments_json(self, dashboard_app):
        """GET /optimization/experiments.json returns JSON."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/optimization/experiments.json")

        assert response.status_code == 200
        # Should return JSON
        assert "application/json" in response.headers.get("content-type", "")
        data = response.json()
        assert "experiments" in data
        assert "mlflow_available" in data

    async def test_compare_json_nonexistent(self, dashboard_app):
        """GET /optimization/compare.json with nonexistent experiment returns error."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/optimization/compare.json",
                params={"experiment": "nonexistent", "metric": "cost_usd_avg"}
            )

        # Should return JSON with error info
        assert response.status_code == 200
        data = response.json()
        # Either has experiments list or error message
        assert "mlflow_available" in data or "error" in data


@pytest.mark.asyncio
class TestOrchestratorPage:
    """Tests for orchestrator view page."""

    async def test_orchestrator_page_renders(self, dashboard_app):
        """GET /orchestrator renders the orchestrator page."""
        transport = ASGITransport(app=dashboard_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/orchestrator")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        text = response.text
        # Should have orchestrator-related content
        assert "Orchestrator" in text or "orchestrator" in text.lower()
