"""Agent engine exception definitions and normalization helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional


class AgentEngineError(Exception):
    """Base exception for agent engine failures."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AGENT_ENGINE_ERROR"
        self.details = details or {}
        self.suggestion = suggestion
        self.retryable = retryable

    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception into a stable payload."""
        return {
            "error": self.error_code,
            "error_code": self.error_code,
            "error_type": type(self).__name__,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "retryable": self.retryable,
        }


class AgentConfigError(AgentEngineError):
    """Raised when agent configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        if config_path:
            payload["config_path"] = config_path
        if field:
            payload["field"] = field

        super().__init__(
            message=message,
            error_code="AGENT_CONFIG_ERROR",
            details=payload,
            suggestion="Please review the agent_spec.yaml configuration and referenced resources",
            retryable=False,
        )


class AgentExecutionError(AgentEngineError):
    """Raised when agent execution fails during runtime."""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        if agent_name:
            payload["agent_name"] = agent_name
        if execution_id:
            payload["execution_id"] = execution_id
        if step:
            payload["step"] = step

        super().__init__(
            message=message,
            error_code="AGENT_EXECUTION_ERROR",
            details=payload,
            suggestion="Please check the runtime configuration, input data, and structured logs",
            retryable=True,
        )


class AgentTimeoutError(AgentEngineError):
    """Raised when agent execution exceeds the configured timeout."""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        if agent_name:
            payload["agent_name"] = agent_name
        if timeout_seconds:
            payload["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code="AGENT_TIMEOUT_ERROR",
            details=payload,
            suggestion="Consider increasing the timeout or optimizing the agent workflow",
            retryable=True,
        )


class ModelNotFoundError(AgentEngineError):
    """Raised when a referenced model cannot be resolved."""

    def __init__(
        self,
        model_reference: str,
        catalog_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        payload["model_reference"] = model_reference
        if catalog_id:
            payload["catalog_id"] = catalog_id

        super().__init__(
            message=f"Model '{model_reference}' was not found",
            error_code="MODEL_NOT_FOUND",
            details=payload,
            suggestion="Verify the model reference and confirm the model exists in the catalog",
            retryable=False,
        )


class SkillLoadError(AgentEngineError):
    """Raised when a skill cannot be loaded."""

    def __init__(
        self,
        skill_name: str,
        agent_name: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        payload["skill_name"] = skill_name
        if agent_name:
            payload["agent_name"] = agent_name
        if reason:
            payload["reason"] = reason

        super().__init__(
            message=f"Skill '{skill_name}' failed to load: {reason or 'unknown reason'}",
            error_code="SKILL_LOAD_ERROR",
            details=payload,
            suggestion="Check the skill package files and dependency availability",
            retryable=False,
        )


class PromptTemplateError(AgentEngineError):
    """Raised when a prompt template cannot be resolved or rendered."""

    def __init__(
        self,
        template_name: str,
        agent_name: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        payload["template_name"] = template_name
        if agent_name:
            payload["agent_name"] = agent_name
        if reason:
            payload["reason"] = reason

        super().__init__(
            message=f"Prompt template '{template_name}' error: {reason or 'unknown reason'}",
            error_code="PROMPT_TEMPLATE_ERROR",
            details=payload,
            suggestion="Check the prompt templates and their referenced variables",
            retryable=False,
        )


class DaemonServiceError(AgentEngineError):
    """Raised when a supporting daemon service fails."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        if service_name:
            payload["service_name"] = service_name
        if operation:
            payload["operation"] = operation

        super().__init__(
            message=message,
            error_code="DAEMON_SERVICE_ERROR",
            details=payload,
            suggestion="Check the daemon status, runtime dependencies, and system resources",
            retryable=False,
        )


class LocalModelNotImplementedError(AgentEngineError):
    """Raised when a local model entry is configured but runtime support is still a placeholder."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        payload = details or {}
        payload["model_type"] = "local"
        if provider:
            payload["provider"] = provider
        if model_name:
            payload["model_name"] = model_name

        super().__init__(
            message="Local model runtime is not implemented yet",
            error_code="LOCAL_MODEL_NOT_IMPLEMENTED",
            details=payload,
            suggestion=(
                "Use an endpoint model for execution now, or keep the local model entry as a placeholder "
                "until the local runtime adapter is implemented"
            ),
            retryable=False,
        )



def serialize_exception(exc: Exception) -> Dict[str, Any]:
    """Normalize arbitrary exceptions into a stable error payload."""
    if isinstance(exc, AgentEngineError):
        return exc.to_dict()
    return {
        "error": "INTERNAL_ERROR",
        "error_code": "INTERNAL_ERROR",
        "error_type": type(exc).__name__,
        "message": str(exc),
        "details": {},
        "suggestion": None,
        "retryable": False,
    }
