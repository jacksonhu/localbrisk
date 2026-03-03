"""
Model 运行时 API
提供 Model 加载、执行、状态查询等运行时管理接口

用于直接与 LLM 模型交互，不涉及 Agent 逻辑
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from agent_engine.llm.services.model_executor import ModelExecutorService, get_model_executor_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求/响应模型 ====================

class ModelExecuteRequest(BaseModel):
    """执行 Model 请求"""
    input: str = Field(..., description="用户输入")
    context: Optional[Dict[str, Any]] = Field(default=None, description="执行上下文")
    temperature: Optional[float] = Field(default=None, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大生成长度")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")


class ModelExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: str
    model_name: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None


class ModelStatusResponse(BaseModel):
    """状态响应"""
    execution_id: Optional[str] = None
    status: str
    model_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ==================== API 端点 ====================

@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/load")
async def load_model(business_unit_id: str, agent_name: str, model_name: str):
    """加载 Model
    
    从配置文件加载 Model 并初始化运行时
    """
    logger.info(f"加载 Model: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        # 从文件系统加载配置
        from app.services import business_unit_service
        
        model = business_unit_service.get_model(business_unit_id, agent_name, model_name)
        if not model:
            logger.warning(f"Model 不存在: {business_unit_id}/{agent_name}/{model_name}")
            raise HTTPException(status_code=404, detail="Model not found")
        
        # 加载 Model
        await executor.load_model(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            model_config=model
        )
        
        logger.info(f"Model 加载成功: {business_unit_id}/{agent_name}/{model_name}")
        return {
            "message": "Model loaded successfully",
            "model_name": model_name,
            "business_unit_id": business_unit_id,
            "agent_name": agent_name,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加载 Model 失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute", response_model=ModelExecutionResponse)
async def execute_model(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest
):
    """执行 Model
    
    同步执行 Model 并返回结果
    """
    logger.info(f"执行 Model: {business_unit_id}/{agent_name}/{model_name}, input_length={len(request.input)}")
    try:
        executor = get_model_executor_service()
        
        result = await executor.execute(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            input_text=request.input,
            context=request.context,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt
        )
        
        logger.info(f"Model 执行完成: {model_name}, execution_id={result.execution_id}, status={result.status}")
        return ModelExecutionResponse(
            execution_id=result.execution_id,
            model_name=result.model_name,
            status=result.status,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            usage=result.usage,
        )
        
    except Exception as e:
        logger.error(f"执行 Model 失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute/stream")
async def execute_model_streaming(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest
):
    """流式执行 Model
    
    流式执行 Model，实时返回生成内容
    """
    logger.info(f"流式执行 Model: {business_unit_id}/{agent_name}/{model_name}, input_length={len(request.input)}")
    
    async def event_generator():
        event_count = 0
        try:
            executor = get_model_executor_service()
            
            async for event in executor.execute_streaming(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                model_name=model_name,
                input_text=request.input,
                context=request.context,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                system_prompt=request.system_prompt
            ):
                event_count += 1
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            logger.info(f"流式执行完成: {model_name}, event_count={event_count}")
            yield "data: {\"event_type\": \"done\"}\n\n"
            
        except Exception as e:
            logger.error(f"流式执行失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
            yield f"data: {{\"event_type\": \"error\", \"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Transfer-Encoding": "chunked",
        }
    )


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}/status", response_model=ModelStatusResponse)
async def get_model_status(business_unit_id: str, agent_name: str, model_name: str):
    """获取 Model 执行状态"""
    logger.debug(f"获取 Model 状态: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        status = await executor.get_status(business_unit_id, agent_name, model_name)
        if not status:
            return ModelStatusResponse(status="not_loaded")
        
        return ModelStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"获取状态失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/cancel")
async def cancel_model(business_unit_id: str, agent_name: str, model_name: str):
    """取消 Model 执行"""
    logger.info(f"取消 Model 执行: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        success = await executor.cancel(business_unit_id, agent_name, model_name)
        
        if success:
            logger.info(f"Model 执行已取消: {model_name}")
        else:
            logger.debug(f"没有运行中的执行: {model_name}")
        
        return {
            "message": "Cancelled" if success else "No running execution",
            "success": success,
        }
        
    except Exception as e:
        logger.error(f"取消执行失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}/unload")
async def unload_model(business_unit_id: str, agent_name: str, model_name: str):
    """卸载 Model
    
    清理 Model 运行时资源
    """
    logger.info(f"卸载 Model: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        success = await executor.cleanup_model(business_unit_id, agent_name, model_name)
        
        if success:
            logger.info(f"Model 卸载成功: {model_name}")
        else:
            logger.warning(f"Model 未找到: {model_name}")
        
        return {
            "message": "Unloaded" if success else "Model not found",
            "success": success,
        }
        
    except Exception as e:
        logger.error(f"卸载 Model 失败: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/loaded")
async def list_loaded_models():
    """列出已加载的 Model"""
    logger.debug("获取已加载 Model 列表")
    try:
        executor = get_model_executor_service()
        models = executor.list_loaded_models()
        logger.debug(f"已加载 {len(models)} 个 Model")
        return models
        
    except Exception as e:
        logger.error(f"获取列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
