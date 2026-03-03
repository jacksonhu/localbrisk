"""
Agent Engine 测试配置

提供 Agent Engine 测试所需的 fixtures
"""

import pytest
import tempfile
import shutil
import yaml
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


# ============================================================================
# Agent 测试数据
# ============================================================================

def create_test_agent_data() -> Dict[str, Any]:
    """创建测试 Agent 配置数据"""
    return {
        "agent_spec": {
            "baseinfo": {
                "name": "test_data_analyst",
                "description": "测试数据分析师智能体",
                "version": "1.0.0"
            },
            "active_model": "test_model",
            "llm_config": {
                "temperature": 0.7,
                "max_tokens": 2048
            }
        },
        "model_config": {
            "model_type": "endpoint",
            "endpoint_provider": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "model_id": "gpt-4",
            "temperature": 0.7
        },
        "prompt_content": """你是一个数据分析助手。

你的职责是帮助用户分析数据，提供数据洞察。

## 能力
- 数据查询
- 数据可视化
- 统计分析
""",
        "skill_config": {
            "name": "test_skill",
            "description": "测试技能",
            "version": "1.0.0",
            "tools": ["tool1", "tool2"]
        }
    }


def _create_agent_directory(agent_dir: Path, data: Dict[str, Any]) -> None:
    """在指定目录创建完整的 Agent 结构"""
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 创建 agent_spec.yaml
    with open(agent_dir / "agent_spec.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["agent_spec"], f, default_flow_style=False, allow_unicode=True)
    
    # 2. 创建 models 目录
    models_dir = agent_dir / "models"
    models_dir.mkdir(exist_ok=True)
    with open(models_dir / "test_model.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["model_config"], f, default_flow_style=False, allow_unicode=True)
    
    # 3. 创建 prompts 目录
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    with open(prompts_dir / "system.md", "w", encoding="utf-8") as f:
        f.write(data["prompt_content"])
    # 创建 prompt 元数据
    with open(prompts_dir / ".system.meta.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"description": "系统提示词", "order": 1}, f)
    
    # 4. 创建 skills 目录
    skills_dir = agent_dir / "skills"
    skills_dir.mkdir(exist_ok=True)
    test_skill_dir = skills_dir / "test_skill"
    test_skill_dir.mkdir(exist_ok=True)
    with open(test_skill_dir / "test_skill.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["skill_config"], f, default_flow_style=False, allow_unicode=True)
    with open(test_skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
        f.write("# Test Skill\n\nThis is a test skill.")
    
    # 5. 创建 workroot 目录
    workroot_dir = agent_dir / "workroot"
    workroot_dir.mkdir(exist_ok=True)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def temp_agent_dir():
    """
    创建临时 Agent 目录用于测试
    
    目录结构:
    temp_dir/
    └── test_data_analyst/
        ├── agent_spec.yaml
        ├── models/
        │   └── test_model.yaml
        ├── prompts/
        │   ├── system.md
        │   └── .system.meta.yaml
        ├── skills/
        │   └── test_skill/
        │       ├── test_skill.yaml
        │       └── SKILL.md
        └── workroot/
    """
    temp_dir = tempfile.mkdtemp(prefix="agent_test_")
    agent_dir = Path(temp_dir) / "test_data_analyst"
    
    # 创建测试数据
    data = create_test_agent_data()
    _create_agent_directory(agent_dir, data)
    
    yield {
        "temp_dir": temp_dir,
        "agent_path": str(agent_dir),
        "agent_name": "test_data_analyst",
        "data": data
    }
    
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_agents_catalog():
    """
    创建临时 Catalog 目录，包含多个 Agent
    
    目录结构:
    temp_dir/
    └── App_Data/
        └── Catalogs/
            └── test_unit/
                └── agents/
                    ├── agent_a/
                    └── agent_b/
    """
    temp_dir = tempfile.mkdtemp(prefix="catalog_test_")
    catalogs_dir = Path(temp_dir) / "App_Data" / "Catalogs" / "test_unit" / "agents"
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    
    data = create_test_agent_data()
    
    # 创建两个测试 Agent
    agent_a_dir = catalogs_dir / "agent_a"
    agent_b_dir = catalogs_dir / "agent_b"
    
    data_a = data.copy()
    data_a["agent_spec"] = data["agent_spec"].copy()
    data_a["agent_spec"]["baseinfo"] = {"name": "agent_a", "description": "Agent A"}
    
    data_b = data.copy()
    data_b["agent_spec"] = data["agent_spec"].copy()
    data_b["agent_spec"]["baseinfo"] = {"name": "agent_b", "description": "Agent B"}
    
    _create_agent_directory(agent_a_dir, data_a)
    _create_agent_directory(agent_b_dir, data_b)
    
    yield {
        "temp_dir": temp_dir,
        "catalogs_dir": str(catalogs_dir.parent),
        "business_unit_id": "test_unit",
        "agents": {
            "agent_a": str(agent_a_dir),
            "agent_b": str(agent_b_dir)
        }
    }
    
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def real_agent_path():
    """
    返回真实的 Agent 路径 (如果存在)
    
    用于集成测试，测试真实的 Agent 配置
    """
    agent_path = os.path.expanduser(
        "~/.localbrisk/App_Data/Catalogs/myunit/agents/Data_analyst"
    )
    
    if Path(agent_path).exists():
        return {
            "agent_path": agent_path,
            "business_unit_id": "myunit",
            "exists": True
        }
    else:
        return {
            "agent_path": agent_path,
            "business_unit_id": "myunit",
            "exists": False
        }
