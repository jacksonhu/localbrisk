"""
Agent 引擎异常定义
定义各种专用异常类，提供详细的错误信息和处理建议
"""

from typing import Optional, Dict, Any


class AgentEngineError(Exception):
    """Agent 引擎基础异常"""
    
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
        """转换为字典格式"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
        }


class AgentConfigError(AgentEngineError):
    """Agent 配置错误"""
    
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
            suggestion="请检查 agent_spec.yaml 配置文件的格式和内容"
        )


class AgentExecutionError(AgentEngineError):
    """Agent 执行错误"""
    
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
            suggestion="请检查 Agent 配置和输入数据，或查看详细日志"
        )


class AgentTimeoutError(AgentEngineError):
    """Agent 执行超时错误"""
    
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
            suggestion="考虑增加超时时间或优化 Agent 执行逻辑"
        )


class ModelNotFoundError(AgentEngineError):
    """模型未找到错误"""
    
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
            message=f"模型 '{model_reference}' 未找到",
            error_code="MODEL_NOT_FOUND",
            details=details,
            suggestion="请确认模型引用格式为 'schema.model_name'，且模型已正确配置"
        )


class SkillLoadError(AgentEngineError):
    """技能加载错误"""
    
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
            message=f"技能 '{skill_name}' 加载失败: {reason or '未知原因'}",
            error_code="SKILL_LOAD_ERROR",
            details=details,
            suggestion="请检查技能配置文件和依赖是否正确"
        )


class PromptTemplateError(AgentEngineError):
    """提示词模板错误"""
    
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
            message=f"提示词模板 '{template_name}' 错误: {reason or '未知原因'}",
            error_code="PROMPT_TEMPLATE_ERROR",
            details=details,
            suggestion="请检查 prompts 目录下的模板文件"
        )


class DaemonServiceError(AgentEngineError):
    """守护进程服务错误"""
    
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
            suggestion="请检查服务状态和系统资源"
        )
