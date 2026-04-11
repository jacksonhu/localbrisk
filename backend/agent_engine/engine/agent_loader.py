"""
Agent configuration loader

Loads and parses config from Agent directories, supports:
- agent_spec.yaml base configuration
- Model configs under models/ directory
- System prompts under prompts/ directory
- Skill configs under skills/ directory
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import yaml

from .agent_context_loader import ensure_output_dir, load_agent_spec, resolve_agent_path

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model config信息"""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    model_type: str = "endpoint"
    enabled: bool = True
    
    # Endpoint model config
    endpoint_provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    
    # Runtime parameters
    temperature: float = 0.0
    max_tokens: int = 4096
    
    # Raw config
    raw_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ModelInfo":
        """Load from YAML filemodel config"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        baseinfo = config.get("baseinfo", {})
        
        # Handle temperature typo compatibility
        temperature = config.get("temperature") or config.get("tempreture", 0.0)
        
        return cls(
            name=baseinfo.get("name", yaml_path.stem),
            display_name=baseinfo.get("display_name"),
            description=baseinfo.get("description"),
            model_type=config.get("model_type", "endpoint"),
            enabled=config.get("enabled", True),
            endpoint_provider=config.get("endpoint_provider"),
            api_base_url=config.get("api_base_url"),
            api_key=config.get("api_key"),
            model_id=config.get("model_id"),
            temperature=float(temperature) if temperature else 0.0,
            max_tokens=config.get("max_tokens", 4096),
            raw_config=config
        )


@dataclass
class PromptInfo:
    """Prompt config信息"""
    name: str
    content: str
    file_path: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    order: int = 0
    
    # Metadata
    meta: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, md_path: Path) -> "PromptInfo":
        """Load from MD file with metadata提示词"""
        name = md_path.stem
        
        # Read content
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Read metadata
        meta_path = md_path.parent / f".{name}.meta.yaml"
        meta = {}
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f) or {}
        
        return cls(
            name=name,
            content=content,
            file_path=str(md_path),
            display_name=meta.get("display_name", name),
            description=meta.get("description"),
            enabled=meta.get("enabled", True),
            order=meta.get("order", 0),
            meta=meta
        )


@dataclass
class SkillInfo:
    """Skill config信息"""
    name: str
    directory: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    
    # SKILL.md path
    skill_md_path: Optional[str] = None
    
    # Meta config
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_directory(cls, skill_dir: Path) -> Optional["SkillInfo"]:
        """Load from skill directory配置"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        
        name = skill_dir.name
        
        # 尝试Load yaml 配置
        config = {}
        yaml_file = skill_dir / f"{name}.yaml"
        if yaml_file.exists():
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        
        baseinfo = config.get("baseinfo", {})
        
        return cls(
            name=name,
            directory=str(skill_dir),
            display_name=baseinfo.get("display_name", name),
            description=baseinfo.get("description"),
            enabled=config.get("enabled", True),
            skill_md_path=str(skill_md),
            config=config
        )


@dataclass
class AgentConfig:
    """Complete Agent 配置"""
    name: str
    path: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Active model
    active_model: Optional[str] = None
    
    # All configs
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    prompts: List[PromptInfo] = field(default_factory=list)
    skills: List[SkillInfo] = field(default_factory=list)
    
    # Working directory
    output: Optional[str] = None
    
    # Raw spec
    raw_spec: Dict[str, Any] = field(default_factory=dict)
    
    def get_active_model(self) -> Optional[ModelInfo]:
        """Get 激活的model config"""
        if self.active_model and self.active_model in self.models:
            return self.models[self.active_model]
        return None
    
    def get_enabled_prompts(self) -> List[PromptInfo]:
        """Get 所有启用的提示词, 按 order 排序"""
        enabled = [p for p in self.prompts if p.enabled]
        return sorted(enabled, key=lambda p: p.order)
    
    def get_enabled_skills(self) -> List[SkillInfo]:
        """Get 所有启用的Skill"""
        return [s for s in self.skills if s.enabled]
    
    def get_skill_paths(self) -> List[str]:
        """Get 所有启用Skill的directory path"""
        return [s.directory for s in self.get_enabled_skills()]
    
    def build_system_prompt(self) -> Optional[str]:
        """Build 完整的系统提示
        
        将所有启用的 prompt 按顺序拼接
        """
        enabled_prompts = self.get_enabled_prompts()
        if not enabled_prompts:
            return None
        
        parts = []
        for prompt in enabled_prompts:
            content = prompt.content.strip()
            if content:
                parts.append(f"## {prompt.name}\n\n{content}")
        
        if not parts:
            return None
        
        return "\n\n---\n\n".join(parts)


class AgentConfigLoader:
    """Agent configLoad器"""
    
    def __init__(self):
        logger.debug("Initializing AgentConfigLoader")
    
    def load(self, agent_path: str) -> AgentConfig:
        """Load Agent 配置
        
        Args:
            agent_path: Agent directory path
            
        Returns:
            AgentConfig: Complete Agent configuration
        """
        path = resolve_agent_path(agent_path)
        agent_path = str(path)

        logger.info(f"Loading Agent 配置: {agent_path}")

        # 1. Load agent_spec.yaml
        spec = self._load_spec(path)
        
        baseinfo = spec.get("baseinfo", {})
        name = baseinfo.get("name", path.name)
        
        # 2. 确定active model
        active_model = spec.get("active_model")
        if not active_model:
            llm_config = spec.get("llm_config", {})
            active_model = llm_config.get("llm_model")
        
        # 3. Loadmodel config
        models = self._load_models(path)
        
        # 4. Load提示词
        prompts = self._load_prompts(path)
        
        # 5. LoadSkill
        skills = self._load_skills(path)
        
        # 6. 确定 output
        output = ensure_output_dir(path)
        
        config = AgentConfig(
            name=name,
            path=agent_path,
            display_name=baseinfo.get("display_name", name),
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            active_model=active_model,
            models=models,
            prompts=prompts,
            skills=skills,
            output=output,
            raw_spec=spec
        )
        
        logger.info(
            f"Agent 配置Load完成: name={config.name}, "
            f"models={len(config.models)}, "
            f"prompts={len(config.prompts)}, "
            f"skills={len(config.skills)}"
        )
        
        return config
    
    def _load_spec(self, path: Path) -> Dict[str, Any]:
        """Load ``agent_spec.yaml`` via the shared runtime helper."""
        return load_agent_spec(path)
    
    def _load_models(self, path: Path) -> Dict[str, ModelInfo]:
        """Load 所有model config"""
        models = {}
        models_dir = path / "models"
        
        if not models_dir.exists():
            return models
        
        for yaml_file in models_dir.glob("*.yaml"):
            if yaml_file.name.startswith("."):
                continue
            
            try:
                model = ModelInfo.from_yaml(yaml_file)
                models[model.name] = model
                logger.debug(f"Loading 模型: {model.name}")
            except Exception as e:
                logger.error(f"Failed to load 模型failed {yaml_file}: {e}")
        
        return models
    
    def _load_prompts(self, path: Path) -> List[PromptInfo]:
        """Load 所有提示词"""
        prompts = []
        prompts_dir = path / "prompts"
        
        if not prompts_dir.exists():
            return prompts
        
        for md_file in sorted(prompts_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue
            
            try:
                prompt = PromptInfo.from_file(md_file)
                prompts.append(prompt)
                logger.debug(f"Loading 提示词: {prompt.name}")
            except Exception as e:
                logger.error(f"Failed to load 提示词failed {md_file}: {e}")
        
        return prompts
    
    def _load_skills(self, path: Path) -> List[SkillInfo]:
        """Load 所有Skill"""
        skills = []
        skills_dir = path / "skills"
        
        if not skills_dir.exists():
            return skills
        
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill = SkillInfo.from_directory(skill_dir)
            if skill:
                skills.append(skill)
                logger.debug(f"Loading Skill: {skill.name}")
        
        return skills


# Global loader instance
_loader_instance: Optional[AgentConfigLoader] = None


def get_agent_config_loader() -> AgentConfigLoader:
    """Get global config loader instance"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = AgentConfigLoader()
    return _loader_instance


def load_agent_config(agent_path: str) -> AgentConfig:
    """Load Agent config convenience function
    
    Args:
        agent_path: Agent directory path
        
    Returns:
        AgentConfig: Complete Agent configuration
    """
    loader = get_agent_config_loader()
    return loader.load(agent_path)
