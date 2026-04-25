"""集成测试脚本 - 测试 OpenAI Agents Engine 的构建与执行流程。"""

import asyncio
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# 配置 DEBUG 日志，输出到控制台
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from backend.agent_engine.engine.openai_agents_engine import get_openai_agents_engine


async def main():
    engine = get_openai_agents_engine()
    logger.debug("引擎实例已获取: %s", engine)

    # 构建 Agent Runtime
    agent_path = "/Users/loganhu/.localbrisk/App_Data/Catalogs/myunit/agents/Data_analyst"
    business_unit_id = "demo_unit"
    logger.debug("开始构建 Agent Runtime: agent_path=%s, business_unit_id=%s", agent_path, business_unit_id)

    runtime = await engine.build_agent(
        agent_path=agent_path,
        business_unit_id=business_unit_id,
    )
    logger.debug(
        "Agent Runtime 构建完成: agent=%s, model=%s, provider=%s, tools=%d, handoffs=%d",
        runtime.context.agent_name,
        getattr(runtime, "model_id", "N/A"),
        getattr(runtime, "provider", "N/A"),
        len(runtime.sdk_tools),
        len(runtime.handoffs),
    )

    try:
        # ========== 测试非流式执行 ==========
        logger.debug("=" * 60)
        logger.debug("开始非流式执行: input='本地有哪些关于统一语义层的文档'")
        result = await runtime.run("本地有哪些关于统一语义层的文档")
        final_output = getattr(result, "final_output", result)
        logger.debug("非流式执行完成, final_output 类型: %s", type(final_output).__name__)
        print("\n===== 非流式执行结果 =====")
        print(final_output)

        # ========== 测试流式执行 ==========
        logger.debug("=" * 60)
        logger.debug("开始流式执行: input='Please analyze this file'")
        stream_result = await runtime.run_streamed("Please analyze this file")
        logger.debug("stream_result 类型: %s", type(stream_result).__name__)

        print("\n===== 流式执行事件 =====")
        event_count = 0
        async for event in stream_result.stream_events():
            event_count += 1
            event_type = getattr(event, "type", "unknown")
            logger.debug("收到流式事件 #%d: type=%s", event_count, event_type)
            print(f"[事件 #{event_count}] type={event_type}, data={event}")

        stream_final_output = getattr(stream_result, "final_output", None)
        logger.debug("流式执行完成, 共收到 %d 个事件", event_count)
        print(f"\n===== 流式执行最终输出 =====")
        print(stream_final_output)

    except Exception as exc:
        logger.error("执行过程中发生异常: %s", exc, exc_info=True)
        raise
    finally:
        # 清理资源
        logger.debug("开始清理资源...")
        runtime.close()
        await engine.close_agent_resources(runtime)
        logger.debug("资源清理完成")


if __name__ == "__main__":
    asyncio.run(main())