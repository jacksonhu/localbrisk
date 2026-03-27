"""
DeepAgents 引擎单元测试

测试 deepagents_engine.py 中的 Agent 构建和执行功能
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock


class TestDeepAgentsEngineImport:
    """测试 DeepAgentsEngine 模块导入"""
    
    def test_import_deepagents_engine(self):
        """测试导入 deepagents_engine 模块"""
        from agent_engine.engine import deepagents_engine
        
        assert hasattr(deepagents_engine, 'DeepAgentsEngine')
        assert hasattr(deepagents_engine, 'AgentBuildContext')
        assert hasattr(deepagents_engine, 'get_deepagents_engine')
        assert hasattr(deepagents_engine, 'check_dependencies')
    
    def test_import_from_engine_init(self):
        """测试从 engine 包导入"""
        from agent_engine.engine import (
            DeepAgentsEngine,
            AgentBuildContext,
            get_deepagents_engine,
            check_dependencies,
        )
        
        assert DeepAgentsEngine is not None
        assert AgentBuildContext is not None
        assert get_deepagents_engine is not None
        assert check_dependencies is not None


class TestCheckDependencies:
    """测试依赖检查功能"""
    
    def test_check_dependencies_no_raise(self):
        """测试依赖检查不抛出异常"""
        from agent_engine.engine.deepagents_engine import check_dependencies
        
        # 不抛出异常，返回布尔值
        result = check_dependencies(raise_error=False)
        assert isinstance(result, bool)
    
    def test_check_dependencies_returns_status(self):
        """测试依赖检查返回正确的状态"""
        from agent_engine.engine.deepagents_engine import (
            check_dependencies,
            _LANGCHAIN_AVAILABLE,
            _DEEPAGENTS_AVAILABLE,
        )
        
        result = check_dependencies(raise_error=False)
        expected = _LANGCHAIN_AVAILABLE and _DEEPAGENTS_AVAILABLE
        assert result == expected


class TestDeepAgentsEngineSingleton:
    """测试 DeepAgentsEngine 单例模式"""
    
    def test_get_deepagents_engine_singleton(self):
        """测试获取单例 DeepAgentsEngine"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine1 = get_deepagents_engine()
        engine2 = get_deepagents_engine()
        
        assert engine1 is engine2
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        from agent_engine.engine.deepagents_engine import DeepAgentsEngine
        
        engine = DeepAgentsEngine()
        
        assert engine is not None
        assert engine._llm_factory is None  # 延迟初始化
        assert engine._model_resolver is None


class TestAgentBuildContext:
    """测试 AgentBuildContext 数据类"""
    
    def test_agent_build_context_creation(self):
        """测试 AgentBuildContext 创建"""
        from agent_engine.engine.deepagents_engine import AgentBuildContext
        
        context = AgentBuildContext(
            agent_name="test_agent",
            agent_path="/path/to/agent",
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test"}},
            model_config={"model_type": "endpoint"},
            prompts=[{"name": "system", "content": "test prompt"}],
            skills=["/path/to/skill1"],  # skills 是路径字符串列表
            output_path="/path/to/output"
        )
        
        assert context.agent_name == "test_agent"
        assert context.business_unit_id == "test_unit"
        assert len(context.prompts) == 1
        assert len(context.skills) == 1


class TestLoadAgentContext:
    """测试加载 Agent 上下文"""
    
    @pytest.mark.asyncio
    async def test_load_agent_context_success(self, temp_agent_dir):
        """测试成功加载 Agent 上下文"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_agent_dir["agent_path"],
            "test_unit"
        )
        
        assert context is not None
        assert context.agent_name == "test_data_analyst"
        assert context.business_unit_id == "test_unit"
        assert Path(context.agent_path).exists()
    
    @pytest.mark.asyncio
    async def test_load_agent_context_with_model(self, temp_agent_dir):
        """测试加载 Agent 上下文包含模型配置"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_agent_dir["agent_path"],
            "test_unit"
        )
        
        assert context.model_config is not None
        assert context.model_config.get("endpoint_provider") == "openai"
        assert context.model_config.get("model_id") == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_load_agent_context_with_prompts(self, temp_agent_dir):
        """测试加载 Agent 上下文包含提示词"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_agent_dir["agent_path"],
            "test_unit"
        )
        
        assert len(context.prompts) >= 1
        # 检查 prompts 列表中有内容
        prompt = context.prompts[0]
        assert "content" in prompt
        assert "数据分析助手" in prompt.get("content", "")
    
    @pytest.mark.asyncio
    async def test_load_agent_context_with_skills(self, temp_agent_dir):
        """测试加载 Agent 上下文包含技能"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_agent_dir["agent_path"],
            "test_unit"
        )
        
        assert len(context.skills) >= 1
        # skills 是 SkillConfig 对象列表
        from agent_engine.engine.deepagents_engine import SkillConfig
        skill_config = context.skills[0]
        assert isinstance(skill_config, SkillConfig)
        assert skill_config.name == "test_skill"
        assert "test_skill" in skill_config.absolute_path
        assert skill_config.mount_path == "/skills/test_skill/"
    
    @pytest.mark.asyncio
    async def test_load_agent_context_nonexistent_path(self):
        """测试加载不存在的 Agent 路径"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        
        with pytest.raises(ValueError, match="目录不存在"):
            await engine._load_agent_context(
                "/nonexistent/agent/path",
                "test_unit"
            )
    
    @pytest.mark.asyncio
    async def test_load_agent_context_output_created(self, temp_agent_dir):
        """测试加载时自动创建 output 目录"""
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        import shutil
        
        # 删除 output 目录
        output = Path(temp_agent_dir["agent_path"]) / "output"
        if output.exists():
            shutil.rmtree(output)
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_agent_dir["agent_path"],
            "test_unit"
        )
        
        # 验证 output 被创建
        assert Path(context.output_path).exists()


class TestBuildAgent:
    """测试构建 Agent"""
    
    @pytest.mark.asyncio
    async def test_build_agent_requires_deepagents(self, temp_agent_dir):
        """测试构建 Agent 需要 deepagents 依赖"""
        from agent_engine.engine.deepagents_engine import (
            get_deepagents_engine,
            _DEEPAGENTS_AVAILABLE,
        )
        
        if _DEEPAGENTS_AVAILABLE:
            pytest.skip("deepagents 已安装，跳过依赖检查测试")
        
        engine = get_deepagents_engine()
        
        with pytest.raises(ImportError, match="缺少必要依赖"):
            await engine.build_agent(
                temp_agent_dir["agent_path"],
                "test_unit"
            )

class TestSetModelResolver:
    """测试设置模型解析器"""
    
    def test_set_model_resolver(self):
        """测试设置模型解析器"""
        from agent_engine.engine.deepagents_engine import DeepAgentsEngine
        
        engine = DeepAgentsEngine()
        
        async def mock_resolver(unit_id, agent_name, model_name):
            return {"model_id": "test"}
        
        engine.set_model_resolver(mock_resolver)
        
        assert engine._model_resolver is mock_resolver


class TestRealAgentBuild:
    """真实 Agent 构建测试 (集成测试)"""
    
    @pytest.mark.asyncio
    async def test_load_real_agent_context(self, real_agent_path):
        """测试加载真实 Agent 上下文"""
        if not real_agent_path["exists"]:
            pytest.skip("真实 Agent 目录不存在")
        
        from agent_engine.engine.deepagents_engine import get_deepagents_engine
        
        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            real_agent_path["agent_path"],
            real_agent_path["business_unit_id"]
        )
        
        assert context is not None
        print(f"\n真实 Agent 上下文:")
        print(f"  - 名称: {context.agent_name}")
        print(f"  - 路径: {context.agent_path}")
        print(f"  - 工作目录: {context.output_path}")
        print(f"  - 提示词数量: {len(context.prompts)}")
        print(f"  - 技能数量: {len(context.skills)}")
        if context.model_config:
            print(f"  - 模型 Provider: {context.model_config.get('endpoint_provider')}")


class TestBuiltinSubagents:
    """测试内置子 Agent 定义"""

    def test_create_builtin_subagents_has_three_agents(self):
        from agent_engine.engine.subagents import create_builtin_subagents

        subagents = create_builtin_subagents(
            parent_model="mock-model",
            parent_tools=[],
            parent_backend=None,
        )

        assert len(subagents) == 3

        names = [
            item.get("name") if isinstance(item, dict) else getattr(item, "name", "")
            for item in subagents
        ]

        assert "web_crawl_summary_agent" in names
        assert "text2sql_agent" in names
        assert "ppt_summary_agent" in names
