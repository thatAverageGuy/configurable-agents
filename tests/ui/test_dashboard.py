"""Tests for the dashboard application.

Tests dashboard app creation, route registration, and endpoint responses.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock

from configurable_agents.ui.dashboard import create_dashboard_app, DashboardApp
from configurable_agents.storage.models import Execution, Deployment
from configurable_agents.ui.dashboard.routes.workflows import (
    _format_duration,
    _format_cost,
    _format_datetime,
    _format_datetime_relative,
    _get_status_badge_class,
)
from configurable_agents.ui.dashboard.routes.agents import (
    _time_ago,
    _format_datetime as _format_datetime_agents,
    _parse_capabilities,
)


class TestDashboardAppCreation:
    """Tests for dashboard app creation and initialization."""

    def test_dashboard_app_creation(self):
        """Verify dashboard app initializes with repositories."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Verify app was created
        assert dashboard.app is not None
        assert dashboard.execution_repo == execution_repo
        assert dashboard.deployment_repo == agent_repo

    def test_dashboard_routes_registered(self):
        """Verify all dashboard routes are registered."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Get routes
        routes = [route.path for route in dashboard.app.routes]

        # Verify main routes exist
        assert "/" in routes
        assert "/health" in routes
        assert "/static" in routes

        # Verify workflow routes
        assert any("/workflows" in r for r in routes)

        # Verify agent routes
        assert any("/agents" in r for r in routes)

        # Verify metrics routes
        assert any("/metrics" in r for r in routes)

    def test_dashboard_factory_function(self):
        """Verify create_dashboard_app factory function works."""
        # Create dashboard app using factory
        dashboard = create_dashboard_app(db_url="sqlite:///:memory:")

        # Verify app was created
        assert dashboard.app is not None
        assert isinstance(dashboard, DashboardApp)


class TestWorkflowHelpers:
    """Tests for workflow route helper functions."""

    def test_format_duration_none(self):
        """Test formatting None duration."""
        assert _format_duration(None) == "-"

    def test_format_duration_negative(self):
        """Test formatting negative duration."""
        assert _format_duration(-1.0) == "-"

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        assert _format_duration(0.5) == "< 1s"
        assert _format_duration(5) == "5s"
        assert _format_duration(59) == "59s"

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(125) == "2m 5s"
        assert _format_duration(3600) == "60m 0s"

    def test_format_cost_none(self):
        """Test formatting None cost."""
        assert _format_cost(None) == "$0.00"

    def test_format_cost_values(self):
        """Test formatting cost values."""
        assert _format_cost(0.0) == "$0.0000"
        assert _format_cost(0.123456) == "$0.1235"
        assert _format_cost(1.5) == "$1.5000"
        assert _format_cost(10.99999) == "$11.0000"

    def test_format_datetime_none(self):
        """Test formatting None datetime."""
        assert _format_datetime(None) == "-"

    def test_format_datetime_value(self):
        """Test formatting datetime value."""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = _format_datetime(dt)
        assert "2024-01-15" in result
        assert "14:30:00" in result

    def test_format_datetime_relative_none(self):
        """Test formatting None as relative datetime."""
        assert _format_datetime_relative(None) == "-"

    def test_format_datetime_relative_just_now(self):
        """Test formatting recent datetime as relative."""
        dt = datetime.utcnow() - timedelta(seconds=30)
        assert _format_datetime_relative(dt) == "just now"

    def test_format_datetime_relative_minutes(self):
        """Test formatting datetime minutes ago."""
        dt = datetime.utcnow() - timedelta(minutes=5)
        assert "5 minute" in _format_datetime_relative(dt)

        dt = datetime.utcnow() - timedelta(minutes=1)
        assert "1 minute ago" in _format_datetime_relative(dt)

    def test_format_datetime_relative_hours(self):
        """Test formatting datetime hours ago."""
        dt = datetime.utcnow() - timedelta(hours=2)
        assert "2 hour" in _format_datetime_relative(dt)

        dt = datetime.utcnow() - timedelta(hours=1)
        assert "1 hour ago" in _format_datetime_relative(dt)

    def test_format_datetime_relative_days(self):
        """Test formatting datetime days ago."""
        dt = datetime.utcnow() - timedelta(days=3)
        assert "3 day" in _format_datetime_relative(dt)

    def test_get_status_badge_class(self):
        """Test getting CSS class for status badge."""
        assert _get_status_badge_class("running") == "badge-running"
        assert _get_status_badge_class("completed") == "badge-completed"
        assert _get_status_badge_class("failed") == "badge-failed"
        assert _get_status_badge_class("pending") == "badge-pending"
        assert _get_status_badge_class("cancelled") == "badge-cancelled"
        assert _get_status_badge_class("unknown") == "badge-pending"
        assert _get_status_badge_class(None) == "badge-pending"
        assert _get_status_badge_class("") == "badge-pending"


class TestAgentHelpers:
    """Tests for agent route helper functions."""

    def test_time_ago_none(self):
        """Test formatting None as time ago."""
        assert _time_ago(None) == "-"

    def test_time_ago_just_now(self):
        """Test formatting recent datetime as time ago."""
        dt = datetime.utcnow() - timedelta(seconds=30)
        assert _time_ago(dt) == "just now"

    def test_time_ago_minutes(self):
        """Test formatting datetime minutes ago."""
        dt = datetime.utcnow() - timedelta(minutes=5)
        assert _time_ago(dt) == "5m ago"

        dt = datetime.utcnow() - timedelta(minutes=1)
        assert _time_ago(dt) == "1m ago"

    def test_time_ago_hours(self):
        """Test formatting datetime hours ago."""
        dt = datetime.utcnow() - timedelta(hours=2)
        assert _time_ago(dt) == "2h ago"

        dt = datetime.utcnow() - timedelta(hours=1)
        assert _time_ago(dt) == "1h ago"

    def test_time_ago_days(self):
        """Test formatting datetime days ago."""
        dt = datetime.utcnow() - timedelta(days=3)
        assert _time_ago(dt) == "3d ago"

    def test_format_datetime_agents_none(self):
        """Test formatting None datetime in agents module."""
        assert _format_datetime_agents(None) == "-"

    def test_parse_capabilities_none(self):
        """Test parsing None capabilities."""
        assert _parse_capabilities(None) == []

    def test_parse_capabilities_empty_string(self):
        """Test parsing empty string capabilities."""
        assert _parse_capabilities("") == []

    def test_parse_capabilities_invalid_json(self):
        """Test parsing invalid JSON capabilities."""
        assert _parse_capabilities("not json") == []

    def test_parse_capabilities_dict(self):
        """Test parsing capabilities from dict."""
        metadata = '{"capabilities": ["chat", "search"]}'
        result = _parse_capabilities(metadata)
        assert result == ["chat", "search"]

    def test_parse_capabilities_list(self):
        """Test parsing capabilities from list."""
        metadata = '["chat", "search", "summarize"]'
        result = _parse_capabilities(metadata)
        assert result == ["chat", "search", "summarize"]

    def test_parse_capabilities_nodes(self):
        """Test parsing capabilities from nodes field."""
        metadata = '{"nodes": ["agent_1", "agent_2"]}'
        result = _parse_capabilities(metadata)
        assert result == ["agent_1", "agent_2"]


@pytest.mark.asyncio
class TestDashboardEndpoints:
    """Tests for dashboard HTTP endpoints."""

    async def test_dashboard_home_page(self, httpx_mock_client):
        """Test GET / returns HTML dashboard."""
        # Create mock repositories
        execution_repo = Mock()
        execution_repo.engine = Mock()
        agent_repo = Mock()
        agent_repo.list_all = Mock(return_value=[])

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Mock the session query
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///:memory:")

        # Create a test client using httpx ASGI transport
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        # Verify response
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    async def test_health_endpoint(self):
        """Test GET /health returns health status."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
class TestWorkflowEndpoints:
    """Tests for workflow monitoring endpoints."""

    async def test_workflows_list_empty(self):
        """Test GET /workflows with no workflows."""
        # Create mock repositories
        execution_repo = Mock()
        execution_repo.list_all = Mock(return_value=[])
        agent_repo = Mock()

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/workflows/")

        # Verify response
        assert response.status_code == 200

    async def test_workflows_stream_sse(self):
        """Test GET /metrics/workflows/stream returns SSE."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/workflows/stream")

        # Verify response is SSE
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestAgentEndpoints:
    """Tests for agent discovery endpoints."""

    async def test_agents_list_empty(self):
        """Test GET /agents with no agents."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()
        agent_repo.list_all = Mock(return_value=[])

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents/")

        # Verify response
        assert response.status_code == 200

    async def test_agents_stream_sse(self):
        """Test GET /metrics/agents/stream returns SSE."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()
        agent_repo.list_all = Mock(return_value=[])

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/agents/stream")

        # Verify response is SSE
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestMetricsEndpoints:
    """Tests for metrics endpoints."""

    async def test_metrics_summary(self):
        """Test GET /metrics/summary returns metrics summary."""
        # Create mock repositories
        execution_repo = Mock()
        agent_repo = Mock()
        agent_repo.list_all = Mock(return_value=[])

        # Create dashboard app
        dashboard = DashboardApp(
            execution_repo=execution_repo,
            deployment_repo=agent_repo,
        )

        # Create a test client
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=dashboard.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics/summary")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "total_workflows" in data
        assert "running_workflows" in data
        assert "registered_agents" in data
        assert "total_cost_usd" in data
        assert "timestamp" in data
