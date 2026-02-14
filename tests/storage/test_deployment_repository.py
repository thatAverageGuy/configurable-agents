"""Tests for DeploymentRepository enhancements.

Tests the new metadata querying and active deployment filtering methods
added to the deployment repository.

Renamed in UI Redesign (2026-02-13):
- AgentRecord → Deployment
- SqliteAgentRegistryRepository → SqliteDeploymentRepository
- agent_id → deployment_id, agent_name → deployment_name
"""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from configurable_agents.storage.models import Deployment, Base
from configurable_agents.storage.sqlite import SqliteDeploymentRepository


@pytest.fixture
def deployment_repo(tmp_path):
    """Create a fresh DeploymentRepository for each test."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    repo = SqliteDeploymentRepository(engine)
    return repo


class TestQueryByMetadata:
    """Tests for query_by_metadata method."""

    def test_query_by_type(self, deployment_repo) -> None:
        """Test querying deployments by type metadata."""
        # Create test deployments with different types
        deployment_repo.add(
            Deployment(
                deployment_id="llm-deployment-1",
                deployment_name="LLM Deployment 1",
                host="localhost",
                port=8001,
                deployment_metadata=json.dumps({"type": "llm", "model": "gpt-4"}),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="tool-deployment-1",
                deployment_name="Tool Deployment 1",
                host="localhost",
                port=8002,
                deployment_metadata=json.dumps({"type": "tool", "name": "browser"}),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="llm-deployment-2",
                deployment_name="LLM Deployment 2",
                host="localhost",
                port=8003,
                deployment_metadata=json.dumps({"type": "llm", "model": "claude"}),
            )
        )

        # Query for LLM deployments
        llm_deployments = deployment_repo.query_by_metadata({"type": "llm"})

        assert len(llm_deployments) == 2
        assert all(d.deployment_id.startswith("llm") for d in llm_deployments)

    def test_query_by_wildcard(self, deployment_repo) -> None:
        """Test querying deployments with wildcard patterns."""
        deployment_repo.add(
            Deployment(
                deployment_id="gpt4-deployment",
                deployment_name="GPT-4 Deployment",
                host="localhost",
                port=8001,
                deployment_metadata=json.dumps({"model": "gpt-4"}),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="gpt35-deployment",
                deployment_name="GPT-3.5 Deployment",
                host="localhost",
                port=8002,
                deployment_metadata=json.dumps({"model": "gpt-3.5-turbo"}),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="claude-deployment",
                deployment_name="Claude Deployment",
                host="localhost",
                port=8003,
                deployment_metadata=json.dumps({"model": "claude-3"}),
            )
        )

        # Query for GPT models with wildcard
        gpt_deployments = deployment_repo.query_by_metadata({"model": "gpt-*"})

        assert len(gpt_deployments) == 2
        deployment_ids = {d.deployment_id for d in gpt_deployments}
        assert deployment_ids == {"gpt4-deployment", "gpt35-deployment"}

    def test_query_by_nested_keys(self, deployment_repo) -> None:
        """Test querying deployments with nested metadata keys."""
        deployment_repo.add(
            Deployment(
                deployment_id="multi-deployment",
                deployment_name="Multi-capability Deployment",
                host="localhost",
                port=8001,
                deployment_metadata=json.dumps({
                    "capabilities": {"llm": True, "vision": True, "tool": False}
                }),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="llm-only-deployment",
                deployment_name="LLM Only Deployment",
                host="localhost",
                port=8002,
                deployment_metadata=json.dumps({
                    "capabilities": {"llm": True, "vision": False}
                }),
            )
        )

        # Query for deployments with vision capability
        vision_deployments = deployment_repo.query_by_metadata({"capabilities.vision": True})

        assert len(vision_deployments) == 1
        assert vision_deployments[0].deployment_id == "multi-deployment"

    def test_query_by_multiple_filters(self, deployment_repo) -> None:
        """Test querying deployments with multiple filter criteria."""
        deployment_repo.add(
            Deployment(
                deployment_id="gpt4-vision",
                deployment_name="GPT-4 Vision",
                host="localhost",
                port=8001,
                deployment_metadata=json.dumps({
                    "type": "llm",
                    "model": "gpt-4",
                    "capabilities": {"vision": True}
                }),
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="gpt4-text",
                deployment_name="GPT-4 Text",
                host="localhost",
                port=8002,
                deployment_metadata=json.dumps({
                    "type": "llm",
                    "model": "gpt-4",
                    "capabilities": {"vision": False}
                }),
            )
        )

        # Query for LLM + GPT-4 + vision
        results = deployment_repo.query_by_metadata({
            "type": "llm",
            "model": "gpt-4",
            "capabilities.vision": True
        })

        assert len(results) == 1
        assert results[0].deployment_id == "gpt4-vision"

    def test_query_with_no_metadata(self, deployment_repo) -> None:
        """Test querying when deployment has no metadata."""
        deployment_repo.add(
            Deployment(
                deployment_id="no-metadata",
                deployment_name="No Metadata Deployment",
                host="localhost",
                port=8001,
                deployment_metadata=None,
            )
        )

        results = deployment_repo.query_by_metadata({"type": "llm"})

        assert len(results) == 0

    def test_query_with_invalid_metadata(self, deployment_repo) -> None:
        """Test querying with invalid JSON metadata."""
        deployment_repo.add(
            Deployment(
                deployment_id="bad-metadata",
                deployment_name="Bad Metadata Deployment",
                host="localhost",
                port=8001,
                deployment_metadata="not-valid-json",
            )
        )

        results = deployment_repo.query_by_metadata({"type": "llm"})

        assert len(results) == 0


class TestGetActiveDeployments:
    """Tests for get_active_deployments method."""

    def test_get_recent_heartbeats(self, deployment_repo) -> None:
        """Test getting deployments with recent heartbeats."""
        now = datetime.utcnow()

        # Create deployments with different heartbeat times
        deployment_repo.add(
            Deployment(
                deployment_id="active-1",
                deployment_name="Active Deployment 1",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=30),
                deployment_metadata='{}',
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="active-2",
                deployment_name="Active Deployment 2",
                host="localhost",
                port=8002,
                last_heartbeat=now - timedelta(seconds=45),
                deployment_metadata='{}',
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="inactive",
                deployment_name="Inactive Deployment",
                host="localhost",
                port=8003,
                last_heartbeat=now - timedelta(seconds=120),
                deployment_metadata='{}',
            )
        )

        # Get deployments active in last 60 seconds
        active = deployment_repo.get_active_deployments(cutoff_seconds=60)

        assert len(active) == 2
        assert all(d.deployment_id.startswith("active") for d in active)

    def test_get_active_with_custom_cutoff(self, deployment_repo) -> None:
        """Test getting active deployments with custom cutoff."""
        now = datetime.utcnow()

        deployment_repo.add(
            Deployment(
                deployment_id="very-recent",
                deployment_name="Very Recent",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=20),
                deployment_metadata='{}',
            )
        )
        deployment_repo.add(
            Deployment(
                deployment_id="somewhat-recent",
                deployment_name="Somewhat Recent",
                host="localhost",
                port=8002,
                last_heartbeat=now - timedelta(seconds=90),
                deployment_metadata='{}',
            )
        )

        # Get deployments active in last 30 seconds
        active = deployment_repo.get_active_deployments(cutoff_seconds=30)

        assert len(active) == 1
        assert active[0].deployment_id == "very-recent"

    def test_get_active_includes_dead_deployments(self, deployment_repo) -> None:
        """Test that get_active_deployments can return dead deployments if heartbeat is recent."""
        now = datetime.utcnow()

        # Create deployment with very recent heartbeat but TTL expired
        deployment_repo.add(
            Deployment(
                deployment_id="dead-but-recent",
                deployment_name="Dead But Recent",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=10),
                ttl_seconds=5,  # TTL of 5 seconds (expired)
                deployment_metadata='{}',
            )
        )

        active = deployment_repo.get_active_deployments(cutoff_seconds=60)

        # Should be included because heartbeat is recent, even though TTL expired
        assert len(active) == 1
        assert active[0].deployment_id == "dead-but-recent"

    def test_get_active_with_old_heartbeat(self, deployment_repo) -> None:
        """Test that deployments with old heartbeats are excluded."""
        now = datetime.utcnow()

        # Create deployment with very old heartbeat (older than 60 seconds)
        deployment_repo.add(
            Deployment(
                deployment_id="old-heartbeat",
                deployment_name="Old Heartbeat",
                host="localhost",
                port=8001,
                last_heartbeat=now - timedelta(seconds=120),
                deployment_metadata='{}',
            )
        )

        active = deployment_repo.get_active_deployments(cutoff_seconds=60)

        # Should be excluded because heartbeat is too old
        assert len(active) == 0
