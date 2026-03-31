"""
Agent Configuration Model Definitions
Extends existing Pydantic models for strongly-typed validation and serialization of agent_spec.yaml
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class RunMode(str, Enum):
    """Run mode"""
    DEBUG = "debug"      # Debug mode
    SERVICE = "service"  # Service mode


class ModelReference(BaseModel):
    """Model reference
    
    Supported formats:
    1. Model name only: model_name (model in Agent directory)
    2. schema.model format: schema_name.model_name (compatible with old format)
    """
    schema_name: Optional[str] = None
    model_name: str
    full_reference: str
    
    @classmethod
    def parse(cls, reference: str) -> "ModelReference":
        """Parse model reference string"""
        if not reference:
            raise ValueError("Model reference must not be empty")
        
        # Support new format: model name only (model in Agent directory)
        if "." not in reference:
            return cls(
                schema_name=None,
                model_name=reference,
                full_reference=reference
            )
        
        # Compatible with old format: schema.model
        parts = reference.split(".", 1)
        return cls(
            schema_name=parts[0],
            model_name=parts[1],
            full_reference=reference
        )


class SkillConfig(BaseModel):
    """Skill config"""
    name: str
    enabled: bool = True
    config_path: Optional[str] = None
    # Skill details (loaded at runtime)
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    prompt_content: Optional[str] = None
    tools: List[Dict[str, Any]] = Field(default_factory=list)


class PromptConfig(BaseModel):
    """Prompt config"""
    name: str
    enabled: bool = True
    file_path: Optional[str] = None
    # Prompt details (loaded at runtime)
    content: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None


class LLMRuntimeConfig(BaseModel):
    """LLM runtime配置"""
    model_reference: Optional[ModelReference] = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    response_format: str = Field(default="text", pattern="^(text|json_object)$")
    # Fully resolved model config at runtime
    resolved_model: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_agent_llm_config(cls, llm_config: Dict[str, Any]) -> "LLMRuntimeConfig":
        """Create from agent_spec.yaml llm_config"""
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
    """Agent runtime配置
    
    简化的 Agent runtime config, 仅contains必要的配置项
    """
    # Base info
    agent_name: str
    business_unit_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_path: Optional[str] = None
    
    # Core config (parsed from agent_spec.yaml)
    llm_config: Optional[LLMRuntimeConfig] = None
    
    # Runtime extension config
    run_mode: RunMode = RunMode.DEBUG
    debug_mode: bool = Field(default=False, description="Whether to enable debug mode")
    max_execution_time: int = Field(default=300, description="Max execution time (seconds)")
    max_iterations: int = Field(default=10, description="Max iterations")
    enable_logging: bool = Field(default=True, description="Enable logging")
    enable_tracing: bool = Field(default=False, description="Enable tracing")
    
    # Raw config (备份)
    raw_config: Optional[Dict[str, Any]] = None
    
    # Metadata
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
        """Create from agent_spec.yaml data运行时配置"""
        baseinfo = spec_data.get("baseinfo", {})
        
        # Parse LLM 配置
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
        """Get model reference"""
        if self.llm_config and self.llm_config.model_reference:
            return self.llm_config.model_reference
        return None
