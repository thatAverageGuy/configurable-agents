"""Agent registry client for self-registration and heartbeat.

Provides the client-side component that agents use to register themselves
and send heartbeats to the registry server.

Example:
    >>> from configurable_agents.registry import AgentRegistryClient
    >>> client = AgentRegistryClient(
    ...     registry_url="http://localhost:9000",
    ...     agent_id="my-agent"
    ... )
    >>> await client.register({"host": "localhost", "port": 8000})
    >>> await client.start_heartbeat_loop()
    >>> # ... agent runs ...
    >>> await client.deregister()
"""

import asyncio
import socket
from typing import Optional

import httpx


class AgentRegistryClient:
    """Client for agent self-registration and heartbeat.

    Agents use this client to register themselves with the registry server
    and maintain their registration via periodic heartbeats.

    The heartbeat loop runs in the background, retrying on HTTP errors
    instead of crashing. This ensures agents stay registered even during
    transient network issues.

    Attributes:
        registry_url: URL of the registry server (e.g., "http://localhost:9000")
        agent_id: Unique identifier for this agent
        ttl_seconds: Time-to-live for registration (default: 60)
        heartbeat_interval: Seconds between heartbeat sends (default: 20)
        _http_client: Async HTTP client for registry requests
        _heartbeat_task: Background task for heartbeat loop
    """

    def __init__(
        self,
        registry_url: str,
        agent_id: str,
        ttl_seconds: int = 60,
        heartbeat_interval: int = 20,
    ):
        """Initialize the agent registry client.

        Args:
            registry_url: URL of the registry server
                (e.g., "http://localhost:9000")
            agent_id: Unique identifier for this agent
            ttl_seconds: Time-to-live in seconds (default: 60)
            heartbeat_interval: Seconds between heartbeats (default: 20)
                Should be ~1/3 of TTL to ensure reliable refresh

        Raises:
            ValueError: If heartbeat_interval >= ttl_seconds
        """
        if heartbeat_interval >= ttl_seconds:
            raise ValueError(
                f"heartbeat_interval ({heartbeat_interval}) must be less than "
                f"ttl_seconds ({ttl_seconds})"
            )

        self.registry_url = registry_url.rstrip("/")
        self.agent_id = agent_id
        self.ttl_seconds = ttl_seconds
        self.heartbeat_interval = heartbeat_interval

        # Async HTTP client for registry requests
        self._http_client = httpx.AsyncClient(timeout=10.0)

        # Background task reference
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Host/port (detected on registration)
        self._host: Optional[str] = None
        self._port: Optional[int] = None

    def _get_host_port(self, metadata: dict) -> tuple[str, int]:
        """Get host and port from environment, metadata, or defaults.

        Checks environment variables AGENT_HOST and AGENT_PORT first,
        then looks in provided metadata, falls back to defaults.

        Args:
            metadata: Optional metadata dict that may contain host/port

        Returns:
            Tuple of (host, port)
        """
        import os

        # Try environment variables first
        host = os.getenv("AGENT_HOST")
        port_str = os.getenv("AGENT_PORT")

        # Try metadata next
        if not host:
            host = metadata.get("host")
        if not port_str:
            port_str = metadata.get("port")

        # Detect hostname if not provided
        if not host:
            host = socket.gethostname()

        # Default port if not provided
        if port_str:
            try:
                port = int(port_str)
            except (ValueError, TypeError):
                port = 8000
        else:
            port = 8000

        return host, port

    async def register(
        self,
        metadata: Optional[dict] = None,
    ) -> None:
        """Register this agent with the registry server.

        Sends a POST request to /agents/register with agent information.
        Registration is idempotent - re-registering updates the existing record.

        Args:
            metadata: Optional dict with additional agent information.
                May include 'host' and 'port' (auto-detected if not provided)

        Raises:
            httpx.HTTPStatusError: If registration fails
        """
        metadata = metadata or {}

        # Detect or retrieve host/port
        host, port = self._get_host_port(metadata)
        self._host = host
        self._port = port

        # Build registration payload
        payload = {
            "agent_id": self.agent_id,
            "agent_name": metadata.get("agent_name", self.agent_id),
            "host": host,
            "port": port,
            "ttl_seconds": self.ttl_seconds,
            "metadata": metadata.get("metadata"),
        }

        # Send registration request
        response = await self._http_client.post(
            f"{self.registry_url}/agents/register",
            json=payload,
        )
        response.raise_for_status()

    async def start_heartbeat_loop(self) -> None:
        """Start the background heartbeat loop.

        Creates an asyncio background task that sends heartbeats
        every heartbeat_interval seconds.

        The loop handles HTTP errors gracefully - on failure it sleeps
        for 5 seconds and retries instead of crashing.

        Note: This runs in a background task and does not block.
        """
        if self._heartbeat_task is not None:
            # Already started
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def _heartbeat(self) -> None:
        """Background heartbeat loop.

        Sends heartbeat POST requests to /agents/{agent_id}/heartbeat
        every heartbeat_interval seconds.

        Handles:
        - asyncio.CancelledError for clean shutdown
        - HTTP errors: sleeps 5 seconds and retries

        This loop is designed to be resilient - transient network issues
        don't crash the agent.
        """
        retry_delay = 5  # seconds

        try:
            while True:
                try:
                    response = await self._http_client.post(
                        f"{self.registry_url}/agents/{self.agent_id}/heartbeat"
                    )
                    response.raise_for_status()

                    # Sleep until next heartbeat
                    await asyncio.sleep(self.heartbeat_interval)

                except (httpx.HTTPError, asyncio.CancelledError):
                    # On CancelledError, re-raise to exit cleanly
                    # On HTTP errors, sleep and retry
                    try:
                        await asyncio.sleep(retry_delay)
                    except asyncio.CancelledError:
                        # Exit cleanly during retry sleep
                        raise

        except asyncio.CancelledError:
            # Normal shutdown - exit the loop
            pass

    async def deregister(self) -> None:
        """Deregister this agent from the registry.

        Cancels the heartbeat task (if running) and sends a DELETE
        request to /agents/{agent_id}.

        Call this during agent shutdown to clean up the registry entry.
        """
        # Cancel heartbeat task if running
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Send deregistration request
        try:
            response = await self._http_client.delete(
                f"{self.registry_url}/agents/{self.agent_id}"
            )
            response.raise_for_status()
        except httpx.HTTPError:
            # Log but don't raise - deregistration is best-effort
            pass

    async def close(self) -> None:
        """Close the HTTP client.

        Call this when shutting down the agent to clean up resources.
        """
        await self._http_client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - deregisters and closes client."""
        await self.deregister()
        await self.close()
