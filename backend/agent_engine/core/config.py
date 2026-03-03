"""
Agent 配置模型定义
基于现有 Pydantic 模型扩展，实现 agent_spec.yaml 配置的强类型验证和序列化
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class RunMode(str, Enum):
    """运行模式"""
    DEBUG = "debug"      # 调试模式
    SERVICE = "service"  # 服务模式


class ModelReference(BaseModel):
    """模型引用
    
    支持格式:
    1. 仅模型名称: model_name (Model 在 Agent 目录下)
    2. schema.model 格式: schema_name.model_name (兼容旧格式)
    """
    schema_name: Optional[str] = None
    model_name: str
    full_reference: str
    
    @classmethod
    def parse(cls, reference: str) -> "ModelReference":
        """解析模型引用字符串"""
        if not reference:
            raise ValueError("模型引用不能为空")
        
        # 支持新格式：仅模型名称（Model 在 Agent 目录下）
        if "." not in reference:
            return cls(
                schema_name=None,
                model_name=reference,
                full_reference=reference
            )
        
        # 兼容旧格式：schema.model
        parts = reference.split(".", 1)
        return cls(
            schema_name=parts[0],
            model_name=parts[1],
            full_reference=reference
        )


class SkillConfig(BaseModel):
    """技能配置"""
    name: str
    enabled: bool = True
    config_path: Optional[str] = None
    # 技能详细信息（运行时加载）
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    prompt_content: Optional[str] = None
    tools: List[Dict[str, Any]] = Field(default_factory=list)


class PromptConfig(BaseModel):
    """提示词配置"""
    name: str
    enabled: bool = True
    file_path: Optional[str] = None
    # 提示词详细信息（运行时加载）
    content: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None


class LLMRuntimeConfig(BaseModel):
    """LLM 运行时配置"""
    model_reference: Optional[ModelReference] = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    response_format: str = Field(default="text", pattern="^(text|json_object)$")
    # 运行时解析的完整模型配置
    resolved_model: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_agent_llm_config(cls, llm_config: Dict[str, Any]) -> "LLMRuntimeConfig":
        """从 agent_spec.yaml 的 llm_config 创建"""
        model_ref = None
        if llm_config.get("llm_model"):
            model_ref = ModelReference.parse(llm_config["llm_model"])
        
        return cls(
            model_reference=model_ref,
            temperature=llm_config.get("temperature", 0.2),
            max_tokens=llm_config.get("max_tokens", 4096),
            response_format=llm_config.get("response_format", "text"),
        )


class AgentRuntimeConfig(BaseModel):
    """Agent 运行时配置
    
    简化的 Agent 运行时配置，仅包含必要的配置项
    """
    # 基础信息
    agent_name: str
    business_unit_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_path: Optional[str] = None
    
    # 核心配置（从 agent_spec.yaml 解析）
    llm_config: Optional[LLMRuntimeConfig] = None
    
    # 运行时扩展配置
    run_mode: RunMode = RunMode.DEBUG
    debug_mode: bool = Field(default=False, description="是否启用调试模式")
    max_execution_time: int = Field(default=300, description="最大执行时间（秒）")
    max_iterations: int = Field(default=10, description="最大迭代次数")
    enable_logging: bool = Field(default=True, description="启用日志")
    enable_tracing: bool = Field(default=False, description="启用追踪")
    
    # 原始配置（备份）
    raw_config: Optional[Dict[str, Any]] = None
    
    # 元数据
    loaded_at: Optional[datetime] = None
    config_version: Optional[str] = None
    
    class Config:
        use_enum_values = True

    @classmethod
    def from_agent_spec(
        cls,
        agent_name: str,
        business_unit_id: str,
        spec_data: Dict[str, Any],
        agent_path: Optional[str] = None
    ) -> "AgentRuntimeConfig":
        """从 agent_spec.yaml 数据创建运行时配置"""
        baseinfo = spec_data.get("baseinfo", {})
        
        # 解析 LLM 配置
        llm_config = None
        if spec_data.get("llm_config"):
            llm_config = LLMRuntimeConfig.from_agent_llm_config(spec_data["llm_config"])
        
        return cls(
            agent_name=agent_name,
            business_unit_id=business_unit_id,
            display_name=baseinfo.get("display_name", agent_name),
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            agent_path=agent_path,
            llm_config=llm_config,
            raw_config=spec_data,
            loaded_at=datetime.now(),
        )
    
    def get_model_reference(self) -> Optional[ModelReference]:
        """获取模型引用"""
        if self.llm_config and self.llm_config.model_reference:
            return self.llm_config.model_reference
        return None
