"""
Agent Engine Exception Definitions
Defines specialized exception classes with detailed error messages and suggestions
"""

from typing import Optional, Dict, Any


class AgentEngineError(Exception):
    """Agent engine base exception"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AGENT_ENGINE_ERROR"
        self.details = details or {}
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
        }


class AgentConfigError(AgentEngineError):
    """Agent config error"""
    
    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if config_path:
            details["config_path"] = config_path
        if field:
            details["field"] = field
        
        super().__init__(
            message=message,
            error_code="AGENT_CONFIG_ERROR",
            details=details,
            suggestion="Please check the agent_spec.yaml config file format and content"
        )


class AgentExecutionError(AgentEngineError):
    """Agent execution error"""
    
    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if agent_name:
            details["agent_name"] = agent_name
        if execution_id:
            details["execution_id"] = execution_id
        if step:
            details["step"] = step
        
        super().__init__(
            message=message,
            error_code="AGENT_EXECUTION_ERROR",
            details=details,
            suggestion="Please check Agent config and input data, or review detailed logs"
        )


class AgentTimeoutError(AgentEngineError):
    """Agent execution timeout error"""
    
    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if agent_name:
            details["agent_name"] = agent_name
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            error_code="AGENT_TIMEOUT_ERROR",
            details=details,
            suggestion="Consider increasing the timeout or optimizing Agent execution logic"
        )


class ModelNotFoundError(AgentEngineError):
    """Model not found error"""
    
    def __init__(
        self,
        model_reference: str,
        catalog_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["model_reference"] = model_reference
        if catalog_id:
            details["catalog_id"] = catalog_id
        
        super().__init__(
            message=f"Model '{model_reference}' not found",
            error_code="MODEL_NOT_FOUND",
            details=details,
            suggestion="Please verify the model reference format is 'schema.model_name' and the model is configured correctly"
        )


class SkillLoadError(AgentEngineError):
    """Skill load error"""
    
    def __init__(
        self,
        skill_name: str,
        agent_name: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["skill_name"] = skill_name
        if agent_name:
            details["agent_name"] = agent_name
        if reason:
            details["reason"] = reason
        
        super().__init__(
            message=f"Skill '{skill_name}' load failed: {reason or 'unknown reason'}",
            error_code="SKILL_LOAD_ERROR",
            details=details,
            suggestion="Please check the skill config file and dependencies"
        )


class PromptTemplateError(AgentEngineError):
    """Prompt template error"""
    
    def __init__(
        self,
        template_name: str,
        agent_name: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["template_name"] = template_name
        if agent_name:
            details["agent_name"] = agent_name
        if reason:
            details["reason"] = reason
        
        super().__init__(
            message=f"Prompt template '{template_name}' error: {reason or 'unknown reason'}",
            error_code="PROMPT_TEMPLATE_ERROR",
            details=details,
            suggestion="Please check template files in the prompts directory"
        )


class DaemonServiceError(AgentEngineError):
    """Daemon服务error"""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service_name:
            details["service_name"] = service_name
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="DAEMON_SERVICE_ERROR",
            details=details,
            suggestion="Please check service status and system resources"
        )
