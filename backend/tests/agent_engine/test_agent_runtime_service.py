"""
Agent 运行时服务单元测试

测试 agent_runtime_service.py 中的运行时管理功能
使用 StreamMessage 协议（v2）
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestAgentRuntimeServiceImport:
    """测试 AgentRuntimeService 导入"""
    
    def test_import_agent_runtime_service(self):
        """测试导入 agent_runtime_service 模块"""
        from agent_engine.services import agent_runtime_service
        
        assert hasattr(agent_runtime_service, 'AgentRuntimeService')
        assert hasattr(agent_runtime_service, 'AgentStatus')
        assert hasattr(agent_runtime_service, 'MessageTranslator')
        assert hasattr(agent_runtime_service, 'get_agent_runtime_service')
    
    def test_import_from_services_init(self):
        """测试从 services 包导入"""
        from agent_engine.services import (
            AgentRuntimeService,
            AgentStatus,
            MessageTranslator,
            get_agent_runtime_service,
        )
        
        assert AgentRuntimeService is not None
        assert AgentStatus is not None
        assert MessageTranslator is not None
        assert get_agent_runtime_service is not None


class TestAgentStatus:
    """测试 AgentStatus 枚举"""
    
    def test_agent_status_values(self):
        """测试 AgentStatus 枚举值"""
        from agent_engine.services import AgentStatus
        
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.LOADING.value == "loading"
        assert AgentStatus.READY.value == "ready"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"
        assert AgentStatus.UNLOADED.value == "unloaded"


class TestMessageTranslator:
    """测试 MessageTranslator 翻译器"""

    def test_detect_phase_planning(self):
        """测试 planning 阶段检测"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.detect_phase("plan_node", "hello") == "planning"
        assert MessageTranslator.detect_phase("node", "plan something") == "planning"

    def test_detect_phase_reflecting(self):
        """测试 reflecting 阶段检测"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.detect_phase("reflect_node", "checking") == "reflecting"

    def test_detect_phase_searching(self):
        """测试 searching 阶段检测"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.detect_phase("node", "搜索文件内容") == "searching"
        assert MessageTranslator.detect_phase("node", "search for data") == "searching"

    def test_detect_phase_coding(self):
        """测试 coding 阶段检测"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.detect_phase("node", "代码生成") == "coding"
        assert MessageTranslator.detect_phase("node", "code snippet") == "coding"

    def test_detect_phase_default(self):
        """测试默认阶段"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.detect_phase("node", "general content") == "analyzing"

    def test_tool_icon_mapping(self):
        """测试工具图标映射"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.tool_icon("web_search") == "search"
        assert MessageTranslator.tool_icon("python_repl") == "code"
        assert MessageTranslator.tool_icon("office_reader") == "file"
        assert MessageTranslator.tool_icon("sql_executor") == "database"
        assert MessageTranslator.tool_icon("unknown_tool") == "tool"

    def test_parse_todo_args_list(self):
        """测试解析任务列表"""
        from agent_engine.services import MessageTranslator

        args = {
            "todos": [
                {"id": "1", "content": "任务一", "status": "pending"},
                {"id": "2", "content": "任务二", "status": "completed"},
            ]
        }
        tasks = MessageTranslator.parse_todo_args(args)

        assert len(tasks) == 2
        assert tasks[0].title == "任务一"
        assert tasks[0].status.value == "pending"
        assert tasks[1].status.value == "completed"

    def test_parse_todo_args_json_string(self):
        """测试解析 JSON 字符串形式的任务列表"""
        import json
        from agent_engine.services import MessageTranslator

        args = {
            "todos": json.dumps([
                {"id": "1", "content": "任务A", "status": "running"},
            ])
        }
        tasks = MessageTranslator.parse_todo_args(args)

        assert len(tasks) == 1
        assert tasks[0].title == "任务A"
        assert tasks[0].status.value == "running"

    def test_parse_todo_args_empty(self):
        """测试空任务列表"""
        from agent_engine.services import MessageTranslator

        assert MessageTranslator.parse_todo_args({}) == []
        assert MessageTranslator.parse_todo_args({"todos": []}) == []



class TestAgentRuntimeServiceSingleton:
    """测试 AgentRuntimeService 单例"""
    
    def test_get_agent_runtime_service_singleton(self):
        """测试获取单例 AgentRuntimeService"""
        from agent_engine.services import get_agent_runtime_service
        
        service1 = get_agent_runtime_service()
        service2 = get_agent_runtime_service()
        
        assert service1 is service2
    
    def test_service_initialization(self):
        """测试服务初始化"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        assert service is not None
        assert service._agents == {}
        assert service._engine is None


class TestAgentKeyGeneration:
    """测试 Agent Key 生成"""
    
    def test_get_agent_key(self):
        """测试生成 Agent 键"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        key = service._get_agent_key("unit1", "agent1")
        
        assert key == "unit1/agent1"


class TestAgentRuntimeServiceLoad:
    """测试 Agent 加载功能"""
    
    @pytest.mark.asyncio
    async def test_load_agent_not_found(self):
        """测试加载不存在的 Agent"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        with pytest.raises(Exception):
            await service.load_agent(
                "nonexistent_unit",
                "nonexistent_agent",
                "/nonexistent/path"
            )
    
    @pytest.mark.asyncio
    async def test_load_agent_with_mock(self, temp_agent_dir):
        """测试使用 mock 加载 Agent"""
        from agent_engine.services import AgentRuntimeService, AgentStatus
        
        service = AgentRuntimeService()
        
        mock_agent = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            state = await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            assert state is not None
            assert state.status == AgentStatus.READY
            assert state.agent_name == "test_agent"
            assert state.business_unit_id == "test_unit"
            assert state.agent_instance is mock_agent


class TestAgentRuntimeServiceStream:
    """测试 Agent 流式执行功能（StreamMessage 协议）"""
    
    @pytest.mark.asyncio
    async def test_execute_agent_stream_with_mock(self, temp_agent_dir):
        """测试使用 mock 流式执行 Agent — 输出 StreamMessage"""
        from agent_engine.services import AgentRuntimeService
        from agent_engine.core.stream_protocol import StreamMessage, MessageType
        
        service = AgentRuntimeService()
        
        # 创建 mock Agent（无 stream 方法，走 invoke 路径）
        mock_agent = MagicMock(spec=[])  # spec=[] 确保没有 stream 属性
        mock_agent.invoke = MagicMock(return_value={
            "messages": [MagicMock(content="流式回复")]
        })
        
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            messages = []
            async for msg in service.execute_agent_stream(
                "test_unit",
                "test_agent",
                "测试输入"
            ):
                messages.append(msg)
            
            assert len(messages) > 0
            
            # 所有消息都应该是 StreamMessage 类型
            for msg in messages:
                assert isinstance(msg, StreamMessage)
                assert msg.execution_id  # 有执行 ID
            
            # 最后一条应是 DONE
            done_msg = messages[-1]
            assert done_msg.type == MessageType.DONE

    @pytest.mark.asyncio
    async def test_execute_agent_stream_fallback_to_non_stream_when_stream_fails(self, temp_agent_dir):
        """测试 stream 不可用时回退到非流式 invoke"""
        from agent_engine.services import AgentRuntimeService
        from agent_engine.core.stream_protocol import MessageType

        service = AgentRuntimeService()

        class BrokenStreamAgent:
            def stream(self, input_data, config=None, stream_mode=None):
                raise RuntimeError("stream disabled")

            def invoke(self, input_data, config=None):
                return {"messages": [{"content": "非流式回退输出"}]}

        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=BrokenStreamAgent())

        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )

            messages = []
            async for msg in service.execute_agent_stream(
                "test_unit",
                "test_agent",
                "测试输入"
            ):
                messages.append(msg)

            thought = next((m for m in messages if m.type == MessageType.THOUGHT and "非流式回退输出" in str(m.payload.get("content", ""))), None)
            assert thought is not None
            assert messages[-1].type == MessageType.DONE


class TestAgentRuntimeServiceStatus:
    """测试 Agent 状态查询功能"""
    
    @pytest.mark.asyncio
    async def test_get_agent_status_not_loaded(self):
        """测试获取未加载 Agent 的状态"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        status = await service.get_agent_status("unit1", "agent1")
        
        assert status["status"] == "not_loaded"
    
    @pytest.mark.asyncio
    async def test_get_agent_status_loaded(self, temp_agent_dir):
        """测试获取已加载 Agent 的状态"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        mock_agent = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            status = await service.get_agent_status("test_unit", "test_agent")
            
            assert status["status"] == "ready"
            assert status["agent_name"] == "test_agent"
            assert status["business_unit_id"] == "test_unit"


class TestAgentRuntimeServiceCancel:
    """测试 Agent 取消功能"""
    
    @pytest.mark.asyncio
    async def test_cancel_agent_not_running(self, temp_agent_dir):
        """测试取消未运行的 Agent"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        mock_agent = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            result = await service.cancel_agent("test_unit", "test_agent")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_agent(self):
        """测试取消不存在的 Agent"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        result = await service.cancel_agent("unit1", "nonexistent")
        
        assert result is False


class TestAgentRuntimeServiceUnload:
    """测试 Agent 卸载功能"""
    
    @pytest.mark.asyncio
    async def test_unload_agent(self, temp_agent_dir):
        """测试卸载 Agent"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        mock_agent = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            result = await service.unload_agent("test_unit", "test_agent")
            
            assert result is True
            
            status = await service.get_agent_status("test_unit", "test_agent")
            assert status["status"] == "not_loaded"
    
    @pytest.mark.asyncio
    async def test_unload_nonexistent_agent(self):
        """测试卸载不存在的 Agent"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        result = await service.unload_agent("unit1", "nonexistent")
        
        assert result is False


class TestListLoadedAgents:
    """测试列出已加载 Agent"""
    
    @pytest.mark.asyncio
    async def test_list_loaded_agents_empty(self):
        """测试空列表"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        agents = service.list_loaded_agents()
        
        assert agents == []
    
    @pytest.mark.asyncio
    async def test_list_loaded_agents_with_agents(self, temp_agent_dir):
        """测试有 Agent 时的列表"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        mock_agent = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_agent = AsyncMock(return_value=mock_agent)
        
        with patch.object(service, '_ensure_engine', return_value=mock_engine):
            await service.load_agent(
                "test_unit",
                "test_agent",
                temp_agent_dir["agent_path"]
            )
            
            agents = service.list_loaded_agents()
            
            assert len(agents) == 1
            assert agents[0]["agent_name"] == "test_agent"
            assert agents[0]["business_unit_id"] == "test_unit"
            assert agents[0]["status"] == "ready"


class TestExtractOutput:
    """测试输出提取功能"""
    
    def test_extract_output_from_messages(self):
        """测试从 messages 提取输出"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        mock_msg = MagicMock()
        mock_msg.content = "测试内容"
        
        result = {"messages": [mock_msg]}
        output = service._extract_output(result)
        
        assert output == "测试内容"
    
    def test_extract_output_from_dict_messages(self):
        """测试从字典 messages 提取输出"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        result = {"messages": [{"content": "字典内容"}]}
        output = service._extract_output(result)
        
        assert output == "字典内容"
    
    def test_extract_output_from_output_field(self):
        """测试从 output 字段提取输出"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        result = {"output": "直接输出"}
        output = service._extract_output(result)
        
        assert output == "直接输出"
    
    def test_extract_output_empty(self):
        """测试空结果"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        output = service._extract_output({})
        
        assert output == ""
    
    def test_extract_output_none(self):
        """测试 None 结果"""
        from agent_engine.services import AgentRuntimeService
        
        service = AgentRuntimeService()
        
        output = service._extract_output(None)
        
        assert output == ""


class TestExecutionSnapshot:
    """测试执行快照功能"""

    def test_get_snapshot_nonexistent(self):
        """测试获取不存在的快照"""
        from agent_engine.services import AgentRuntimeService

        service = AgentRuntimeService()
        result = service.get_execution_snapshot("nonexistent-id")
        assert result is None

    def test_snapshot_structure(self):
        """测试快照数据结构"""
        from agent_engine.services.agent_runtime_service import ExecutionSnapshot
        from agent_engine.core.stream_protocol import TaskItem, TaskStatus

        snapshot = ExecutionSnapshot(execution_id="test-123")
        snapshot.thoughts.append({"content": "思考内容", "phase": "analyzing"})
        snapshot.tasks.append(TaskItem(id="t1", title="任务1", status=TaskStatus.COMPLETED))
        snapshot.artifacts.append({"artifact_type": "code", "content": "print(1)"})

        assert snapshot.execution_id == "test-123"
        assert len(snapshot.thoughts) == 1
        assert len(snapshot.tasks) == 1
        assert len(snapshot.artifacts) == 1


class TestExplainabilityFields:
    """测试可解释字段映射"""

    def test_extract_reason_and_expected_outcome(self):
        """测试从工具参数提取 why / expected_outcome"""
        from agent_engine.services import MessageTranslator

        args = {
            "reason": "先定位调用链",
            "expected_outcome": "找到协议消费点",
        }

        assert MessageTranslator.extract_reason(args) == "先定位调用链"
        assert MessageTranslator.extract_expected_outcome(args) == "找到协议消费点"

    def test_emit_final_output_markdown_only(self):
        """测试最终输出走 Markdown 文本模式"""
        from agent_engine.services import AgentRuntimeService
        from agent_engine.services.agent_runtime_service import ExecutionSnapshot
        from agent_engine.core.stream_protocol import StreamMessageBuilder, MessageType

        service = AgentRuntimeService()
        builder = StreamMessageBuilder(execution_id="test-exec")
        snapshot = ExecutionSnapshot(execution_id="test-exec")

        messages = service._emit_final_output("## 结果\n完成", builder, snapshot)

        assert len(messages) == 1
        assert messages[0].type == MessageType.THOUGHT
        assert messages[0].payload.get("mode") == "replace"
        assert "结果" in messages[0].payload.get("content", "")

    @pytest.mark.asyncio
    async def test_tool_call_running_contains_reason(self):
        """测试 TOOL_CALL running 消息携带 reason/expected_outcome"""
        from agent_engine.services import AgentRuntimeService, AgentStatus
        from agent_engine.services.agent_runtime_service import AgentRuntimeState
        from agent_engine.core.stream_protocol import MessageType

        service = AgentRuntimeService()

        class FakeChunk:
            type = "ai"
            content = ""
            tool_call_chunks = []
            tool_calls = [{
                "name": "search_content",
                "id": "call_1",
                "args": {
                    "pattern": "TODO",
                    "reason": "先定位待办项",
                    "expected_outcome": "获得修改入口",
                },
            }]

        class FakeAgent:
            def stream(self, input_data, config=None, stream_mode=None):
                yield (FakeChunk(), {"langgraph_node": "planner"})

        state = AgentRuntimeState(
            business_unit_id="u1",
            agent_name="a1",
            agent_path="/tmp/a1",
            status=AgentStatus.RUNNING,
        )
        from agent_engine.core.stream_protocol import StreamMessageBuilder
        from agent_engine.services.agent_runtime_service import ExecutionSnapshot

        builder = StreamMessageBuilder("exec-1")
        snapshot = ExecutionSnapshot(execution_id="exec-1")

        msgs = []
        async for msg in service._stream_execution(
            FakeAgent(),
            {"messages": [{"role": "user", "content": "test"}]},
            {"configurable": {"thread_id": "exec-1"}},
            "exec-1",
            "a1",
            state,
            builder,
            snapshot,
        ):
            msgs.append(msg)

        running = next((m for m in msgs if m.type == MessageType.TOOL_CALL and m.payload.get("status") == "running"), None)
        assert running is not None
        assert running.payload.get("reason") == "先定位待办项"
        assert running.payload.get("expected_outcome") == "获得修改入口"
