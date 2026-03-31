"""
Model Runtime API
Provides runtime management endpoints for Model loading, execution, status query

For direct LLM model interaction without Agent logic
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


# ==================== Request/Response Models ====================

class ModelExecuteRequest(BaseModel):
    """Execute  Model request"""
    input: str = Field(..., description="User input")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Execution context")
    temperature: Optional[float] = Field(default=None, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, description="Max generation length")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")


class ModelExecutionResponse(BaseModel):
    """Execute response"""
    execution_id: str
    model_name: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None


class ModelStatusResponse(BaseModel):
    """Status response"""
    execution_id: Optional[str] = None
    status: str
    model_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ==================== API Endpoints ====================

@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/load")
async def load_model(business_unit_id: str, agent_name: str, model_name: str):
    """Load Model
    
    从配置文件Load Model 并初始化运行时
    """
    logger.info(f"Loading  Model: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        # 从文件系统Load配置
        from app.services import business_unit_service
        
        model = business_unit_service.get_model(business_unit_id, agent_name, model_name)
        if not model:
            logger.warning(f"Model  does not exist: {business_unit_id}/{agent_name}/{model_name}")
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Load Model
        await executor.load_model(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            model_config=model
        )
        
        logger.info(f"Model Load成功: {business_unit_id}/{agent_name}/{model_name}")
        return {
            "message": "Model loaded successfully",
            "model_name": model_name,
            "business_unit_id": business_unit_id,
            "agent_name": agent_name,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load  Model failed: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute", response_model=ModelExecutionResponse)
async def execute_model(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest
):
    """Execute  Model
    
    SyncExecute Model 并返回结果
    """
    logger.info(f"Executing  Model: {business_unit_id}/{agent_name}/{model_name}, input_length={len(request.input)}")
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
        
        logger.info(f"Model Execute完成: {model_name}, execution_id={result.execution_id}, status={result.status}")
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
        logger.error(f"Execute Model failed: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute/stream")
async def execute_model_streaming(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest
):
    """Stream execution of Model
    
    streaming execution Model, 实时返回生成内容
    """
    logger.info(f"Streaming execution of  Model: {business_unit_id}/{agent_name}/{model_name}, input_length={len(request.input)}")
    
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
            
            logger.info(f"Streaming execution of 完成: {model_name}, event_count={event_count}")
            yield "data: {\"event_type\": \"done\"}\n\n"
            
        except Exception as e:
            logger.error(f"流式Execution failed: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
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
    """Get Model Execute状态"""
    logger.debug(f"Fetching  Model 状态: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        status = await executor.get_status(business_unit_id, agent_name, model_name)
        if not status:
            return ModelStatusResponse(status="not_loaded")
        
        return ModelStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get 状态failed: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/cancel")
async def cancel_model(business_unit_id: str, agent_name: str, model_name: str):
    """Cancel  Model Execute"""
    logger.info(f"Cancelling  Model Execute: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        success = await executor.cancel(business_unit_id, agent_name, model_name)
        
        if success:
            logger.info(f"Model Executecancelled: {model_name}")
        else:
            logger.debug(f"没有运行中的Execute: {model_name}")
        
        return {
            "message": "Cancelled" if success else "No running execution",
            "success": success,
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel execution: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}/unload")
async def unload_model(business_unit_id: str, agent_name: str, model_name: str):
    """Unload  Model
    
    清理 Model 运行时资源
    """
    logger.info(f"Unloading  Model: {business_unit_id}/{agent_name}/{model_name}")
    try:
        executor = get_model_executor_service()
        
        success = await executor.cleanup_model(business_unit_id, agent_name, model_name)
        
        if success:
            logger.info(f"Model 卸载成功: {model_name}")
        else:
            logger.warning(f"Model not found: {model_name}")
        
        return {
            "message": "Unloaded" if success else "Model not found",
            "success": success,
        }
        
    except Exception as e:
        logger.error(f"卸载 Model failed: {business_unit_id}/{agent_name}/{model_name} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/loaded")
async def list_loaded_models():
    """列出已Load的 Model"""
    logger.debug("Get已Load Model 列表")
    try:
        executor = get_model_executor_service()
        models = executor.list_loaded_models()
        logger.debug(f"已Load {len(models)}  Model(s)")
        return models
        
    except Exception as e:
        logger.error(f"Failed to get 列表failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
