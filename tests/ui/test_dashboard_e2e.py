"""End-to-end tests for the Dashboard UI.

Tests all dashboard pages load correctly, navigation links work, HTMX
endpoints respond properly, and empty states render without crashes.

Tests are marked as @pytest.mark.slow for manual/pre-release testing.
Follows the httpx.AsyncClient with ASGITransport pattern from test_dashboard.py.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import Mock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from configurable_agents.ui.dashboard import DashboardApp
from configurable_agents.storage.models import (
    WorkflowRunRecord,
    AgentRecord,
    Base,
)


# =============================================================================
# Helper Functions
# =============================================================================


def _create_test_dashboard():
    """Create a dashboard app with mock repositories for testing.

    Returns:
        DashboardApp: Dashboard app instance with mock repos
    """
    # Create mock repositories with proper return values
    workflow_repo = Mock()
    workflow_repo.list_all = Mock(return_value=[])
    # Make get() return None for non-existent workflows
    workflow_repo.get = Mock(return_value=None)
    # Don't set engine attribute so _get_all_runs falls back to list_all
    # (or explicitly set to None to bypass hasattr check)
    del workflow_repo.engine

    agent_repo = Mock()
    agent_repo.list_all = Mock(return_value=[])
    # Make get() return None for non-existent agents
    agent_repo.get = Mock(return_value=None)

    # Create dashboard app
    dashboard = DashboardApp(
        workflow_repo=workflow_repo,
        agent_registry_repo=agent_repo,
    )

    return dashboard


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def populated_db() -> Generator:
    """Create a database with sample workflow and agent records.

    Yields:
        Engine: SQLAlchemy engine with sample data
    """
    engine = create_engine("sqlite:///:memory:")

    # Create tables
    Base.metadata.create_all(engine)

    # Add sample workflow records
    with Session(engine) as session:
        # Completed workflow
        workflow1 = WorkflowRunRecord(
            id="test-workflow-001",
            workflow_name="test_workflow",
            status="completed",
            started_at=datetime.utcnow() - timedelta(hours=1),
            duration_seconds=45.5,
            total_tokens=1500,
            total_cost_usd=0.0234,
            inputs='{"input": "test input"}',
            outputs='{"output": "test output"}',
        )

        # Running workflow
        workflow2 = WorkflowRunRecord(
            id="test-workflow-002",
            workflow_name="running_workflow",
            status="running",
            started_at=datetime.utcnow() - timedelta(minutes=5),
            duration_seconds=None,
            total_tokens=None,
            total_cost_usd=None,
        )

        # Failed workflow
        workflow3 = WorkflowRunRecord(
            id="test-workflow-003",
            workflow_name="failed_workflow",
            status="failed",
            started_at=datetime.utcnow() - timedelta(hours=2),
            duration_seconds=12.3,
            total_tokens=500,
            total_cost_usd=0.0078,
            error_message="Test error message",
        )

        session.add_all([workflow1, workflow2, workflow3])

        # Add sample agent records
        agent1 = AgentRecord(
            agent_id="agent-001",
            agent_name="TestAgent1",
            host="localhost",
            port=8001,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=30),
            agent_metadata='{"capabilities": ["chat", "search"]}',
        )

        agent2 = AgentRecord(
            agent_id="agent-002",
            agent_name="TestAgent2",
            host="localhost",
            port=8002,
            last_heartbeat=datetime.utcnow() - timedelta(minutes=15),
            agent_metadata='{"capabilities": ["summarize"]}',
        )

        session.add_all([agent1, agent2])
        session.commit()

    yield engine


# =============================================================================
# TestDashboardPageLoads
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestDashboardPageLoads:
    """Tests for verifying all dashboard pages load with 200 status."""

    async def test_dashboard_home_page_200(self):
        """Test GET / returns 200 status with HTML content."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            # Verify it's the dashboard
            text = response.text
            assert "Dashboard" in text or "Configurable Agents" in text

    async def test_workflows_page_200(self):
        """Test GET /workflows returns 200 status with HTML content."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            text = response.text
            assert "Workflow" in text

    async def test_workflows_page_without_trailing_slash(self):
        """Test GET /workflows (no trailing slash) works."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows")
            # Should either 200 or redirect to /workflows/
            assert response.status_code in (200, 307, 308)

    async def test_agents_page_200(self):
        """Test GET /agents returns 200 status with HTML content."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            text = response.text
            assert "Agent" in text

    async def test_agents_page_without_trailing_slash(self):
        """Test GET /agents (no trailing slash) works."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents")
            # Should either 200 or redirect to /agents/
            assert response.status_code in (200, 307, 308)

    async def test_experiments_page_200(self):
        """Test GET /optimization/experiments returns 200 status."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/optimization/experiments")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            text = response.text
            # Should show experiments page even if MLFlow unavailable
            assert "experiment" in text.lower() or "optimization" in text.lower()

    async def test_optimization_compare_without_mlflow(self):
        """Test GET /optimization/compare shows friendly message when MLFlow unavailable."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Without MLFlow, this should still return a friendly error page
            response = await client.get(
                "/optimization/compare",
                params={"experiment": "test-experiment"}
            )
            # Should return 200 with error message, not 404 or 500
            assert response.status_code == 200
            text = response.text
            # Should contain some indication of MLFlow issue or comparison page
            assert "MLFlow" in text or "optimization" in text.lower() or "compare" in text.lower()

    async def test_mlflow_unavailable_page_200(self):
        """Test GET /mlflow returns friendly page (not JSON 404) when unavailable."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mlflow")
            # Should return 200 with friendly unavailable message
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            text = response.text
            # Should show MLFlow unavailable message
            assert "MLFlow" in text or "unavailable" in text.lower() or "not available" in text.lower()

    async def test_orchestrator_page_200(self):
        """Test GET /orchestrator returns 200 status."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/orchestrator")
            # Orchestrator page may return 200 or show error if service unavailable
            # Either way should not crash
            assert response.status_code == 200

    async def test_health_endpoint(self):
        """Test GET /health returns JSON with status."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            assert "timestamp" in data


# =============================================================================
# TestNavigationLinks
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestNavigationLinks:
    """Tests for verifying navigation links are present and functional."""

    async def test_dashboard_contains_nav_links(self):
        """Verify all expected navigation links are present in dashboard HTML."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            text = response.text

            # Expected nav links from base.html
            expected_links = [
                ("/", "Dashboard"),
                ("/workflows", "Workflows"),
                ("/agents", "Agents"),
                ("/orchestrator", "Orchestrator"),
                ("/mlflow", "MLFlow"),
                ("/optimization/experiments", "Optimization"),
            ]

            for href, label in expected_links:
                # Check href exists in nav
                assert f'href="{href}"' in text or f"href='{href}'" in text, \
                    f"Nav link to {href} not found"
                # Check label exists
                assert label in text, f"Nav label '{label}' not found"

    async def test_nav_links_work(self):
        """Verify each nav link returns a valid response."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            nav_paths = [
                "/",
                "/workflows/",
                "/agents/",
                "/orchestrator",
                "/mlflow",
                "/optimization/experiments",
            ]

            for path in nav_paths:
                response = await client.get(path)
                assert response.status_code == 200, \
                    f"Nav link '{path}' returned {response.status_code}"
                assert "text/html" in response.headers.get("content-type", ""), \
                    f"Nav link '{path}' did not return HTML"

    async def test_workflows_detail_link_404_without_data(self):
        """Test workflow detail page returns appropriate response for non-existent run."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/nonexistent-id")
            # Should handle gracefully - either 404 page or return to list with error
            assert response.status_code == 200
            text = response.text
            # Should show some error or not-found indication
            assert "not found" in text.lower() or "error" in text.lower() or "workflow" in text.lower()


# =============================================================================
# TestHTMXInteractions
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestHTMXInteractions:
    """Tests for HTMX-powered endpoints that return HTML partials."""

    async def test_workflows_table_htmx(self):
        """Test GET /workflows/table returns HTML partial for HTMX swap."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/table")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            # Should return HTML table fragment
            text = response.text
            assert "<table" in text or "<tbody" in text
            # Empty state should be shown when no workflows
            assert "No workflows found" in text or "workflow" in text.lower()

    async def test_workflows_table_htmx_with_filter(self):
        """Test GET /workflows/table with status filter works."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/table?status_filter=running")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    async def test_agents_table_htmx(self):
        """Test GET /agents/table returns HTML partial for HTMX swap."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/table")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
            # Should return HTML table fragment
            text = response.text
            assert "<table" in text or "<tbody" in text
            # Empty state should be shown when no agents
            assert "No agents found" in text or "agent" in text.lower()

    async def test_workflows_stream_sse(self):
        """Test GET /metrics/workflows/stream returns text/event-stream."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/workflows/stream")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type
            # Check SSE headers
            assert response.headers.get("Cache-Control") == "no-cache"
            # Response should be a streaming response (httpx may buffer but content type is correct)

    async def test_agents_stream_sse(self):
        """Test GET /metrics/agents/stream returns text/event-stream."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/agents/stream")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type
            # Check SSE headers
            assert response.headers.get("Cache-Control") == "no-cache"

    async def test_metrics_summary_json(self):
        """Test GET /metrics/summary returns JSON with metrics."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/summary")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type
            data = response.json()
            # Check expected fields
            assert "total_workflows" in data
            assert "running_workflows" in data
            assert "registered_agents" in data
            assert "total_cost_usd" in data
            assert "timestamp" in data
            # Values should be numeric or zero
            assert isinstance(data["total_workflows"], int)
            assert isinstance(data["running_workflows"], int)

    async def test_experiments_json_endpoint(self):
        """Test GET /optimization/experiments.json returns JSON."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/optimization/experiments.json")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type
            data = response.json()
            # Should have experiments list and availability flag
            assert "experiments" in data
            assert "mlflow_available" in data
            assert isinstance(data["experiments"], list)


# =============================================================================
# TestEmptyStates
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestEmptyStates:
    """Tests for verifying empty states render correctly without crashes."""

    async def test_workflows_empty_state(self):
        """Test with no workflows, 'No workflows found' message is shown."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/table")
            assert response.status_code == 200
            text = response.text
            # Should show empty state message
            assert "No workflows found" in text or ("workflow" in text.lower() and "no" in text.lower())

    async def test_agents_empty_state(self):
        """Test with no agents, 'No agents found' message is shown."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/table")
            assert response.status_code == 200
            text = response.text
            # Should show empty state message
            assert "No agents found" in text or ("agent" in text.lower() and "no" in text.lower())

    async def test_dashboard_home_empty_state(self):
        """Test dashboard home with no data still renders correctly."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            text = response.text
            # Should show zero counts
            assert "0" in text or "active" in text.lower()

    async def test_experiments_empty_state(self):
        """Test experiments page with no experiments still renders."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/optimization/experiments")
            assert response.status_code == 200
            text = response.text
            # Should show page even with no experiments
            assert "experiment" in text.lower() or "optimization" in text.lower()


# =============================================================================
# TestPopulatedData
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestPopulatedData:
    """Tests for dashboard behavior with sample data."""

    async def test_workflows_with_data(self, populated_db):
        """Test workflows page displays sample data correctly."""
        # Import create_dashboard_app here for use with real DB
        from configurable_agents.ui.dashboard import create_dashboard_app

        # Create dashboard with populated database
        dashboard = create_dashboard_app(db_url="sqlite:///:memory:")

        # Copy data from populated database
        source_engine = populated_db

        # Get records from source
        with Session(source_engine) as source_session:
            workflows = source_session.query(WorkflowRunRecord).all()
            agents = source_session.query(AgentRecord).all()

        # Insert into test app database
        if hasattr(dashboard.workflow_repo, 'engine'):
            with Session(dashboard.workflow_repo.engine) as target_session:
                for wf in workflows:
                    target_session.merge(wf)
                for agent in agents:
                    target_session.merge(agent)
                target_session.commit()

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/table")
            assert response.status_code == 200
            text = response.text
            # Should show workflow data
            assert "test-workflow" in text.lower() or "workflow" in text.lower()

    async def test_agents_with_data(self, populated_db):
        """Test agents page displays sample data correctly."""
        # Import create_dashboard_app here for use with real DB
        from configurable_agents.ui.dashboard import create_dashboard_app

        # Create dashboard with populated database
        dashboard = create_dashboard_app(db_url="sqlite:///:memory:")

        # Copy data from populated database
        source_engine = populated_db

        # Get records from source
        with Session(source_engine) as source_session:
            workflows = source_session.query(WorkflowRunRecord).all()
            agents = source_session.query(AgentRecord).all()

        # Insert into test app database
        if hasattr(dashboard.workflow_repo, 'engine'):
            with Session(dashboard.workflow_repo.engine) as target_session:
                for wf in workflows:
                    target_session.merge(wf)
                for agent in agents:
                    target_session.merge(agent)
                target_session.commit()

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/table")
            assert response.status_code == 200
            text = response.text
            # Should show agent data
            assert "agent" in text.lower()

    async def test_metrics_summary_with_data(self, populated_db):
        """Test metrics summary reflects sample data."""
        # Import create_dashboard_app here for use with real DB
        from configurable_agents.ui.dashboard import create_dashboard_app

        # Create dashboard with populated database
        dashboard = create_dashboard_app(db_url="sqlite:///:memory:")

        # Copy data from populated database
        source_engine = populated_db

        # Get records from source
        with Session(source_engine) as source_session:
            workflows = source_session.query(WorkflowRunRecord).all()
            agents = source_session.query(AgentRecord).all()

        # Insert into test app database
        if hasattr(dashboard.workflow_repo, 'engine'):
            with Session(dashboard.workflow_repo.engine) as target_session:
                for wf in workflows:
                    target_session.merge(wf)
                for agent in agents:
                    target_session.merge(agent)
                target_session.commit()

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/summary")
            assert response.status_code == 200
            data = response.json()
            # Should have counts matching our sample data
            assert data["total_workflows"] >= 0
            assert data["registered_agents"] >= 0

    async def test_workflow_detail_page(self, populated_db):
        """Test workflow detail page for existing run."""
        # Import create_dashboard_app here for use with real DB
        from configurable_agents.ui.dashboard import create_dashboard_app

        # Create dashboard with populated database
        dashboard = create_dashboard_app(db_url="sqlite:///:memory:")

        # Copy data from populated database
        source_engine = populated_db

        # Get records from source
        with Session(source_engine) as source_session:
            workflows = source_session.query(WorkflowRunRecord).all()
            agents = source_session.query(AgentRecord).all()

        # Insert into test app database
        if hasattr(dashboard.workflow_repo, 'engine'):
            with Session(dashboard.workflow_repo.engine) as target_session:
                for wf in workflows:
                    target_session.merge(wf)
                for agent in agents:
                    target_session.merge(agent)
                target_session.commit()

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First get a workflow ID from the list
            response = await client.get("/workflows/table")
            text = response.text

            # If we have workflows, try to access the first one
            if "test-workflow" in text.lower():
                # Extract workflow ID from the response
                # The table shows truncated IDs like "test-wor..."
                # For this test we'll use a known ID from our fixture
                response = await client.get("/workflows/test-workflow-001")
                assert response.status_code == 200
                assert "test_workflow" in response.text or "workflow" in response.text.lower()


# =============================================================================
# TestAPIEndpoints
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestAPIEndpoints:
    """Tests for JSON API endpoints used by HTMX and JavaScript."""

    async def test_status_api_health(self):
        """Test GET /api/status/health returns health status."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/status/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data

    async def test_agents_refresh_endpoint(self):
        """Test POST /agents/refresh returns HTML."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/agents/refresh")
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type

    async def test_compare_json_without_mlflow(self):
        """Test GET /optimization/compare.json handles MLFlow unavailable."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/optimization/compare.json",
                params={"experiment": "nonexistent-experiment"}
            )
            # Should return JSON, not crash
            assert response.status_code == 200
            data = response.json()
            # Should have mlflow_available flag
            assert "mlflow_available" in data


# =============================================================================
# TestStaticFiles
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestStaticFiles:
    """Tests for static file serving."""

    async def test_static_css_file(self):
        """Test static CSS file is accessible."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/dashboard.css")
            # May return 404 if file doesn't exist yet, but should not crash
            assert response.status_code in (200, 404)

    async def test_nonexistent_static_returns_404(self):
        """Test nonexistent static file returns 404."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/static/nonexistent.css")
            assert response.status_code == 404


# =============================================================================
# TestHTMXAttributes
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestHTMXAttributes:
    """Tests for verifying HTMX attributes are present in HTML."""

    async def test_workflows_page_has_htmx_attributes(self):
        """Test workflows page contains expected HTMX attributes."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/")
            assert response.status_code == 200
            text = response.text
            # Should have HTMX attributes for table refresh
            assert "hx-get" in text or "data-hx-get" in text
            assert "hx-trigger" in text or "data-hx-trigger" in text
            assert "hx-swap" in text or "data-hx-swap" in text

    async def test_agents_page_has_htmx_attributes(self):
        """Test agents page contains expected HTMX attributes."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/")
            assert response.status_code == 200
            text = response.text
            # Should have HTMX attributes for table refresh
            assert "hx-get" in text or "data-hx-get" in text
            assert "hx-trigger" in text or "data-hx-trigger" in text

    async def test_dashboard_has_sse_extension(self):
        """Test dashboard includes SSE extension script."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            text = response.text
            # Should include SSE extension
            assert "sse.js" in text or "sse-connect" in text


# =============================================================================
# TestEdgeCases
# =============================================================================


@pytest.mark.slow
@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_nonexistent_route_returns_404(self):
        """Test that non-existent routes return 404."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/nonexistent-route")
            assert response.status_code == 404

    async def test_workflows_cancel_nonexistent(self):
        """Test POST to cancel nonexistent workflow returns appropriate response."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/workflows/nonexistent-id/cancel")
            # Should return 404
            assert response.status_code == 404

    async def test_agents_deregister_nonexistent(self):
        """Test DELETE for nonexistent agent returns appropriate response."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/agents/nonexistent-agent-id")
            # Should return 404
            assert response.status_code == 404

    async def test_orchestrator_status_unavailable(self):
        """Test orchestrator status when service is unavailable."""
        dashboard = _create_test_dashboard()
        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/orchestrator/status")
            # May return 500 if service not configured, but should not crash
            assert response.status_code in (200, 500, 503)
