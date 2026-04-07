"""Unit tests for stream protocol helpers and default prompt template."""

from agent_engine.core.stream_protocol import MessageType, StreamMessageBuilder
from agent_engine.engine.default_prompt import AGENT_DEFAULT_PROMPT


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


class TestDefaultPromptTemplate:
    """Regression tests for the default prompt template."""

    def test_rules_block_is_closed(self):
        assert AGENT_DEFAULT_PROMPT.count("<rules>") == 1
        assert AGENT_DEFAULT_PROMPT.count("</rules>") == 1
