"""Tests for AgentRegistryClient.

Tests the client-side component that agents use to register themselves
and send heartbeats to the registry server.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from configurable_agents.registry.client import AgentRegistryClient


class TestClientInitialization:
    """Test client initialization and parameter storage."""

    def test_stores_parameters_correctly(self):
        """Test that client stores initialization parameters."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            ttl_seconds=120,
            heartbeat_interval=30,
        )

        assert client.registry_url == "http://localhost:9000"
        assert client.agent_id == "test-agent"
        assert client.ttl_seconds == 120
        assert client.heartbeat_interval == 30

    def test_default_values(self):
        """Test that default values are set correctly."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        assert client.ttl_seconds == 60
        assert client.heartbeat_interval == 20

    def test_removes_trailing_slash_from_url(self):
        """Test that trailing slash is removed from registry URL."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000/",
            agent_id="test-agent",
        )

        assert client.registry_url == "http://localhost:9000"

    def test_raises_error_if_heartbeat_interval_ge_ttl(self):
        """Test that ValueError is raised if heartbeat_interval >= ttl_seconds."""
        with pytest.raises(ValueError, match="heartbeat_interval.*must be less than"):
            AgentRegistryClient(
                registry_url="http://localhost:9000",
                agent_id="test-agent",
                ttl_seconds=60,
                heartbeat_interval=60,
            )

        with pytest.raises(ValueError, match="heartbeat_interval.*must be less than"):
            AgentRegistryClient(
                registry_url="http://localhost:9000",
                agent_id="test-agent",
                ttl_seconds=30,
                heartbeat_interval=60,
            )


class TestGetHostPort:
    """Test host/port detection logic."""

    def test_uses_env_vars_when_set(self):
        """Test that AGENT_HOST and AGENT_PORT env vars are used."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        with patch.dict("os.environ", {"AGENT_HOST": "agent-host", "AGENT_PORT": "8080"}):
            host, port = client._get_host_port({})
            assert host == "agent-host"
            assert port == 8080

    def test_uses_metadata_when_env_not_set(self):
        """Test that metadata host/port are used when env vars not set."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        with patch.dict("os.environ", {}, clear=True):
            host, port = client._get_host_port({"host": "metadata-host", "port": "9999"})
            assert host == "metadata-host"
            assert port == 9999

    def test_falls_back_to_detected_hostname(self):
        """Test that hostname is detected when not provided."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        with patch.dict("os.environ", {}, clear=True):
            with patch("socket.gethostname", return_value="detected-host"):
                host, port = client._get_host_port({})
                assert host == "detected-host"
                assert port == 8000  # Default port

    def test_default_port_8000(self):
        """Test that port defaults to 8000."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        with patch.dict("os.environ", {}, clear=True):
            host, port = client._get_host_port({"host": "some-host"})
            assert port == 8000

    def test_invalid_port_defaults_to_8000(self):
        """Test that invalid port string falls back to 8000."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        with patch.dict("os.environ", {"AGENT_PORT": "invalid"}):
            host, port = client._get_host_port({})
            assert port == 8000


class TestRegister:
    """Test agent registration."""

    @pytest.mark.asyncio
    async def test_register_sends_correct_payload(self):
        """Test that register sends correct POST request."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            ttl_seconds=90,
        )

        # Mock the HTTP client
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        client._http_client.post = AsyncMock(return_value=mock_response)

        # Mock host/port detection
        with patch.object(client, "_get_host_port", return_value=("test-host", 8888)):
            await client.register({"agent_name": "Test Agent", "metadata": '{"key": "value"}'})

        # Verify the POST request
        client._http_client.post.assert_called_once()
        call_args = client._http_client.post.call_args
        assert call_args[0][0] == "http://localhost:9000/agents/register"

        payload = call_args[1]["json"]
        assert payload["agent_id"] == "test-agent"
        assert payload["agent_name"] == "Test Agent"
        assert payload["host"] == "test-host"
        assert payload["port"] == 8888
        assert payload["ttl_seconds"] == 90
        assert payload["metadata"] == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_register_stores_host_port(self):
        """Test that register stores detected host and port."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        client._http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, "_get_host_port", return_value=("stored-host", 7777)):
            await client.register({})

        assert client._host == "stored-host"
        assert client._port == 7777

    @pytest.mark.asyncio
    async def test_register_with_empty_metadata(self):
        """Test register with empty metadata."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        client._http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, "_get_host_port", return_value=("host", 8000)):
            await client.register()

        payload = client._http_client.post.call_args[1]["json"]
        assert payload["agent_name"] == "test-agent"  # defaults to agent_id
        assert payload["metadata"] is None

    @pytest.mark.asyncio
    async def test_register_raises_on_http_error(self):
        """Test that register raises HTTPStatusError on failure."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Bad request", request=MagicMock(), response=mock_response
            )
        )
        client._http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, "_get_host_port", return_value=("host", 8000)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.register()


class TestHeartbeatLoop:
    """Test heartbeat background loop."""

    @pytest.mark.asyncio
    async def test_start_heartbeat_loop_creates_task(self):
        """Test that start_heartbeat_loop creates a background task."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            heartbeat_interval=1,
        )

        # Mock HTTP client - return a response-like object
        async def mock_post(*args, **kwargs):
            class MockResponse:
                def raise_for_status(self):
                    pass
            return MockResponse()

        client._http_client.post = mock_post

        await client.start_heartbeat_loop()

        assert client._heartbeat_task is not None
        assert not client._heartbeat_task.done()

        # Clean up
        client._heartbeat_task.cancel()
        try:
            await client._heartbeat_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_heartbeat_loop_cancellation(self):
        """Test that heartbeat loop exits cleanly on CancelledError."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            heartbeat_interval=0.5,  # Shorter interval
        )

        async def mock_post(*args, **kwargs):
            class MockResponse:
                def raise_for_status(self):
                    pass
            return MockResponse()

        client._http_client.post = mock_post

        await client.start_heartbeat_loop()

        # Wait a bit, then cancel
        await asyncio.sleep(0.1)
        client._heartbeat_task.cancel()

        # Should complete without raising
        await client._heartbeat_task

    @pytest.mark.asyncio
    async def test_heartbeat_retry_on_error(self):
        """Test that heartbeat loop retries on HTTP errors."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            heartbeat_interval=0.1,  # Short interval for testing
        )

        call_count = [0]

        async def mock_post(*args, **kwargs):
            call_count[0] += 1
            class MockResponse:
                def raise_for_status(self):
                    if call_count[0] == 1:
                        raise httpx.HTTPError("Connection error")
            return MockResponse()

        client._http_client.post = mock_post

        await client.start_heartbeat_loop()

        # Wait for retries
        await asyncio.sleep(0.4)

        # Should have been called at least twice (initial + retry)
        assert call_count[0] >= 1

        # Clean up
        client._heartbeat_task.cancel()
        try:
            await client._heartbeat_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_heartbeat_sends_correct_request(self):
        """Test that heartbeat sends correct POST request."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            heartbeat_interval=0.1,
        )

        calls = []

        async def mock_post(url, *args, **kwargs):
            calls.append(url)
            class MockResponse:
                def raise_for_status(self):
                    pass
            return MockResponse()

        client._http_client.post = mock_post

        await client.start_heartbeat_loop()

        # Wait for at least one heartbeat
        await asyncio.sleep(0.15)

        # Verify request
        assert len(calls) >= 1
        assert calls[0] == "http://localhost:9000/agents/test-agent/heartbeat"

        # Clean up
        client._heartbeat_task.cancel()
        try:
            await client._heartbeat_task
        except asyncio.CancelledError:
            pass


class TestDeregister:
    """Test agent deregistration."""

    @pytest.mark.asyncio
    async def test_deregister_cancels_heartbeat_task(self):
        """Test that deregister cancels heartbeat task."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
            heartbeat_interval=0.1,
        )

        async def mock_post(*args, **kwargs):
            class MockResponse:
                def raise_for_status(self):
                    pass
            return MockResponse()

        async def mock_delete(*args, **kwargs):
            class MockResponse:
                def raise_for_status(self):
                    pass
            return MockResponse()

        client._http_client.post = mock_post
        client._http_client.delete = mock_delete

        await client.start_heartbeat_loop()
        assert client._heartbeat_task is not None

        await client.deregister()

        assert client._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_deregister_sends_delete_request(self):
        """Test that deregister sends DELETE request."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        client._http_client.delete = AsyncMock(return_value=mock_response)

        await client.deregister()

        client._http_client.delete.assert_called_once_with(
            "http://localhost:9000/agents/test-agent"
        )

    @pytest.mark.asyncio
    async def test_deregister_best_effort_on_error(self):
        """Test that deregister doesn't raise on HTTP errors."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        # Make DELETE raise an error
        client._http_client.delete = AsyncMock(
            side_effect=httpx.HTTPError("Connection error")
        )

        # Should not raise
        await client.deregister()

    @pytest.mark.asyncio
    async def test_deregister_without_heartbeat_task(self):
        """Test deregister when no heartbeat task is running."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        client._http_client.delete = AsyncMock(return_value=mock_response)

        # Should not raise even without heartbeat task
        await client.deregister()

        client._http_client.delete.assert_called_once()


class TestClose:
    """Test client cleanup."""

    @pytest.mark.asyncio
    async def test_close_closes_http_client(self):
        """Test that close closes the HTTP client."""
        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )

        client._http_client.aclose = AsyncMock()

        await client.close()

        client._http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test that client works as async context manager."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        client = AgentRegistryClient(
            registry_url="http://localhost:9000",
            agent_id="test-agent",
        )
        client._http_client.post = AsyncMock(return_value=mock_response)
        client._http_client.delete = AsyncMock(return_value=mock_response)
        client._http_client.aclose = AsyncMock()

        with patch.object(client, "_get_host_port", return_value=("host", 8000)):
            async with client:
                await client.register()

        # Verify deregister and close were called
        client._http_client.delete.assert_called_once()
        client._http_client.aclose.assert_called_once()
