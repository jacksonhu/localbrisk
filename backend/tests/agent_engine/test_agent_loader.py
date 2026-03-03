"""
Agent 配置加载器单元测试

测试 agent_loader.py 中的配置加载功能
"""

import pytest
import yaml
from pathlib import Path


class TestAgentConfigLoader:
    """AgentConfigLoader 测试类"""
    
    def test_load_agent_config_success(self, temp_agent_dir):
        """测试成功加载 Agent 配置"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        assert config is not None
        assert config.name == "test_data_analyst"
        assert config.active_model == "test_model"
    
    def test_load_agent_models(self, temp_agent_dir):
        """测试加载 Agent 模型配置"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        assert len(config.models) >= 1
        assert "test_model" in config.models
        
        model = config.models["test_model"]
        assert model.endpoint_provider == "openai"
        assert model.model_id == "gpt-4"
        assert model.temperature == 0.7
    
    def test_load_agent_prompts(self, temp_agent_dir):
        """测试加载 Agent 提示词"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        assert len(config.prompts) >= 1
        
        # 查找 system prompt
        system_prompt = next(
            (p for p in config.prompts if p.name == "system"),
            None
        )
        assert system_prompt is not None
        assert "数据分析助手" in system_prompt.content
    
    def test_load_agent_skills(self, temp_agent_dir):
        """测试加载 Agent 技能"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        assert len(config.skills) >= 1
        
        # 查找 test_skill
        test_skill = next(
            (s for s in config.skills if s.name == "test_skill"),
            None
        )
        assert test_skill is not None
        assert Path(test_skill.directory).exists()
    
    def test_build_system_prompt(self, temp_agent_dir):
        """测试构建系统提示词"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        system_prompt = config.build_system_prompt()
        assert system_prompt is not None
        assert len(system_prompt) > 0
        assert "数据分析助手" in system_prompt
    
    def test_get_skill_directories(self, temp_agent_dir):
        """测试获取技能目录列表"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        # 直接从 skills 获取目录
        skill_dirs = [s.directory for s in config.skills]
        assert len(skill_dirs) >= 1
        
        for path in skill_dirs:
            assert Path(path).exists()
    
    def test_load_nonexistent_agent(self):
        """测试加载不存在的 Agent"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        with pytest.raises(ValueError, match="目录不存在"):
            load_agent_config("/nonexistent/path/to/agent")
    
    def test_load_agent_without_spec(self, temp_agent_dir):
        """测试加载没有 agent_spec.yaml 的目录"""
        from agent_engine.engine.agent_loader import load_agent_config
        import os
        
        # 删除 agent_spec.yaml
        spec_path = Path(temp_agent_dir["agent_path"]) / "agent_spec.yaml"
        os.remove(spec_path)
        
        with pytest.raises(ValueError, match="agent_spec.yaml"):
            load_agent_config(temp_agent_dir["agent_path"])


class TestAgentConfigLoaderSingleton:
    """测试 AgentConfigLoader 单例"""
    
    def test_get_agent_config_loader_singleton(self):
        """测试获取单例 AgentConfigLoader"""
        from agent_engine.engine.agent_loader import get_agent_config_loader
        
        loader1 = get_agent_config_loader()
        loader2 = get_agent_config_loader()
        
        assert loader1 is loader2


class TestModelInfo:
    """ModelInfo 数据类测试"""
    
    def test_model_info_creation(self, temp_agent_dir):
        """测试 ModelInfo 创建"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        model = config.models.get("test_model")
        
        assert model is not None
        assert model.name == "test_model"
        assert model.model_type == "endpoint"
    
    def test_model_info_raw_config(self, temp_agent_dir):
        """测试 ModelInfo 原始配置"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        model = config.models.get("test_model")
        
        # 访问原始配置
        assert model.raw_config is not None
        assert isinstance(model.raw_config, dict)
        assert model.endpoint_provider == "openai"


class TestPromptInfo:
    """PromptInfo 数据类测试"""
    
    def test_prompt_info_creation(self, temp_agent_dir):
        """测试 PromptInfo 创建"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        prompt = config.prompts[0] if config.prompts else None
        
        assert prompt is not None
        assert prompt.name is not None
        assert prompt.content is not None


class TestSkillInfo:
    """SkillInfo 数据类测试"""
    
    def test_skill_info_creation(self, temp_agent_dir):
        """测试 SkillInfo 创建"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        skill = config.skills[0] if config.skills else None
        
        assert skill is not None
        assert skill.name == "test_skill"
        assert skill.directory is not None
        assert Path(skill.directory).exists()


class TestMultiplePromptsConcat:
    """测试多个提示词拼接"""
    
    def test_multiple_prompts_concat(self, temp_agent_dir):
        """测试多个提示词正确拼接"""
        from agent_engine.engine.agent_loader import load_agent_config
        
        # 添加第二个提示词
        prompts_dir = Path(temp_agent_dir["agent_path"]) / "prompts"
        with open(prompts_dir / "context.md", "w", encoding="utf-8") as f:
            f.write("## 上下文信息\n\n这是额外的上下文。")
        
        config = load_agent_config(temp_agent_dir["agent_path"])
        
        assert len(config.prompts) >= 2
        
        system_prompt = config.build_system_prompt()
        assert "数据分析助手" in system_prompt
        assert "上下文信息" in system_prompt


class TestRealAgentConfig:
    """真实 Agent 配置测试 (集成测试)"""
    
    def test_load_real_agent_if_exists(self, real_agent_path):
        """测试加载真实 Agent 配置 (如果存在)"""
        if not real_agent_path["exists"]:
            pytest.skip("真实 Agent 目录不存在")
        
        from agent_engine.engine.agent_loader import load_agent_config
        
        config = load_agent_config(real_agent_path["agent_path"])
        
        assert config is not None
        assert config.name is not None
        print(f"\n真实 Agent 配置:")
        print(f"  - 名称: {config.name}")
        print(f"  - 激活模型: {config.active_model}")
        print(f"  - 模型数量: {len(config.models)}")
        print(f"  - 提示词数量: {len(config.prompts)}")
        print(f"  - 技能数量: {len(config.skills)}")
