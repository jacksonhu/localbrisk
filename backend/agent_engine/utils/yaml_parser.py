"""
YAML 解析工具
提供 agent_spec.yaml 配置文件的解析、验证和格式化功能
"""

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import yaml

from ..core.config import AgentRuntimeConfig, ModelReference
from ..core.exceptions import AgentConfigError

logger = logging.getLogger(__name__)


class YamlParser:
    """YAML 解析器
    
    功能：
    1. 解析 agent_spec.yaml 文件
    2. 解析 model 配置文件
    3. 解析 skill 配置文件
    4. 支持变量替换和引用解析
    """
    
    def __init__(self):
        # 自定义加载器以支持特殊标签
        self._loader = yaml.SafeLoader
    
    def parse_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """解析 YAML 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析后的字典数据
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise AgentConfigError(
                message=f"配置文件不存在: {file_path}",
                config_path=str(file_path)
            )
        
        if not file_path.is_file():
            raise AgentConfigError(
                message=f"路径不是文件: {file_path}",
                config_path=str(file_path)
            )
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if data is None:
                data = {}
            
            logger.debug(f"解析 YAML 文件: {file_path}")
            return data
            
        except yaml.YAMLError as e:
            raise AgentConfigError(
                message=f"YAML 解析错误: {str(e)}",
                config_path=str(file_path),
                details={"yaml_error": str(e)}
            )
    
    def parse_string(self, content: str) -> Dict[str, Any]:
        """解析 YAML 字符串
        
        Args:
            content: YAML 内容字符串
            
        Returns:
            解析后的字典数据
        """
        try:
            data = yaml.safe_load(content)
            return data if data else {}
        except yaml.YAMLError as e:
            raise AgentConfigError(
                message=f"YAML 解析错误: {str(e)}",
                details={"yaml_error": str(e)}
            )
    
    def dump(self, data: Dict[str, Any], **kwargs) -> str:
        """将数据转换为 YAML 字符串
        
        Args:
            data: 要转换的数据
            **kwargs: yaml.dump 的额外参数
            
        Returns:
            YAML 字符串
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
        """保存数据到 YAML 文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
            **kwargs: yaml.dump 的额外参数
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.dump(data, **kwargs)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.debug(f"保存 YAML 文件: {file_path}")
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典
        
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
    """解析 agent_spec.yaml 文件并创建运行时配置
    
    Args:
        file_path: agent_spec.yaml 文件路径
        business_unit_id: Business Unit ID
        agent_name: Agent 名称
        
    Returns:
        Agent 运行时配置
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
    """解析模型配置文件
    
    Args:
        file_path: 模型配置文件路径
        
    Returns:
        模型配置数据
    """
    parser = YamlParser()
    return parser.parse_file(file_path)


def parse_skill_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """解析技能配置文件
    
    Args:
        file_path: 技能配置文件路径
        
    Returns:
        技能配置数据
    """
    parser = YamlParser()
    data = parser.parse_file(file_path)
    
    # 读取关联的 prompt 文件（如果有）
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
    """从目录加载所有提示词模板
    
    Args:
        prompts_dir: prompts 目录路径
        
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
    """从目录加载所有技能配置
    
    Args:
        skills_dir: skills 目录路径
        
    Returns:
        技能配置列表
    """
    skills_dir = Path(skills_dir)
    skills = []
    
    if not skills_dir.exists():
        return skills
    
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir():
            # 查找技能配置文件
            config_file = skill_path / f"{skill_path.name}.yaml"
            if config_file.exists():
                try:
                    skill_config = parse_skill_config(config_file)
                    skill_config["name"] = skill_path.name
                    skill_config["path"] = str(skill_path)
                    skills.append(skill_config)
                except Exception as e:
                    logger.warning(f"加载技能失败: {skill_path.name}, 错误: {e}")
    
    return skills
