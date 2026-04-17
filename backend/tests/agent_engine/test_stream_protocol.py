"""Unit tests for stream protocol helpers."""

from agent_engine.core.stream_protocol import MessageType, StreamMessageBuilder


class TestStreamMessageBuilderError:
    """Regression tests for error message construction."""

    def test_error_message_includes_error_code(self):
        builder = StreamMessageBuilder("execution-1")

        message = builder.error(
            message="Local model is not implemented",
            error_type="NotImplementedError",
            error_code="LOCAL_MODEL_NOT_IMPLEMENTED",
            suggestion="Switch to a supported provider.",
            retryable=False,
        )

        assert message.type == MessageType.ERROR
        assert message.execution_id == "execution-1"
        assert message.payload["message"] == "Local model is not implemented"
        assert message.payload["error_type"] == "NotImplementedError"
        assert message.payload["error_code"] == "LOCAL_MODEL_NOT_IMPLEMENTED"
        assert message.payload["suggestion"] == "Switch to a supported provider."
        assert message.payload["retryable"] is False
