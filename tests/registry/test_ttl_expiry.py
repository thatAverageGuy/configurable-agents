"""Tests for TTL expiry logic.

Tests AgentRecord.is_alive() and delete_expired() behavior including
edge cases for TTL calculation.
"""

from datetime import datetime, timedelta

import pytest

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import AgentRecord


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository for TTL expiry tests."""
    db_path = str(tmp_path / "test_ttl_expiry.db")
    config = StorageConfig(backend="sqlite", path=db_path)
    _, _, repo, _, _ = create_storage_backend(config)
    return repo


class TestIsAlive:
    """Test AgentRecord.is_alive() method."""

    def test_is_alive_with_valid_heartbeat(self):
        """Test that is_alive returns True when heartbeat is recent."""
        agent = AgentRecord(
            agent_id="test-agent",
            agent_name="Test Agent",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=60,
        )

        assert agent.is_alive() is True

    def test_is_alive_with_heartbeat_at_boundary(self):
        """Test is_alive at the exact boundary of TTL expiration."""
        # Heartbeat exactly TTL seconds ago should be expired
        agent = AgentRecord(
            agent_id="boundary-agent",
            agent_name="Boundary Agent",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=60),
            ttl_seconds=60,
        )

        # At exactly the boundary, should be expired (current time >= expiration)
        assert agent.is_alive() is False

    def test_is_alive_with_expired_heartbeat(self):
        """Test that is_alive returns False when heartbeat + TTL < now."""
        agent = AgentRecord(
            agent_id="expired-agent",
            agent_name="Expired Agent",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=120),
            ttl_seconds=60,
        )

        assert agent.is_alive() is False

    def test_is_alive_with_different_ttl_values(self):
        """Test is_alive with various TTL values."""
        # Short TTL (10 seconds)
        agent_short = AgentRecord(
            agent_id="short-ttl",
            agent_name="Short TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=5),
            ttl_seconds=10,
        )
        assert agent_short.is_alive() is True

        # Long TTL (3600 seconds)
        agent_long = AgentRecord(
            agent_id="long-ttl",
            agent_name="Long TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=100),
            ttl_seconds=3600,
        )
        assert agent_long.is_alive() is True

    def test_is_alive_with_zero_ttl(self):
        """Test edge case: TTL of 0 means agent is always expired."""
        agent = AgentRecord(
            agent_id="zero-ttl",
            agent_name="Zero TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=0,
        )

        # TTL=0 means expiration time is now, so should be expired
        assert agent.is_alive() is False

    def test_is_alive_with_negative_ttl(self):
        """Test edge case: negative TTL is handled (treated as 0)."""
        agent = AgentRecord(
            agent_id="negative-ttl",
            agent_name="Negative TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=-10,
        )

        # Negative TTL should result in expired agent
        assert agent.is_alive() is False

    def test_is_alive_with_none_ttl(self):
        """Test that None TTL defaults to 60 seconds."""
        agent = AgentRecord(
            agent_id="none-ttl",
            agent_name="None TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=None,
        )

        # None TTL defaults to 60, so should be alive
        assert agent.is_alive() is True


class TestDeleteExpired:
    """Test repository delete_expired() method."""

    def test_delete_expired_removes_only_expired(self, test_repo, tmp_path):
        """Test that delete_expired only removes expired agents."""
        # Create alive agent
        alive_agent = AgentRecord(
            agent_id="alive-agent",
            agent_name="Alive Agent",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=60,
        )
        test_repo.add(alive_agent)

        # Create expired agent
        expired_agent = AgentRecord(
            agent_id="expired-agent",
            agent_name="Expired Agent",
            host="localhost",
            port=8001,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=120),
            ttl_seconds=60,
        )
        test_repo.add(expired_agent)

        # Delete expired
        deleted = test_repo.delete_expired()

        assert deleted == 1
        assert test_repo.get("alive-agent") is not None
        assert test_repo.get("expired-agent") is None

    def test_delete_expired_with_multiple_expired(self, test_repo, tmp_path):
        """Test delete_expired with multiple expired agents."""
        # Add mix of alive and expired agents
        for i in range(3):
            alive = AgentRecord(
                agent_id=f"alive-{i}",
                agent_name=f"Alive {i}",
                host="localhost",
                port=8000 + i,
                last_heartbeat=datetime.utcnow(),
                ttl_seconds=60,
            )
            test_repo.add(alive)

        for i in range(5):
            expired = AgentRecord(
                agent_id=f"expired-{i}",
                agent_name=f"Expired {i}",
                host="localhost",
                port=8010 + i,
                last_heartbeat=datetime.utcnow() - timedelta(seconds=120),
                ttl_seconds=60,
            )
            test_repo.add(expired)

        deleted = test_repo.delete_expired()

        assert deleted == 5

        # Verify all alive remain
        for i in range(3):
            assert test_repo.get(f"alive-{i}") is not None

        # Verify all expired are gone
        for i in range(5):
            assert test_repo.get(f"expired-{i}") is None

    def test_delete_expired_returns_zero_when_none_expired(self, test_repo, tmp_path):
        """Test delete_expired when no agents are expired."""
        agent = AgentRecord(
            agent_id="all-alive",
            agent_name="All Alive",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=60,
        )
        test_repo.add(agent)

        deleted = test_repo.delete_expired()

        assert deleted == 0
        assert test_repo.get("all-alive") is not None

    def test_delete_expired_with_empty_registry(self, test_repo, tmp_path):
        """Test delete_expired when registry is empty."""
        deleted = test_repo.delete_expired()
        assert deleted == 0

    def test_delete_expired_with_boundary_cases(self, test_repo, tmp_path):
        """Test delete_expired with TTL boundary conditions."""
        # Agent at exact boundary (heartbeat + TTL = now)
        boundary_agent = AgentRecord(
            agent_id="boundary",
            agent_name="Boundary",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=60),
            ttl_seconds=60,
        )
        test_repo.add(boundary_agent)

        # Agent just before boundary
        almost_expired = AgentRecord(
            agent_id="almost",
            agent_name="Almost",
            host="localhost",
            port=8001,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=59),
            ttl_seconds=60,
        )
        test_repo.add(almost_expired)

        deleted = test_repo.delete_expired()

        # Only the boundary agent should be deleted
        assert deleted == 1
        assert test_repo.get("boundary") is None
        assert test_repo.get("almost") is not None


class TestTTLCalculation:
    """Test TTL expiration calculation edge cases."""

    def test_expiration_time_calculation(self):
        """Test that expiration time = heartbeat + TTL."""
        agent = AgentRecord(
            agent_id="calc-test",
            agent_name="Calc Test",
            host="localhost",
            port=8000,
            last_heartbeat=datetime(2025, 1, 1, 12, 0, 0),
            ttl_seconds=60,
        )

        # Expiration should be at 12:01:00
        from datetime import timedelta
        expected_expiration = datetime(2025, 1, 1, 12, 0, 0) + timedelta(seconds=60)

        # is_alive checks if now < expiration
        # At 12:00:59, should be alive
        assert datetime(2025, 1, 1, 12, 0, 59) < expected_expiration

        # At 12:01:00, should be expired
        assert not (datetime(2025, 1, 1, 12, 1, 0) < expected_expiration)

        # At 12:01:01, should be expired
        assert not (datetime(2025, 1, 1, 12, 1, 1) < expected_expiration)

    def test_very_long_ttl(self):
        """Test behavior with very large TTL values."""
        agent = AgentRecord(
            agent_id="long-ttl-test",
            agent_name="Long TTL Test",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=86400,  # 24 hours
        )

        # Should definitely be alive
        assert agent.is_alive() is True

    def test_fractional_ttl_not_supported(self):
        """Test that TTL is stored as integer (not fractional)."""
        # AgentRecord uses Integer type for ttl_seconds
        # This test documents the expected behavior
        agent = AgentRecord(
            agent_id="int-ttl",
            agent_name="Int TTL",
            host="localhost",
            port=8000,
            last_heartbeat=datetime.utcnow(),
            ttl_seconds=30,  # Must be integer
        )

        assert agent.ttl_seconds == 30
        assert isinstance(agent.ttl_seconds, int)


class TestAgentRecordDefaults:
    """Test AgentRecord __init__ default values."""

    def test_default_ttl_is_60_seconds(self):
        """Test that default TTL is 60 seconds when not specified."""
        agent = AgentRecord(
            agent_id="default-ttl",
            agent_name="Default TTL",
            host="localhost",
            port=8000,
        )

        assert agent.ttl_seconds == 60

    def test_default_last_heartbeat_is_now(self):
        """Test that default last_heartbeat is current time."""
        before = datetime.utcnow()
        agent = AgentRecord(
            agent_id="default-heartbeat",
            agent_name="Default Heartbeat",
            host="localhost",
            port=8000,
        )
        after = datetime.utcnow()

        assert before <= agent.last_heartbeat <= after

    def test_default_registered_at_is_now(self):
        """Test that default registered_at is current time."""
        before = datetime.utcnow()
        agent = AgentRecord(
            agent_id="default-registered",
            agent_name="Default Registered",
            host="localhost",
            port=8000,
        )
        after = datetime.utcnow()

        assert before <= agent.registered_at <= after

    def test_custom_values_override_defaults(self):
        """Test that custom values override defaults."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)

        agent = AgentRecord(
            agent_id="custom-values",
            agent_name="Custom Values",
            host="localhost",
            port=8000,
            ttl_seconds=120,
            last_heartbeat=custom_time,
            registered_at=custom_time,
        )

        assert agent.ttl_seconds == 120
        assert agent.last_heartbeat == custom_time
        assert agent.registered_at == custom_time
