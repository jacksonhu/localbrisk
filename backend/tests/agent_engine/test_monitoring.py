"""Unit tests for runtime observability helpers."""

from __future__ import annotations


def test_scoped_logging_context_restores_previous_state():
    from agent_engine.monitoring import get_logging_context, scoped_logging_context

    assert get_logging_context() == {}

    with scoped_logging_context(request_id="req-1", session_id="sess-1"):
        assert get_logging_context()["request_id"] == "req-1"
        with scoped_logging_context(agent_id="agent-a"):
            current = get_logging_context()
            assert current["request_id"] == "req-1"
            assert current["agent_id"] == "agent-a"
        assert "agent_id" not in get_logging_context()

    assert get_logging_context() == {}



def test_emit_runtime_event_uses_context_and_updates_metrics():
    from agent_engine.monitoring import emit_runtime_event, runtime_metrics, scoped_logging_context

    with scoped_logging_context(request_id="req-2", session_id="sess-2", business_unit_id="unit-a"):
        payload = emit_runtime_event("test.runtime.event", duration_ms=12.5, status="ok")

    assert payload["event_name"] == "test.runtime.event"
    assert payload["request_id"] == "req-2"
    assert payload["session_id"] == "sess-2"
    assert payload["business_unit_id"] == "unit-a"
    assert payload["status"] == "ok"

    snapshot = runtime_metrics.snapshot()
    assert snapshot["counters"]["test.runtime.event"] >= 1
    assert snapshot["avg_duration_ms"]["test.runtime.event"] >= 12.5
