"""Tests for AgentRegistryRepository enhancements.

Tests the new metadata querying and active agent filtering methods
added to the agent registry repository.
"""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from configurable_agents.storage.models import AgentRecord, Base
from configurable_agents.storage.sqlite import SqliteAgentRegistryRepository


@pytest.fixture
def agent_repo(tmp_path):
    """Create a fresh AgentRegistryRepository for each test."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    repo = SqliteAgentRegistryRepository(engine)
    return repo


class TestQueryByMetadata:
    """Tests for query_by_metadata method."""

    def test_query_by_type(self, agent_repo) -> None:
        """Test querying agents by type metadata."""
        # Create test agents with different types
        agent_repo.add(
            AgentRecord(
                agent_id="llm-agent-1",
                agent_name="LLM Agent 1",
                host="localhost",
                port=8001,
                agent_metadata=json.dumps({"type": "llm", "model": "gpt-4"}),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="tool-agent-1",
                agent_name="Tool Agent 1",
                host="localhost",
                port=8002,
                agent_metadata=json.dumps({"type": "tool", "name": "browser"}),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="llm-agent-2",
                agent_name="LLM Agent 2",
                host="localhost",
                port=8003,
                agent_metadata=json.dumps({"type": "llm", "model": "claude"}),
            )
        )

        # Query for LLM agents
        llm_agents = agent_repo.query_by_metadata({"type": "llm"})

        assert len(llm_agents) == 2
        assert all(a.agent_id.startswith("llm") for a in llm_agents)

    def test_query_by_wildcard(self, agent_repo) -> None:
        """Test querying agents with wildcard patterns."""
        agent_repo.add(
            AgentRecord(
                agent_id="gpt4-agent",
                agent_name="GPT-4 Agent",
                host="localhost",
                port=8001,
                agent_metadata=json.dumps({"model": "gpt-4"}),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="gpt35-agent",
                agent_name="GPT-3.5 Agent",
                host="localhost",
                port=8002,
                agent_metadata=json.dumps({"model": "gpt-3.5-turbo"}),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="claude-agent",
                agent_name="Claude Agent",
                host="localhost",
                port=8003,
                agent_metadata=json.dumps({"model": "claude-3"}),
            )
        )

        # Query for GPT models with wildcard
        gpt_agents = agent_repo.query_by_metadata({"model": "gpt-*"})

        assert len(gpt_agents) == 2
        agent_ids = {a.agent_id for a in gpt_agents}
        assert agent_ids == {"gpt4-agent", "gpt35-agent"}

    def test_query_by_nested_keys(self, agent_repo) -> None:
        """Test querying agents with nested metadata keys."""
        agent_repo.add(
            AgentRecord(
                agent_id="multi-agent",
                agent_name="Multi-capability Agent",
                host="localhost",
                port=8001,
                agent_metadata=json.dumps({
                    "capabilities": {"llm": True, "vision": True, "tool": False}
                }),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="llm-only-agent",
                agent_name="LLM Only Agent",
                host="localhost",
                port=8002,
                agent_metadata=json.dumps({
                    "capabilities": {"llm": True, "vision": False}
                }),
            )
        )

        # Query for agents with vision capability
        vision_agents = agent_repo.query_by_metadata({"capabilities.vision": True})

        assert len(vision_agents) == 1
        assert vision_agents[0].agent_id == "multi-agent"

    def test_query_by_multiple_filters(self, agent_repo) -> None:
        """Test querying agents with multiple filter criteria."""
        agent_repo.add(
            AgentRecord(
                agent_id="gpt4-vision",
                agent_name="GPT-4 Vision",
                host="localhost",
                port=8001,
                agent_metadata=json.dumps({
                    "type": "llm",
                    "model": "gpt-4",
                    "capabilities": {"vision": True}
                }),
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="gpt4-text",
                agent_name="GPT-4 Text",
                host="localhost",
                port=8002,
                agent_metadata=json.dumps({
                    "type": "llm",
                    "model": "gpt-4",
                    "capabilities": {"vision": False}
                }),
            )
        )

        # Query for LLM + GPT-4 + vision
        results = agent_repo.query_by_metadata({
            "type": "llm",
            "model": "gpt-4",
            "capabilities.vision": True
        })

        assert len(results) == 1
        assert results[0].agent_id == "gpt4-vision"

    def test_query_with_no_metadata(self, agent_repo) -> None:
        """Test querying when agent has no metadata."""
        agent_repo.add(
            AgentRecord(
                agent_id="no-metadata",
                agent_name="No Metadata Agent",
                host="localhost",
                port=8001,
                agent_metadata=None,
            )
        )

        results = agent_repo.query_by_metadata({"type": "llm"})

        assert len(results) == 0

    def test_query_with_invalid_metadata(self, agent_repo) -> None:
        """Test querying with invalid JSON metadata."""
        agent_repo.add(
            AgentRecord(
                agent_id="bad-metadata",
                agent_name="Bad Metadata Agent",
                host="localhost",
                port=8001,
                agent_metadata="not-valid-json",
            )
        )

        results = agent_repo.query_by_metadata({"type": "llm"})

        assert len(results) == 0


class TestGetActiveAgents:
    """Tests for get_active_agents method."""

    def test_get_recent_heartbeats(self, agent_repo) -> None:
        """Test getting agents with recent heartbeats."""
        now = datetime.utcnow()

        # Create agents with different heartbeat times
        agent_repo.add(
            AgentRecord(
                agent_id="active-1",
                agent_name="Active Agent 1",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=30),
                agent_metadata='{}',
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="active-2",
                agent_name="Active Agent 2",
                host="localhost",
                port=8002,
                last_heartbeat=now - timedelta(seconds=45),
                agent_metadata='{}',
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="inactive",
                agent_name="Inactive Agent",
                host="localhost",
                port=8003,
                last_heartbeat=now - timedelta(seconds=120),
                agent_metadata='{}',
            )
        )

        # Get agents active in last 60 seconds
        active = agent_repo.get_active_agents(cutoff_seconds=60)

        assert len(active) == 2
        assert all(a.agent_id.startswith("active") for a in active)

    def test_get_active_with_custom_cutoff(self, agent_repo) -> None:
        """Test getting active agents with custom cutoff."""
        now = datetime.utcnow()

        agent_repo.add(
            AgentRecord(
                agent_id="very-recent",
                agent_name="Very Recent",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=20),
                agent_metadata='{}',
            )
        )
        agent_repo.add(
            AgentRecord(
                agent_id="somewhat-recent",
                agent_name="Somewhat Recent",
                host="localhost",
                port=8002,
                last_heartbeat=now - timedelta(seconds=90),
                agent_metadata='{}',
            )
        )

        # Get agents active in last 30 seconds
        active = agent_repo.get_active_agents(cutoff_seconds=30)

        assert len(active) == 1
        assert active[0].agent_id == "very-recent"

    def test_get_active_includes_dead_agents(self, agent_repo) -> None:
        """Test that get_active_agents can return dead agents if heartbeat is recent."""
        now = datetime.utcnow()

        # Create agent with very recent heartbeat but TTL expired
        agent_repo.add(
            AgentRecord(
                agent_id="dead-but-recent",
                agent_name="Dead But Recent",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=10),
                ttl_seconds=5,  # TTL of 5 seconds (expired)
                agent_metadata='{}',
            )
        )

        active = agent_repo.get_active_agents(cutoff_seconds=60)

        # Should be included because heartbeat is recent, even though TTL expired
        assert len(active) == 1
        assert active[0].agent_id == "dead-but-recent"

    def test_get_active_with_old_heartbeat(self, agent_repo) -> None:
        """Test that agents with old heartbeats are excluded."""
        now = datetime.utcnow()

        # Create agent with very old heartbeat (older than 60 seconds)
        agent_repo.add(
            AgentRecord(
                agent_id="old-heartbeat",
                agent_name="Old Heartbeat",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=120),
                agent_metadata='{}',
            )
        )

        active = agent_repo.get_active_agents(cutoff_seconds=60)

        # Should be excluded because heartbeat is too old
        assert len(active) == 0
