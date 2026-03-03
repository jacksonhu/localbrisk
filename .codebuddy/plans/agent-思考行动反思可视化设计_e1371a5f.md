---
name: agent-思考行动反思可视化设计
overview: 设计一套可落地的 Agent 提示词与执行协议，使复杂任务中可流式展示思考过程、每一步 Action 及其动机（why），并与现有后端流协议和前端渲染契合。
todos:
  - id: trace-call-chain
    content: 使用 [subagent:code-explorer] 复核协议与渲染调用点
    status: completed
  - id: revise-agent-prompt
    content: 重写 AGENTS.md 思考动作原因反思约束
    status: completed
    dependencies:
      - trace-call-chain
  - id: extend-protocol-schema
    content: 扩展 stream_protocol.py 与 response_schema.py 可解释字段
    status: completed
    dependencies:
      - revise-agent-prompt
  - id: update-runtime-translator
    content: 改造 agent_runtime_service.py 输出原因与反思流事件
    status: completed
    dependencies:
      - extend-protocol-schema
  - id: adapt-frontend-render
    content: 更新 stream-protocol.ts 与 AgentChatPanel.vue 展示新字段
    status: completed
    dependencies:
      - update-runtime-translator
  - id: add-regression-tests
    content: 补充 test_agent_runtime_service.py 并验证SSE链路
    status: completed
    dependencies:
      - update-runtime-translator
---

## User Requirements

用户希望在复杂任务执行时，能像 CodeBuddy 一样清晰看到：

- 思考过程
- 每一步执行动作
- 执行动作的原因（为什么这么做）
- 执行后的反思与修正

并要求基于现有 Agent 体系，重点设计可落地的提示词与执行范式，而不是只给概念描述。

## Product Overview

在现有对话执行链路中，增加“过程可解释”能力：执行中持续展示思考与动作，执行后可回看反思；最终输出仍保持结构化结果，兼顾可读性与可追踪性。

视觉上应体现为：对话区可分段看到“思考/动作/反思”，动作卡片中直接显示“原因说明”，整体时间顺序清晰、可快速回放。

## Core Features

- 明确“思考→动作→反思”三段式执行协议，并固化到系统提示词
- 流式消息中为动作补充“原因/预期”信息，支持前端实时展示
- 最终结构化响应中保留关键思考与反思块，支持执行复盘
- 保持任务清单、工具调用、最终总结的一致语义与顺序
- 异常与截断情况下提供降级展示，避免过程信息丢失

## Tech Stack Selection

- 后端沿用现有 Python + FastAPI + Pydantic + LangGraph/DeepAgents 链路
- 前端沿用 Vue3 + TypeScript 的 StreamMessage 协议消费模式
- 不新增独立协议通道，直接扩展现有 `THOUGHT/TOOL_CALL` 负载字段，降低改造面

## Implementation Approach

采用“提示词约束 + 协议扩展 + 运行时翻译 + 前端渲染”四层方案：
先在 `AGENTS.md` 强化可解释行为规范，再在流式协议与结构化 schema 中新增可解释字段（可选字段，向后兼容），最后由 `agent_runtime_service` 在流式过程中把“动作原因/反思阶段”稳定映射给前端展示。

关键决策：

- **不新增消息类型**，优先扩展 `ToolCallPayload/ThoughtPayload` 可选字段，避免前端分发器和历史逻辑大改
- **原因与反思分层**：动作原因走 `TOOL_CALL`，阶段反思走 `THOUGHT`/`ThinkingBlock`，语义清晰
- **失败可降级**：字段缺失时前端回退原展示，不阻塞主链路

性能与可靠性：

- 流式处理保持单次线性扫描，复杂度 O(n)（n 为消息块数）
- 仅新增轻量字段拼装，不引入额外网络往返
- 控制日志粒度，避免长文本重复写入造成 I/O 放大

## Implementation Notes

- 复用 `StreamMessageBuilder`，仅添加可选参数，避免破坏既有调用
- `MessageTranslator` 中新增“原因提取/传递”逻辑时，避免对 tool_result 做大文本全量复制
- `_emit_final_output` 继续遵循“纯文本替换 thought、非文本转 artifact”策略，避免前端渲染分叉
- 前端仅在字段存在时显示“为什么做”，缺失则不渲染，控制变更爆炸半径

## Architecture Design

- **提示词层**：定义强约束执行语法（思考、动作原因、反思）
- **协议层**：扩展 `stream_protocol` 与 `response_schema` 字段承载
- **翻译层**：`agent_runtime_service` 将 LangGraph 事件映射为统一流式消息
- **展示层**：`AgentWorkspace -> AgentChatPanel` 消费扩展字段并分区展示

## Directory Structure Summary

本次改造围绕既有 Agent 流式链路，最小化扩展协议字段与渲染能力，不引入新模块。

- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/engine/AGENTS.md`  # [MODIFY] 行为主提示模板。补充“动作前必须说明原因、动作后反思”的强约束与输出示例。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/core/stream_protocol.py`  # [MODIFY] 流式协议定义。为 THOUGHT/TOOL_CALL 增加可选可解释字段与 Builder 参数。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/core/response_schema.py`  # [MODIFY] 最终结构化响应 schema。补充反思/动机相关字段，保持可选兼容。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/services/agent_runtime_service.py`  # [MODIFY] 流事件翻译与聚合。将原因、阶段、反思映射到协议消息并维持降级策略。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/frontend/src/types/stream-protocol.ts`  # [MODIFY] 前端协议类型同步，新增可解释字段类型声明。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/frontend/src/components/detail/AgentChatPanel.vue`  # [MODIFY] 对话执行块 UI。展示动作原因与反思标识，保持原任务/工具展示逻辑。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/tests/agent_engine/test_agent_runtime_service.py`  # [MODIFY] 单测补充。覆盖字段映射、降级路径与消息输出语义。

## Agent Extensions

- **code-explorer**
- Purpose: 在实现前后快速核对跨文件调用链与协议消费点，避免遗漏前后端联动改动。
- Expected outcome: 产出完整、可执行的改动清单，并确认字段变更在发送端与消费端均已闭环。