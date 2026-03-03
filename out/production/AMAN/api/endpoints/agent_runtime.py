"""
Agent 运行时 API
提供 Agent 启动、停止、状态查询等运行时管理接口

支持两种流式协议:
1. v1: 旧协议（ExecutionEvent），保留兼容
2. v2: 新协议（StreamMessage），支持 THOUGHT/TASK_LIST/ARTIFACT/STATUS/ERROR/DONE
"""

import logging
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_engine.services import get_agent_runtime_service


logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求/响应模型 ====================

class AgentLoadRequest(BaseModel):
    """加载 Agent 请求"""
    business_unit_id: str = Field(..., description="BusinessUnit ID")
    agent_name: str = Field(..., description="Agent 名称")


class AgentExecuteRequest(BaseModel):
    """执行 Agent 请求"""
    input: str = Field(..., description="用户输入")
    context: Optional[Dict[str, Any]] = Field(default=None, description="执行上下文")


class AgentScheduleRequest(BaseModel):
    """调度执行请求"""
    input: str = Field(..., description="用户输入")
    context: Optional[Dict[str, Any]] = Field(default=None, description="执行上下文")
    priority: int = Field(default=0, description="优先级")


class AgentChainRequest(BaseModel):
    """Agent 链执行请求"""
    agent_names: List[str] = Field(..., description="Agent 名称列表")
    input: str = Field(..., description="初始输入")
    context: Optional[Dict[str, Any]] = Field(default=None, description="执行上下文")


class ServiceStartRequest(BaseModel):
    """启动服务请求"""
    auto_restart: bool = Field(default=True, description="自动重启")
    max_restarts: int = Field(default=3, description="最大重启次数")


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: str
    agent_name: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class StatusResponse(BaseModel):
    """状态响应"""
    execution_id: Optional[str] = None
    status: str
    current_step: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    execution_mode: Optional[str] = None


class LoadResponse(BaseModel):
    """加载响应"""
    message: str
    agent_name: str
    business_unit_id: str
    status: str


class CancelResponse(BaseModel):
    """取消响应"""
    message: str
    success: bool


class UnloadResponse(BaseModel):
    """卸载响应"""
    message: str
    success: bool


# ==================== API 端点 ====================

@router.post("/{business_unit_id}/agents/{agent_name}/load", response_model=LoadResponse)
async def load_agent(
    business_unit_id: str,
    agent_name: str
):
    """加载 Agent"""
    logger.info(f"加载 Agent: {business_unit_id}/{agent_name}")
    
    try:
        service = get_agent_runtime_service()
        state = await service.load_agent(business_unit_id, agent_name)
        
        return LoadResponse(
            message=f"Agent {agent_name} 加载成功",
            agent_name=agent_name,
            business_unit_id=business_unit_id,
            status=state.status.value,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Agent 配置不存在: {e}")
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"缺少依赖: {e}")
    except Exception as e:
        logger.exception(f"加载 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载 Agent 失败: {e}")


@router.post("/{business_unit_id}/agents/{agent_name}/execute", response_model=ExecutionResponse)
async def execute_agent(
    business_unit_id: str,
    agent_name: str,
    request: AgentExecuteRequest
):
    """执行 Agent（同步）"""
    logger.info(f"执行 Agent: {business_unit_id}/{agent_name}, input_length={len(request.input)}")
    
    try:
        service = get_agent_runtime_service()
        result = await service.execute_agent(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            user_input=request.input,
            context=request.context,
        )
        
        return ExecutionResponse(
            execution_id=result.get("execution_id", ""),
            agent_name=agent_name,
            status=result.get("status", "unknown"),
            output=result.get("output"),
            error=result.get("error"),
            execution_time_ms=result.get("execution_time_ms"),
        )
    except Exception as e:
        logger.exception(f"执行 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行 Agent 失败: {e}")


# ==================== v1 流式端点（保留兼容） ====================

@router.post("/{business_unit_id}/agents/{agent_name}/execute/stream")
async def execute_agent_streaming(
    business_unit_id: str,
    agent_name: str,
    request: AgentExecuteRequest
):
    """流式执行 Agent（v1 协议）"""
    logger.info(f"流式执行 Agent (v1): {business_unit_id}/{agent_name}")
    
    async def event_generator():
        try:
            service = get_agent_runtime_service()
            
            async for event in service.execute_agent_stream(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                user_input=request.input,
                context=request.context,
            ):
                event_data = event.to_dict()
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.exception(f"v1 流式执行失败: {e}")
            error_event = {
                "event_type": "error",
                "error": str(e),
                "level": "error",
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== v2 流式端点（新协议） ====================

@router.post("/{business_unit_id}/agents/{agent_name}/execute/stream/v2")
async def execute_agent_streaming_v2(
    business_unit_id: str,
    agent_name: str,
    request: AgentExecuteRequest
):
    """流式执行 Agent（v2 协议）
    
    使用新的 StreamMessage 协议，前端根据 type 字段分流处理:
    - THOUGHT  → 左侧思考面板（打字机效果）
    - TASK_LIST → 左侧任务列表
    - ARTIFACT → 右侧制品展示
    - STATUS   → 瞬时状态提示
    - ERROR    → 错误信息
    - DONE     → 执行完成
    """
    logger.info(f"流式执行 Agent (v2): {business_unit_id}/{agent_name}")
    
    async def event_generator():
        try:
            service = get_agent_runtime_service()
            
            async for message in service.execute_agent_stream_v2(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                user_input=request.input,
                context=request.context,
            ):
                yield message.to_sse()
                
        except Exception as e:
            logger.exception(f"v2 流式执行失败: {e}")
            import time
            error_data = {
                "type": "ERROR",
                "payload": {
                    "message": str(e),
                    "error_type": type(e).__name__,
                    "retryable": True,
                },
                "execution_id": "",
                "timestamp": time.time(),
                "seq": 0,
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 重连快照端点 ====================

@router.get("/{business_unit_id}/agents/{agent_name}/execution/{execution_id}/snapshot")
async def get_execution_snapshot(
    business_unit_id: str,
    agent_name: str,
    execution_id: str
):
    """获取执行快照（用于断线重连）
    
    返回指定执行 ID 的全量快照，包含已有的思考记录、任务列表和制品列表。
    前端重连后调用此接口恢复状态。
    """
    logger.info(f"获取执行快照: {execution_id}")
    
    try:
        service = get_agent_runtime_service()
        snapshot = service.get_execution_snapshot(execution_id)
        
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"未找到执行 ID {execution_id} 的快照"
            )
        
        return snapshot
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取快照失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取快照失败: {e}")


# ==================== 其他端点 ====================

@router.get("/{business_unit_id}/agents/{agent_name}/status", response_model=StatusResponse)
async def get_agent_status(business_unit_id: str, agent_name: str):
    """获取 Agent 执行状态"""
    try:
        service = get_agent_runtime_service()
        status = await service.get_agent_status(business_unit_id, agent_name)
        
        return StatusResponse(
            execution_id=status.get("execution_id"),
            status=status.get("status", "unknown"),
            current_step=status.get("current_step"),
            started_at=status.get("loaded_at"),
            completed_at=status.get("last_execution_at"),
        )
    except Exception as e:
        logger.exception(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {e}")


@router.post("/{business_unit_id}/agents/{agent_name}/cancel", response_model=CancelResponse)
async def cancel_agent(business_unit_id: str, agent_name: str):
    """取消 Agent 执行"""
    logger.info(f"取消 Agent 执行: {business_unit_id}/{agent_name}")
    
    try:
        service = get_agent_runtime_service()
        success = await service.cancel_agent(business_unit_id, agent_name)
        
        return CancelResponse(
            message="取消请求已发送" if success else "没有正在执行的任务",
            success=success,
        )
    except Exception as e:
        logger.exception(f"取消执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消执行失败: {e}")


@router.delete("/{business_unit_id}/agents/{agent_name}/unload", response_model=UnloadResponse)
async def unload_agent(business_unit_id: str, agent_name: str):
    """卸载 Agent"""
    logger.info(f"卸载 Agent: {business_unit_id}/{agent_name}")
    
    try:
        service = get_agent_runtime_service()
        success = await service.unload_agent(business_unit_id, agent_name)
        
        return UnloadResponse(
            message="Agent 已卸载" if success else "Agent 未加载",
            success=success,
        )
    except Exception as e:
        logger.exception(f"卸载 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=f"卸载 Agent 失败: {e}")


@router.get("/agents/loaded")
async def list_loaded_agents():
    """列出已加载的 Agent"""
    try:
        service = get_agent_runtime_service()
        agents = service.list_loaded_agents()
        return agents
    except Exception as e:
        logger.exception(f"获取列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {e}")
