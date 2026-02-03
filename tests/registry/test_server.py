"""Tests for AgentRegistryServer.

Tests the FastAPI server endpoints for agent registration, heartbeat,
listing, and health checks.

Note: Uses direct HTTP testing to avoid compatibility issues between
httpx 0.28 and starlette.testclient.TestClient.
"""

from datetime import datetime, timedelta

import pytest

from configurable_agents.config.schema import StorageConfig
from configurable_agents.registry import AgentRegistryServer
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import AgentRecord


@pytest.fixture
def test_db_url(tmp_path):
    """Create a test database URL."""
    return f"sqlite:///{tmp_path}/test_registry.db"


@pytest.fixture
def test_repo(test_db_url):
    """Create a test repository."""
    config = StorageConfig(backend="sqlite", path=test_db_url.replace("sqlite:///", ""))
    _, _, repo = create_storage_backend(config)
    return repo


@pytest.fixture
def test_server(test_repo, tmp_path):
    """Create a test server instance with app."""
    db_url = f"sqlite:///{tmp_path}/test_server.db"
    server = AgentRegistryServer(registry_url=db_url, repo=test_repo)
    app = server.create_app()
    return server, app


class TestRegisterEndpoint:
    """Test POST /agents/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_creates_new_agent(self, test_server, test_repo):
        """Test that registration creates a new agent record."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-1",
                        "agent_name": "Test Agent 1",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["agent_id"] == "test-agent-1"
                assert data["agent_name"] == "Test Agent 1"
                assert data["host"] == "localhost"
                assert data["port"] == 8000
                assert data["is_alive"] is True
                assert "last_heartbeat" in data
                assert "registered_at" in data

                # Verify in database
                agent = test_repo.get("test-agent-1")
                assert agent is not None
                assert agent.agent_name == "Test Agent 1"
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_register_idempotent_updates_existing(self, test_server, test_repo):
        """Test that re-registering updates existing record instead of duplicating."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # First registration
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-2",
                        "agent_name": "Original Name",
                        "host": "host1",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                # Second registration with different data
                response = await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-2",
                        "agent_name": "Updated Name",
                        "host": "host2",
                        "port": 9000,
                        "ttl_seconds": 120,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["agent_name"] == "Updated Name"
                assert data["host"] == "host2"
                assert data["port"] == 9000
                assert data["ttl_seconds"] == 120

                # Verify only one record exists
                agents = test_repo.list_all(include_dead=True)
                agent_2_records = [a for a in agents if a.agent_id == "test-agent-2"]
                assert len(agent_2_records) == 1
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_register_with_metadata(self, test_server, test_repo):
        """Test registration with metadata field."""
        from httpx import AsyncClient, ASGITransport

        metadata = '{"capabilities": ["chat", "code"], "version": "1.0.0"}'

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-metadata",
                        "agent_name": "Agent with Metadata",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                        "metadata": metadata,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["metadata"] == metadata

                # Verify in database
                agent = test_repo.get("test-agent-metadata")
                assert agent.agent_metadata == metadata
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_register_default_ttl(self, test_server):
        """Test that default TTL is applied when not specified."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-default-ttl",
                        "agent_name": "Default TTL Agent",
                        "host": "localhost",
                        "port": 8000,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["ttl_seconds"] == 60
        finally:
            await app.router.shutdown()


class TestHeartbeatEndpoint:
    """Test POST /agents/{agent_id}/heartbeat endpoint."""

    @pytest.mark.asyncio
    async def test_heartbeat_updates_timestamp(self, test_server, test_repo):
        """Test that heartbeat updates last_heartbeat timestamp."""
        from httpx import AsyncClient, ASGITransport
        import asyncio

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register an agent
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "test-agent-heartbeat",
                        "agent_name": "Heartbeat Agent",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                # Get initial heartbeat
                agent = test_repo.get("test-agent-heartbeat")
                initial_heartbeat = agent.last_heartbeat

                # Wait a tiny bit and send heartbeat
                await asyncio.sleep(0.01)

                response = await client.post(f"/agents/test-agent-heartbeat/heartbeat")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert "last_heartbeat" in data

                # Verify timestamp was updated
                agent = test_repo.get("test-agent-heartbeat")
                assert agent.last_heartbeat > initial_heartbeat
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_heartbeat_returns_404_for_unknown_agent(self, test_server):
        """Test that heartbeat returns 404 for unknown agent."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/agents/unknown-agent/heartbeat")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()
        finally:
            await app.router.shutdown()


class TestListAgentsEndpoint:
    """Test GET /agents endpoint."""

    @pytest.mark.asyncio
    async def test_list_agents_filters_dead_by_default(self, test_server, test_repo):
        """Test that list endpoint filters out dead agents by default."""
        from httpx import AsyncClient, ASGITransport
        from sqlalchemy.orm import Session

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register two agents
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "alive-agent",
                        "agent_name": "Alive Agent",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "dead-agent",
                        "agent_name": "Dead Agent",
                        "host": "localhost",
                        "port": 8001,
                        "ttl_seconds": 60,
                    },
                )

                # Manually expire the dead agent
                dead_agent = test_repo.get("dead-agent")
                dead_agent.last_heartbeat = datetime.utcnow() - timedelta(seconds=120)
                engine = test_repo.engine
                with Session(engine) as session:
                    session.merge(dead_agent)
                    session.commit()

                # List agents (should filter dead)
                response = await client.get("/agents")

                assert response.status_code == 200
                agents = response.json()
                assert len(agents) == 1
                assert agents[0]["agent_id"] == "alive-agent"
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_list_agents_includes_dead_when_flagged(self, test_server, test_repo):
        """Test that list endpoint includes dead agents when include_dead=true."""
        from httpx import AsyncClient, ASGITransport
        from sqlalchemy.orm import Session

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register two agents
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "alive-agent-2",
                        "agent_name": "Alive Agent 2",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "dead-agent-2",
                        "agent_name": "Dead Agent 2",
                        "host": "localhost",
                        "port": 8001,
                        "ttl_seconds": 60,
                    },
                )

                # Manually expire the dead agent
                dead_agent = test_repo.get("dead-agent-2")
                dead_agent.last_heartbeat = datetime.utcnow() - timedelta(seconds=120)
                engine = test_repo.engine
                with Session(engine) as session:
                    session.merge(dead_agent)
                    session.commit()

                # List all agents
                response = await client.get("/agents?include_dead=true")

                assert response.status_code == 200
                agents = response.json()
                assert len(agents) == 2

                agent_ids = {a["agent_id"] for a in agents}
                assert "alive-agent-2" in agent_ids
                assert "dead-agent-2" in agent_ids
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_list_empty_registry(self, test_server):
        """Test listing agents when registry is empty."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/agents")

                assert response.status_code == 200
                agents = response.json()
                assert len(agents) == 0
        finally:
            await app.router.shutdown()


class TestGetAgentEndpoint:
    """Test GET /agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_returns_agent(self, test_server):
        """Test that get endpoint returns specific agent."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register an agent
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "get-test-agent",
                        "agent_name": "Get Test Agent",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                response = await client.get("/agents/get-test-agent")

                assert response.status_code == 200
                data = response.json()
                assert data["agent_id"] == "get-test-agent"
                assert data["agent_name"] == "Get Test Agent"
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_get_agent_returns_404_for_unknown(self, test_server):
        """Test that get endpoint returns 404 for unknown agent."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/agents/unknown-agent-get")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()
        finally:
            await app.router.shutdown()


class TestDeleteAgentEndpoint:
    """Test DELETE /agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_agent_removes_from_registry(self, test_server, test_repo):
        """Test that delete endpoint removes agent."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register an agent
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "delete-test-agent",
                        "agent_name": "Delete Test Agent",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                # Verify exists
                assert test_repo.get("delete-test-agent") is not None

                # Delete
                response = await client.delete("/agents/delete-test-agent")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "deleted"
                assert data["agent_id"] == "delete-test-agent"

                # Verify deleted
                assert test_repo.get("delete-test-agent") is None
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_delete_agent_returns_404_for_unknown(self, test_server):
        """Test that delete endpoint returns 404 for unknown agent."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/agents/unknown-agent-delete")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()
        finally:
            await app.router.shutdown()


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_status(self, test_server):
        """Test that health endpoint returns registry status."""
        from httpx import AsyncClient, ASGITransport

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register some agents
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "health-agent-1",
                        "agent_name": "Health Agent 1",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "health-agent-2",
                        "agent_name": "Health Agent 2",
                        "host": "localhost",
                        "port": 8001,
                        "ttl_seconds": 60,
                    },
                )

                response = await client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["registered_agents"] == 2
                assert data["active_agents"] == 2
        finally:
            await app.router.shutdown()

    @pytest.mark.asyncio
    async def test_health_with_expired_agents(self, test_server, test_repo):
        """Test health endpoint with expired agents."""
        from httpx import AsyncClient, ASGITransport
        from sqlalchemy.orm import Session

        server, app = test_server
        await app.router.startup()

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Register two agents, then expire one
                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "health-alive",
                        "agent_name": "Health Alive",
                        "host": "localhost",
                        "port": 8000,
                        "ttl_seconds": 60,
                    },
                )

                await client.post(
                    "/agents/register",
                    json={
                        "agent_id": "health-dead",
                        "agent_name": "Health Dead",
                        "host": "localhost",
                        "port": 8001,
                        "ttl_seconds": 60,
                    },
                )

                # Manually expire one agent
                dead_agent = test_repo.get("health-dead")
                dead_agent.last_heartbeat = datetime.utcnow() - timedelta(seconds=120)
                engine = test_repo.engine
                with Session(engine) as session:
                    session.merge(dead_agent)
                    session.commit()

                response = await client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["registered_agents"] == 2  # All agents
                assert data["active_agents"] == 1  # Only alive
        finally:
            await app.router.shutdown()


class TestBackgroundCleanup:
    """Test background cleanup task."""

    def test_cleanup_endpoint_deletes_expired(self, test_repo):
        """Test that cleanup task removes expired agents."""
        # Register agents
        alive_agent = AgentRecord(
            agent_id="cleanup-alive",
            agent_name="Cleanup Alive",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=60,
        )
        test_repo.add(alive_agent)

        expired_agent = AgentRecord(
            agent_id="cleanup-expired",
            agent_name="Cleanup Expired",
            host="localhost",
            port=8001,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=120),
            ttl_seconds=60,
        )
        test_repo.add(expired_agent)

        # Manually trigger cleanup
        deleted = test_repo.delete_expired()

        assert deleted == 1
        assert test_repo.get("cleanup-alive") is not None
        assert test_repo.get("cleanup-expired") is None


class TestServerLifecycle:
    """Test server lifecycle events."""

    def test_startup_creates_cleanup_task(self, test_repo, tmp_path):
        """Test that server startup creates background cleanup task."""
        db_url = f"sqlite:///{tmp_path}/test_lifecycle.db"
        server = AgentRegistryServer(registry_url=db_url, repo=test_repo)
        app = server.create_app()

        # Manually trigger startup
        import asyncio

        async def run_test():
            await app.router.startup()
            assert server._cleanup_task is not None
            await app.router.shutdown()

        asyncio.run(run_test())

    def test_shutdown_cancels_cleanup_task(self, test_repo, tmp_path):
        """Test that server shutdown cancels background cleanup task."""
        db_url = f"sqlite:///{tmp_path}/test_lifecycle2.db"
        server = AgentRegistryServer(registry_url=db_url, repo=test_repo)
        app = server.create_app()

        import asyncio

        async def run_test():
            await app.router.startup()
            assert server._cleanup_task is not None
            await app.router.shutdown()
            # Shutdown completes without error

        asyncio.run(run_test())
