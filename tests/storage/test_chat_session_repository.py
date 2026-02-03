"""Tests for chat session storage repository.

Tests ChatSessionRepository implementations including:
- Session creation and retrieval
- Message storage and ordering
- Config update and persistence
- Recent session listing
- Concurrent access
"""

import asyncio
import uuid
from datetime import datetime

import pytest

from configurable_agents.storage import create_storage_backend, ChatSessionRepository


@pytest.fixture
def chat_repo():
    """Create a fresh ChatSessionRepository for each test."""
    workflow_repo, state_repo, agent_repo, chat_repo, webhook_repo = create_storage_backend()
    return chat_repo


@pytest.fixture
def sample_user_id():
    """Sample user identifier for tests - unique per test run."""
    return f"test-user-{uuid.uuid4()}"


class TestChatSessionRepository:
    """Tests for ChatSessionRepository implementations."""

    def test_create_session(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test session creation returns valid session_id."""
        session_id = chat_repo.create_session(sample_user_id)

        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID format

        # Verify session can be retrieved
        session = chat_repo.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["user_identifier"] == sample_user_id
        assert session["status"] == "in_progress"
        assert session["created_at"] is not None

    def test_get_nonexistent_session(self, chat_repo: ChatSessionRepository):
        """Test retrieving a non-existent session returns None."""
        session = chat_repo.get_session("nonexistent-session-id")
        assert session is None

    def test_add_and_get_messages(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test messages are stored and retrieved in correct order."""
        session_id = chat_repo.create_session(sample_user_id)

        # Add multiple messages
        chat_repo.add_message(session_id, "user", "First message")
        chat_repo.add_message(session_id, "assistant", "First response")
        chat_repo.add_message(session_id, "user", "Second message")
        chat_repo.add_message(session_id, "assistant", "Second response")

        # Retrieve messages
        messages = chat_repo.get_messages(session_id)

        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "First response"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Second message"
        assert messages[3]["role"] == "assistant"
        assert messages[3]["content"] == "Second response"

        # Verify timestamps
        for msg in messages:
            assert msg["created_at"] is not None

    def test_add_message_with_metadata(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test messages can include metadata."""
        session_id = chat_repo.create_session(sample_user_id)

        metadata = {
            "model": "gemini-2.5-flash-lite",
            "tokens": 150,
            "cost_usd": 0.001,
        }
        chat_repo.add_message(
            session_id,
            "assistant",
            "Response with metadata",
            metadata=metadata,
        )

        messages = chat_repo.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0]["metadata"] == metadata

    def test_add_message_nonexistent_session(self, chat_repo: ChatSessionRepository):
        """Test adding message to non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            chat_repo.add_message("nonexistent-session", "user", "Test")

    def test_update_config(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test config update saves YAML and updates status."""
        session_id = chat_repo.create_session(sample_user_id)

        yaml_config = """schema_version: "1.0"
flow:
  name: test_workflow
"""

        chat_repo.update_config(session_id, yaml_config)

        # Verify session updated
        session = chat_repo.get_session(session_id)
        assert session["generated_config"] == yaml_config
        assert session["status"] == "completed"

    def test_update_config_nonexistent_session(self, chat_repo: ChatSessionRepository):
        """Test updating config for non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            chat_repo.update_config("nonexistent-session", "config: yaml")

    def test_list_recent_sessions(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test recent sessions are listed with correct ordering."""
        # Create multiple sessions
        session1 = chat_repo.create_session(sample_user_id)
        session2 = chat_repo.create_session(sample_user_id)
        session3 = chat_repo.create_session(sample_user_id)

        # Add messages to update timestamps
        chat_repo.add_message(session1, "user", "Message 1")
        chat_repo.add_message(session2, "user", "Message 2")
        chat_repo.add_message(session3, "user", "Message 3")

        # List recent sessions
        sessions = chat_repo.list_recent_sessions(sample_user_id, limit=10)

        assert len(sessions) == 3
        # Should be ordered by updated_at DESC (most recent first)
        assert sessions[0]["session_id"] == session3
        assert sessions[1]["session_id"] == session2
        assert sessions[2]["session_id"] == session1

    def test_list_recent_sessions_with_limit(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test recent sessions respect the limit parameter."""
        # Create 5 sessions with messages to ensure distinct timestamps
        session_ids = []
        for i in range(5):
            session_ids.append(chat_repo.create_session(sample_user_id))
            chat_repo.add_message(session_ids[-1], "user", f"Message {i}")

        # List with limit of 3
        sessions = chat_repo.list_recent_sessions(sample_user_id, limit=3)

        assert len(sessions) == 3
        # Should get the 3 most recent
        assert sessions[0]["session_id"] == session_ids[4]
        assert sessions[1]["session_id"] == session_ids[3]
        assert sessions[2]["session_id"] == session_ids[2]

    def test_list_recent_sessions_different_users(self, chat_repo: ChatSessionRepository):
        """Test recent sessions are filtered by user."""
        import uuid
        user1 = f"user-1-{uuid.uuid4()}"
        user2 = f"user-2-{uuid.uuid4()}"

        # Create sessions for both users
        session1 = chat_repo.create_session(user1)
        session2 = chat_repo.create_session(user2)
        session3 = chat_repo.create_session(user1)

        # List sessions for user1
        user1_sessions = chat_repo.list_recent_sessions(user1)
        assert len(user1_sessions) >= 2
        # Filter to just the sessions we created
        user1_created = [s for s in user1_sessions if s["session_id"] in [session1, session3]]
        assert len(user1_created) == 2
        assert all(s["user_identifier"] == user1 for s in user1_created)

        # List sessions for user2
        user2_sessions = chat_repo.list_recent_sessions(user2)
        assert len(user2_sessions) >= 1
        # Filter to just the sessions we created
        user2_created = [s for s in user2_sessions if s["session_id"] == session2]
        assert len(user2_created) == 1

    def test_session_status_transitions(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test session status changes through lifecycle."""
        session_id = chat_repo.create_session(sample_user_id)

        # Initial status
        session = chat_repo.get_session(session_id)
        assert session["status"] == "in_progress"

        # Add config - status becomes completed
        chat_repo.update_config(session_id, "config: test")
        session = chat_repo.get_session(session_id)
        assert session["status"] == "completed"

    def test_get_messages_empty_session(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test getting messages from a session with no messages."""
        session_id = chat_repo.create_session(sample_user_id)
        messages = chat_repo.get_messages(session_id)
        assert messages == []

    def test_concurrent_message_add(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test concurrent message additions (SQLite WAL mode)."""
        session_id = chat_repo.create_session(sample_user_id)

        async def add_messages():
            """Add multiple messages concurrently."""
            tasks = []
            for i in range(10):
                task = asyncio.create_task(
                    asyncio.to_thread(
                        chat_repo.add_message,
                        session_id,
                        "user",
                        f"Concurrent message {i}",
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

        # Run concurrent additions
        asyncio.run(add_messages())

        # Verify all messages were added
        messages = chat_repo.get_messages(session_id)
        assert len(messages) == 10

        # Verify content
        contents = [m["content"] for m in messages]
        for i in range(10):
            assert f"Concurrent message {i}" in contents

    def test_to_dict_methods(self, chat_repo: ChatSessionRepository, sample_user_id: str):
        """Test to_dict() methods return proper data structures."""
        from configurable_agents.storage.models import ChatSession, ChatMessage

        # Test ChatSession.to_dict()
        session_id = chat_repo.create_session(sample_user_id)
        session = chat_repo.get_session(session_id)

        assert isinstance(session, dict)
        assert "session_id" in session
        assert "user_identifier" in session
        assert "created_at" in session
        assert "status" in session
        assert isinstance(session["created_at"], str)  # ISO format string

        # Test ChatMessage.to_dict()
        chat_repo.add_message(session_id, "user", "Test message")
        messages = chat_repo.get_messages(session_id)

        assert isinstance(messages[0], dict)
        assert "id" in messages[0]
        assert "role" in messages[0]
        assert "content" in messages[0]
        assert "created_at" in messages[0]
        assert isinstance(messages[0]["created_at"], str)  # ISO format string
