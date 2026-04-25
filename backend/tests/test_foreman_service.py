"""Tests for ForemanService and ForemanSessionStore."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.foreman import (
    AddMembersRequest,
    ConversationDetail,
    ConversationMember,
    ConversationSummary,
    CreateConversationRequest,
    ForemanAgentInfo,
    TimelineMessage,
)
from app.services.foreman_session_store import ForemanSessionStore


# ──────────────────── ForemanSessionStore ────────────────────


class TestForemanSessionStore:
    """Session store file operations."""

    def test_save_and_load_conversation(self, tmp_path: Path):
        store = ForemanSessionStore(base_dir=tmp_path)
        detail = ConversationDetail(
            conversation_id="conv-1",
            conversation_type="direct",
            title="Test Agent",
            members=[
                ConversationMember(
                    member_id="m1",
                    business_unit_id="bu1",
                    agent_name="agent_a",
                    display_name="Agent A",
                )
            ],
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        store.save_conversation(detail)

        loaded = store.get_conversation("conv-1")
        assert loaded is not None
        assert loaded.conversation_id == "conv-1"
        assert loaded.title == "Test Agent"
        assert len(loaded.members) == 1

    def test_list_conversations_returns_sorted(self, tmp_path: Path):
        store = ForemanSessionStore(base_dir=tmp_path)
        for i, ts in enumerate(["2025-01-01T00:00:00", "2025-01-03T00:00:00", "2025-01-02T00:00:00"]):
            detail = ConversationDetail(
                conversation_id=f"conv-{i}",
                conversation_type="direct",
                title=f"Conv {i}",
                members=[],
                created_at=ts,
                updated_at=ts,
            )
            store.save_conversation(detail)

        summaries = store.list_conversations()
        assert len(summaries) == 3
        # Should be sorted by updated_at descending.
        assert summaries[0].conversation_id == "conv-1"
        assert summaries[1].conversation_id == "conv-2"
        assert summaries[2].conversation_id == "conv-0"

    def test_delete_conversation(self, tmp_path: Path):
        store = ForemanSessionStore(base_dir=tmp_path)
        detail = ConversationDetail(
            conversation_id="conv-del",
            conversation_type="direct",
            title="To Delete",
            members=[],
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        store.save_conversation(detail)
        assert store.get_conversation("conv-del") is not None

        assert store.delete_conversation("conv-del") is True
        assert store.get_conversation("conv-del") is None
        assert store.delete_conversation("conv-del") is False

    def test_timeline_append_and_read(self, tmp_path: Path):
        store = ForemanSessionStore(base_dir=tmp_path)
        # Ensure session directory exists.
        detail = ConversationDetail(
            conversation_id="conv-tl",
            conversation_type="group",
            title="Timeline Test",
            members=[],
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        store.save_conversation(detail)

        for i in range(5):
            msg = TimelineMessage(
                message_id=f"msg-{i}",
                conversation_id="conv-tl",
                role="user",
                sender_id="user",
                sender_name="You",
                content=f"Message {i}",
            )
            store.append_timeline("conv-tl", msg)

        messages = store.read_timeline("conv-tl", limit=3, offset=0)
        assert len(messages) == 3
        assert messages[0].content == "Message 0"

        messages_page2 = store.read_timeline("conv-tl", limit=3, offset=3)
        assert len(messages_page2) == 2
        assert messages_page2[0].content == "Message 3"

        assert store.count_timeline("conv-tl") == 5

    def test_update_conversation_preview(self, tmp_path: Path):
        store = ForemanSessionStore(base_dir=tmp_path)
        detail = ConversationDetail(
            conversation_id="conv-preview",
            conversation_type="direct",
            title="Preview Test",
            members=[],
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        store.save_conversation(detail)

        store.update_conversation_preview("conv-preview", "Latest message content")

        reloaded = store.get_conversation("conv-preview")
        assert reloaded.last_message_preview == "Latest message content"
        assert reloaded.updated_at > "2025-01-01T00:00:00"


# ──────────────────── ForemanService ────────────────────


class TestForemanService:
    """ForemanService CRUD and member management tests."""

    @pytest.fixture
    def foreman_service(self, tmp_path: Path, monkeypatch):
        """Create a ForemanService backed by a temp directory."""
        from app.services.foreman_service import ForemanService
        from app.services.foreman_session_store import ForemanSessionStore

        store = ForemanSessionStore(base_dir=tmp_path)
        service = ForemanService()
        service._store = store

        # Mock agent directory to avoid scanning real disk.
        mock_agents = [
            ForemanAgentInfo(
                id="bu1/agent_a",
                business_unit_id="bu1",
                business_unit_name="Business Unit 1",
                name="agent_a",
                display_name="Agent A",
                description="First test agent",
            ),
            ForemanAgentInfo(
                id="bu1/agent_b",
                business_unit_id="bu1",
                business_unit_name="Business Unit 1",
                name="agent_b",
                display_name="Agent B",
                description="Second test agent",
            ),
            ForemanAgentInfo(
                id="bu2/agent_c",
                business_unit_id="bu2",
                business_unit_name="Business Unit 2",
                name="agent_c",
                display_name="Agent C",
                description="Third test agent",
            ),
        ]
        service._agent_cache = mock_agents
        service._agent_cache_ts = 1e18  # Far future to prevent refresh.

        return service

    def test_create_direct_conversation(self, foreman_service):
        request = CreateConversationRequest(agent_ids=["bu1/agent_a"])
        detail = foreman_service.create_conversation(request)

        assert detail.conversation_type == "direct"
        assert len(detail.members) == 1
        assert detail.members[0].agent_name == "agent_a"
        assert detail.coordinator_enabled is False

    def test_create_group_conversation(self, foreman_service):
        request = CreateConversationRequest(agent_ids=["bu1/agent_a", "bu1/agent_b"])
        detail = foreman_service.create_conversation(request)

        assert detail.conversation_type == "group"
        assert len(detail.members) == 2
        assert detail.coordinator_enabled is True

    def test_create_conversation_with_invalid_agent(self, foreman_service):
        request = CreateConversationRequest(agent_ids=["bu99/nonexistent"])
        with pytest.raises(ValueError, match="Agent not found"):
            foreman_service.create_conversation(request)

    def test_list_conversations(self, foreman_service):
        foreman_service.create_conversation(CreateConversationRequest(agent_ids=["bu1/agent_a"]))
        foreman_service.create_conversation(CreateConversationRequest(agent_ids=["bu1/agent_b"]))

        summaries = foreman_service.list_conversations()
        assert len(summaries) == 2

    def test_delete_conversation(self, foreman_service):
        detail = foreman_service.create_conversation(CreateConversationRequest(agent_ids=["bu1/agent_a"]))
        assert foreman_service.delete_conversation(detail.conversation_id) is True
        assert foreman_service.get_conversation(detail.conversation_id) is None

    def test_add_members_upgrades_direct_to_group(self, foreman_service):
        detail = foreman_service.create_conversation(CreateConversationRequest(agent_ids=["bu1/agent_a"]))
        assert detail.conversation_type == "direct"

        updated = foreman_service.add_members(
            detail.conversation_id,
            AddMembersRequest(agent_ids=["bu1/agent_b"]),
        )
        assert updated.conversation_type == "group"
        assert updated.coordinator_enabled is True
        assert len(updated.members) == 2

    def test_add_members_deduplicates(self, foreman_service):
        detail = foreman_service.create_conversation(
            CreateConversationRequest(agent_ids=["bu1/agent_a", "bu1/agent_b"]),
        )
        updated = foreman_service.add_members(
            detail.conversation_id,
            AddMembersRequest(agent_ids=["bu1/agent_a", "bu2/agent_c"]),
        )
        # agent_a already exists, only agent_c should be added.
        assert len(updated.members) == 3

    def test_add_members_to_nonexistent_conversation(self, foreman_service):
        result = foreman_service.add_members(
            "nonexistent-id",
            AddMembersRequest(agent_ids=["bu1/agent_a"]),
        )
        assert result is None

    def test_build_title_direct(self, foreman_service):
        from app.services.foreman_service import ForemanService

        members = [ConversationMember(business_unit_id="bu1", agent_name="a", display_name="Agent A")]
        assert ForemanService._build_title("direct", members) == "Agent A"

    def test_build_title_group_short(self, foreman_service):
        from app.services.foreman_service import ForemanService

        members = [
            ConversationMember(business_unit_id="bu1", agent_name="a", display_name="Alpha"),
            ConversationMember(business_unit_id="bu1", agent_name="b", display_name="Beta"),
        ]
        assert ForemanService._build_title("group", members) == "Alpha · Beta"

    def test_build_title_group_long(self, foreman_service):
        from app.services.foreman_service import ForemanService

        members = [
            ConversationMember(business_unit_id="bu1", agent_name="a", display_name="Alpha"),
            ConversationMember(business_unit_id="bu1", agent_name="b", display_name="Beta"),
            ConversationMember(business_unit_id="bu1", agent_name="c", display_name="Charlie"),
            ConversationMember(business_unit_id="bu1", agent_name="d", display_name="Delta"),
        ]
        assert ForemanService._build_title("group", members) == "Alpha · Beta +2"
