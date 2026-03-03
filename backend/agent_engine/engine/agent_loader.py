"""
Agent 配置加载器

负责从 Agent 目录加载和解析配置，支持：
- agent_spec.yaml 基础配置
- models/ 目录下的模型配置
- prompts/ 目录下的系统提示
- skills/ 目录下的技能配置
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """模型配置信息"""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    model_type: str = "endpoint"
    enabled: bool = True
    
    # 端点模型配置
    endpoint_provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    
    # 运行时参数
    temperature: float = 0.0
    max_tokens: int = 4096
    
    # 原始配置
    raw_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ModelInfo":
        """从 YAML 文件加载模型配置"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        baseinfo = config.get("baseinfo", {})
        
        # 处理 temperature 拼写错误兼容
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
    """提示词配置信息"""
    name: str
    content: str
    file_path: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    order: int = 0
    
    # 元数据
    meta: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, md_path: Path) -> "PromptInfo":
        """从 MD 文件及其元数据加载提示词"""
        name = md_path.stem
        
        # 读取内容
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 读取元数据
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
    """技能配置信息"""
    name: str
    directory: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    
    # SKILL.md 路径
    skill_md_path: Optional[str] = None
    
    # 元配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_directory(cls, skill_dir: Path) -> Optional["SkillInfo"]:
        """从技能目录加载配置"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        
        name = skill_dir.name
        
        # 尝试加载 yaml 配置
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
    """完整的 Agent 配置"""
    name: str
    path: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # 激活的模型
    active_model: Optional[str] = None
    
    # 所有配置
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    prompts: List[PromptInfo] = field(default_factory=list)
    skills: List[SkillInfo] = field(default_factory=list)
    
    # 工作目录
    workroot: Optional[str] = None
    
    # 原始 spec
    raw_spec: Dict[str, Any] = field(default_factory=dict)
    
    def get_active_model(self) -> Optional[ModelInfo]:
        """获取激活的模型配置"""
        if self.active_model and self.active_model in self.models:
            return self.models[self.active_model]
        return None
    
    def get_enabled_prompts(self) -> List[PromptInfo]:
        """获取所有启用的提示词，按 order 排序"""
        enabled = [p for p in self.prompts if p.enabled]
        return sorted(enabled, key=lambda p: p.order)
    
    def get_enabled_skills(self) -> List[SkillInfo]:
        """获取所有启用的技能"""
        return [s for s in self.skills if s.enabled]
    
    def get_skill_paths(self) -> List[str]:
        """获取所有启用技能的目录路径"""
        return [s.directory for s in self.get_enabled_skills()]
    
    def build_system_prompt(self) -> Optional[str]:
        """构建完整的系统提示
        
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
    """Agent 配置加载器"""
    
    def __init__(self):
        logger.debug("初始化 AgentConfigLoader")
    
    def load(self, agent_path: str) -> AgentConfig:
        """加载 Agent 配置
        
        Args:
            agent_path: Agent 目录路径
            
        Returns:
            AgentConfig: 完整的 Agent 配置
        """
        agent_path = os.path.expanduser(agent_path)
        path = Path(agent_path)
        
        if not path.exists():
            raise ValueError(f"Agent 目录不存在: {agent_path}")
        
        logger.info(f"加载 Agent 配置: {agent_path}")
        
        # 1. 加载 agent_spec.yaml
        spec = self._load_spec(path)
        
        baseinfo = spec.get("baseinfo", {})
        name = baseinfo.get("name", path.name)
        
        # 2. 确定激活的模型
        active_model = spec.get("active_model")
        if not active_model:
            llm_config = spec.get("llm_config", {})
            active_model = llm_config.get("llm_model")
        
        # 3. 加载模型配置
        models = self._load_models(path)
        
        # 4. 加载提示词
        prompts = self._load_prompts(path)
        
        # 5. 加载技能
        skills = self._load_skills(path)
        
        # 6. 确定 workroot
        workroot = str(path / "workroot")
        os.makedirs(workroot, exist_ok=True)
        
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
            workroot=workroot,
            raw_spec=spec
        )
        
        logger.info(
            f"Agent 配置加载完成: name={config.name}, "
            f"models={len(config.models)}, "
            f"prompts={len(config.prompts)}, "
            f"skills={len(config.skills)}"
        )
        
        return config
    
    def _load_spec(self, path: Path) -> Dict[str, Any]:
        """加载 agent_spec.yaml"""
        spec_path = path / "agent_spec.yaml"
        if not spec_path.exists():
            raise ValueError(f"agent_spec.yaml 不存在: {spec_path}")
        
        with open(spec_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_models(self, path: Path) -> Dict[str, ModelInfo]:
        """加载所有模型配置"""
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
                logger.debug(f"加载模型: {model.name}")
            except Exception as e:
                logger.error(f"加载模型失败 {yaml_file}: {e}")
        
        return models
    
    def _load_prompts(self, path: Path) -> List[PromptInfo]:
        """加载所有提示词"""
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
                logger.debug(f"加载提示词: {prompt.name}")
            except Exception as e:
                logger.error(f"加载提示词失败 {md_file}: {e}")
        
        return prompts
    
    def _load_skills(self, path: Path) -> List[SkillInfo]:
        """加载所有技能"""
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
                logger.debug(f"加载技能: {skill.name}")
        
        return skills


# 全局加载器实例
_loader_instance: Optional[AgentConfigLoader] = None


def get_agent_config_loader() -> AgentConfigLoader:
    """获取全局配置加载器实例"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = AgentConfigLoader()
    return _loader_instance


def load_agent_config(agent_path: str) -> AgentConfig:
    """加载 Agent 配置的便捷函数
    
    Args:
        agent_path: Agent 目录路径
        
    Returns:
        AgentConfig: 完整的 Agent 配置
    """
    loader = get_agent_config_loader()
    return loader.load(agent_path)
