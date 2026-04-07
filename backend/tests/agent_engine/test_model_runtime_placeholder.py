"""Tests for local model placeholder behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class TestLocalModelPlaceholder:
    """Validate stable placeholder semantics for local models."""

    @pytest.mark.asyncio
    async def test_execute_local_model_returns_structured_placeholder_error(self):
        from agent_engine.llm.services.model_executor import ModelExecutorService

        service = ModelExecutorService()
        await service.load_model(
            business_unit_id="unit-a",
            agent_name="agent-a",
            model_name="local-qwen",
            model_config=SimpleNamespace(
                model_type="local",
                local_provider="qwen2",
                model_id="qwen2-7b",
            ),
        )

        result = await service.execute(
            business_unit_id="unit-a",
            agent_name="agent-a",
            model_name="local-qwen",
            input_text="Hello",
            context={"request_id": "req-local-1", "session_id": "sess-local-1"},
        )

        assert result.status == "error"
        assert result.output is None
        assert result.error_code == "LOCAL_MODEL_NOT_IMPLEMENTED"
        assert result.error_type == "LocalModelNotImplementedError"
        assert result.placeholder is True
        assert result.retryable is False
        assert result.suggestion

    @pytest.mark.asyncio
    async def test_stream_local_model_returns_structured_placeholder_error_event(self):
        from agent_engine.llm.services.model_executor import ModelExecutorService

        service = ModelExecutorService()
        await service.load_model(
            business_unit_id="unit-a",
            agent_name="agent-a",
            model_name="local-qwen",
            model_config=SimpleNamespace(
                model_type="local",
                local_provider="qwen2",
                model_id="qwen2-7b",
            ),
        )

        events = []
        async for event in service.execute_streaming(
            business_unit_id="unit-a",
            agent_name="agent-a",
            model_name="local-qwen",
            input_text="Hello",
            context={"request_id": "req-local-2", "session_id": "sess-local-2"},
        ):
            events.append(event)

        error_event = next(event for event in events if event["event_type"] == "error")
        assert error_event["error_code"] == "LOCAL_MODEL_NOT_IMPLEMENTED"
        assert error_event["error_type"] == "LocalModelNotImplementedError"
        assert error_event["placeholder"] is True
        assert error_event["retryable"] is False

        failed_state = next(event for event in events if event.get("status") == "failed")
        assert failed_state["event_type"] == "state_change"

    def test_local_client_factory_raises_placeholder_error(self):
        from agent_engine.core.config import AgentRuntimeConfig
        from agent_engine.core.exceptions import LocalModelNotImplementedError
        from agent_engine.llm.client_factory import LLMClientFactory

        factory = LLMClientFactory()
        runtime_config = AgentRuntimeConfig(agent_name="agent-a", business_unit_id="unit-a")

        with pytest.raises(LocalModelNotImplementedError) as exc_info:
            factory._create_local_client(
                {"local_provider": "qwen2", "model_id": "qwen2-7b"},
                runtime_config,
            )

        assert exc_info.value.error_code == "LOCAL_MODEL_NOT_IMPLEMENTED"
        assert exc_info.value.details["model_type"] == "local"
