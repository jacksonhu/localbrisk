"""
YAML Parsing Utility
Provides parsing, validation, and formatting for agent_spec.yaml config files
"""

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import yaml

from ..core.config import AgentRuntimeConfig, ModelReference
from ..core.exceptions import AgentConfigError

logger = logging.getLogger(__name__)


class YamlParser:
    """YAML parser
    
    Features:
    1. Parse agent_spec.yaml files
    2. Parse model config files
    3. Parse skill config files
    4. Support variable substitution and reference resolution
    """
    
    def __init__(self):
        # Custom loader to support special tags
        self._loader = yaml.SafeLoader
    
    def parse_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Parse  YAML 文件
        
        Args:
            file_path: file path
            
        Returns:
            Parsed dict data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise AgentConfigError(
                message=f"Config file does not exist: {file_path}",
                config_path=str(file_path)
            )
        
        if not file_path.is_file():
            raise AgentConfigError(
                message=f"Path is not a file: {file_path}",
                config_path=str(file_path)
            )
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if data is None:
                data = {}
            
            logger.debug(f"Parsed YAML file: {file_path}")
            return data
            
        except yaml.YAMLError as e:
            raise AgentConfigError(
                message=f"YAML parse error: {str(e)}",
                config_path=str(file_path),
                details={"yaml_error": str(e)}
            )
    
    def parse_string(self, content: str) -> Dict[str, Any]:
        """Parse  YAML  string
        
        Args:
            content: YAML 内容 string
            
        Returns:
            Parsed dict data
        """
        try:
            data = yaml.safe_load(content)
            return data if data else {}
        except yaml.YAMLError as e:
            raise AgentConfigError(
                message=f"YAML parse error: {str(e)}",
                details={"yaml_error": str(e)}
            )
    
    def dump(self, data: Dict[str, Any], **kwargs) -> str:
        """Convert data to YAML string
        
        Args:
            data: 要转换的数据
            **kwargs: yaml.dump 的额外参数
            
        Returns:
            YAML  string
        """
        default_opts = {
            "default_flow_style": False,
            "allow_unicode": True,
            "sort_keys": False,
        }
        default_opts.update(kwargs)
        
        return yaml.dump(data, **default_opts)
    
    def save_file(
        self,
        data: Dict[str, Any],
        file_path: Union[str, Path],
        **kwargs
    ):
        """Save 数据到 YAML 文件
        
        Args:
            data: 要Save的数据
            file_path: file path
            **kwargs: yaml.dump 的额外参数
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.dump(data, **kwargs)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.debug(f"Saved YAML file: {file_path}")
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries
        
        Args:
            base: 基础字典
            override: 覆盖字典
            
        Returns:
            合并后的字典
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = value
        
        return result


def parse_agent_spec(
    file_path: Union[str, Path],
    business_unit_id: str,
    agent_name: str
) -> AgentRuntimeConfig:
    """Parse  agent_spec.yaml 文件并Create运行时配置
    
    Args:
        file_path: agent_spec.yaml file path
        business_unit_id: Business Unit ID
        agent_name: Agent name
        
    Returns:
        Agent runtime config
    """
    parser = YamlParser()
    spec_data = parser.parse_file(file_path)
    
    return AgentRuntimeConfig.from_agent_spec(
        agent_name=agent_name,
        business_unit_id=business_unit_id,
        spec_data=spec_data,
        agent_path=str(Path(file_path).parent)
    )


def parse_model_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parse model config文件
    
    Args:
        file_path: model configfile path
        
    Returns:
        model config数据
    """
    parser = YamlParser()
    return parser.parse_file(file_path)


def parse_skill_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Parse Skill配置文件
    
    Args:
        file_path: Skill配置file path
        
    Returns:
        Skill配置数据
    """
    parser = YamlParser()
    data = parser.parse_file(file_path)
    
    # 读取关联的 prompt 文件 (如果有)
    if "prompt" in data:
        prompt_file = data["prompt"]
        if not Path(prompt_file).is_absolute():
            prompt_file = Path(file_path).parent / prompt_file
        
        if Path(prompt_file).exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                data["prompt_content"] = f.read()
    
    return data


def load_prompts_from_directory(
    prompts_dir: Union[str, Path]
) -> Dict[str, str]:
    """Load all prompt templates from directory
    
    Args:
        prompts_dir: prompts directory path
        
    Returns:
        {模板名称: 模板内容} 的字典
    """
    prompts_dir = Path(prompts_dir)
    prompts = {}
    
    if not prompts_dir.exists():
        return prompts
    
    for file_path in prompts_dir.iterdir():
        if file_path.is_file() and file_path.suffix in [".md", ".txt", ".prompt"]:
            name = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                prompts[name] = f.read()
    
    return prompts


def load_skills_from_directory(
    skills_dir: Union[str, Path]
) -> List[Dict[str, Any]]:
    """Load all skill configs from directory
    
    Args:
        skills_dir: skills directory path
        
    Returns:
        skill config list
    """
    skills_dir = Path(skills_dir)
    skills = []
    
    if not skills_dir.exists():
        return skills
    
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir():
            # 查找Skill配置文件
            config_file = skill_path / f"{skill_path.name}.yaml"
            if config_file.exists():
                try:
                    skill_config = parse_skill_config(config_file)
                    skill_config["name"] = skill_path.name
                    skill_config["path"] = str(skill_path)
                    skills.append(skill_config)
                except Exception as e:
                    logger.warning(f"Failed to load skill: {skill_path.name}, error: {e}")
    
    return skills
