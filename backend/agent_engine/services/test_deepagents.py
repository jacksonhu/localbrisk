import sys
import os

# 将 backend 目录添加到 Python 模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_engine.services import get_agent_runtime_service

# 配置日志级别为 INFO，确保 info 级别日志能输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# 设置httpx日志以捕获HTTP请求
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.INFO)

# 设置OpenAI相关日志
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("langchain").setLevel(logging.DEBUG)
logging.getLogger("langchain_openai").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def load_agent() -> Any:
    try:
        service = get_agent_runtime_service()
        state = service.load_agent("myunit", "Data_analyst")

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Agent 配置不存在: {e}")
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"缺少依赖: {e}")
    except Exception as e:
        logger.exception(f"加载 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载 Agent 失败: {e}")


async def execute_agent_streaming(
        business_unit_id: str,
        agent_name: str,
        input: str,
):
    """流式执行 Agent，输出 SSE 格式事件"""
    try:
        service = get_agent_runtime_service()

        async for event in service.execute_agent_stream(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                user_input=input,
        ):
            # 输出完整 SSE 格式
            print(event.to_sse())
    except Exception as e:
        logger.exception(f"流式执行失败: {e}")
        print(f"ERROR: {e}")


async def debug_raw_stream(
        business_unit_id: str,
        agent_name: str,
        input_text: str,
):
    """调试：直接查看 LangGraph 原始流式输出"""
    service = get_agent_runtime_service()
    state = await service.load_agent(business_unit_id, agent_name)
    agent = state.agent_instance
    import uuid
    execution_id = str(uuid.uuid4())
    input_data = {"messages": [{"role": "user", "content": input_text}]}
    config = {"configurable": {"thread_id": execution_id}}

    print("=== RAW STREAM OUTPUT ===")
    async for chunk in agent.astream(input_data, config=config, stream_mode="messages"):
        if isinstance(chunk, tuple) and len(chunk) == 2:
            msg, meta = chunk
            print(f"\n--- chunk type={type(msg).__name__} ---")
            print(f"  type attr: {getattr(msg, 'type', 'N/A')}")
            print(f"  content: {repr(getattr(msg, 'content', 'N/A'))}")
            
            # tool_calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"  tool_calls: {msg.tool_calls}")
            
            # tool_call_chunks (AIMessageChunk specific)
            if hasattr(msg, 'tool_call_chunks') and msg.tool_call_chunks:
                print(f"  tool_call_chunks: {msg.tool_call_chunks}")
            
            # additional_kwargs
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                print(f"  additional_kwargs: {msg.additional_kwargs}")
            
            # ToolMessage specific
            if getattr(msg, 'type', '') == 'tool':
                print(f"  tool_call_id: {getattr(msg, 'tool_call_id', 'N/A')}")
                print(f"  name: {getattr(msg, 'name', 'N/A')}")
            
            print(f"  metadata: {meta}")
        else:
            print(f"\n--- non-tuple chunk: {type(chunk)} ---")
            print(f"  {chunk}")


if __name__ == '__main__':
    logger.info("Starting test")
    import asyncio
    #asyncio.run(execute_agent_streaming("myunit", "Data_analyst", "分析一下腾讯股价？"))
    asyncio.run(execute_agent_streaming("myunit", "Data_analyst", "帮我总结一下让DataAgent更可信的统一语义层.pdf的内容"))
    #asyncio.run(execute_agent_streaming("myunit", "Data_analyst","https://docs.wechatpy.org/zh-cn/master/quickstart.html,帮我总结一下这个网页的内容"))
    #asyncio.run(execute_agent_streaming("myunit", "Data_analyst", "你好"))
    #asyncio.run(debug_raw_stream("myunit", "Data_analyst", "你好"))
