---
name: agent-task-tools-and-runtime-taskdir
overview: 在 `agent_engine/tools` 增加可持久化任务管理工具（供 deep agent 调用），并在 `AgentRuntimeService` 加载阶段初始化 `output/.task` 目录。
todos:
  - id: scope-check
    content: 使用 [subagent:code-explorer] 核对工具注册链与影响文件
    status: completed
  - id: build-task-core
    content: 新增 task_board 与 task_tools，实现任务管理闭环
    status: completed
    dependencies:
      - scope-check
  - id: wire-builtin-tools
    content: 修改 tools/__init__.py 注册任务工具并注入 backend
    status: completed
    dependencies:
      - build-task-core
  - id: init-task-dir
    content: 在 load_agent 初始化 output/.task 并完善异常处理
    status: completed
    dependencies:
      - wire-builtin-tools
  - id: add-tests
    content: 补充运行时与任务工具单测并完成回归验证
    status: completed
    dependencies:
      - init-task-dir
---

## User Requirements

- 在 `backend/agent_engine/tools` 下新增“agent task 管理相关工具”，形成可直接被 Agent 调用的任务管理能力。
- 在 `backend/agent_engine/services/agent_runtime_service.py` 的 Agent 初始化流程中，确保任务状态存储目录 `output/.task` 自动创建。
- 参考你提供的任务板实现思路，但保持当前项目风格，代码简洁，不引入无关历史兼容逻辑。

## Product Overview

- Agent 运行时将具备独立任务状态目录，任务数据可落盘保存，重启后仍可读取。
- Agent 可通过任务工具完成任务创建、查询、更新、列出、认领等闭环操作。
- 界面层不新增页面；效果体现在现有对话/执行流程中能稳定读取和维护任务状态。

## Core Features

- 任务目录初始化：Agent 加载完成时自动准备 `output/.task`。
- 任务持久化管理：基于文件存储的任务增删改查与状态流转。
- 工具统一注入：任务工具与现有内置工具一起自动注册给 Agent。
- 可靠性保障：非法输入兜底、并发写入保护、异常可定位。

## Tech Stack Selection

- 复用现有后端栈：Python 服务层 + 现有 Agent 引擎工具体系。
- 工具实现沿用现有 `BaseTool + Pydantic args_schema` 约定（与 `office_reader` 一致）。
- 任务状态存储采用本地 JSON 文件，目录固定在 Agent `output/.task`。

## Implementation Approach

- 方法：新增“任务板核心模块 + 工具封装模块”，并通过 `get_builtin_tools(backend)` 自动注入；在 `load_agent()` 完成时初始化目录。
- 工作方式：工具调用统一读写 `.task` 下任务文件；运行时启动时先确保目录存在，再暴露工具能力给 Agent。
- 关键决策：
- **复用现有工具注册链路**，不改 DeepAgent 主流程，降低改动面。
- **文件持久化优先**，满足本地 Agent 场景，避免额外服务依赖。
- **保持路径收敛到 output**，避免跨目录写入风险。
- 性能与可靠性：
- 单次任务查询/更新复杂度 `O(1)`（按任务 ID 文件命中）或 `O(n)`（任务列表扫描）。
- 列表接口仅扫描 `.task` 目录，避免全仓遍历。
- 通过原子写（临时文件后替换）与输入校验减少损坏与异常扩散。

## Implementation Notes (Execution Details)

- 严格复用现有路径解析与工具注入模式，不新增并行框架。
- 任务字段做白名单校验（状态枚举、标题长度、ID 格式），拒绝非法写入。
- 文件操作需限制在 `output/.task`，禁止 `..` 路径穿越。
- 日志仅记录任务 ID/状态与错误摘要，不输出敏感上下文。
- 保持向后兼容最小化：仅新增能力，不重构无关流式协议逻辑。

## Architecture Design

- `AgentRuntimeService.load_agent()`：负责任务目录引导初始化。
- `task_board`：负责任务模型、持久化读写、状态流转规则。
- `task_tools`：将任务板能力暴露为 Agent 工具接口。
- `tools/__init__.py`：统一注册内置工具（Office + Task）。

## Directory Structure

## Directory Structure Summary

本次改动围绕“任务工具新增 + 运行时目录初始化 + 测试补齐”展开，尽量复用现有 Agent 工具装配方式。

- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/tools/task_board.py`  # [NEW] 任务板核心。定义任务数据结构、JSON 持久化、创建/查询/更新/列表/认领方法；要求原子写入与路径安全校验。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/tools/task_tools.py`  # [NEW] 任务工具封装。将任务板能力封装为可注册工具，参数与返回文本保持对 Agent 友好。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/tools/__init__.py`  # [MODIFY] 内置工具聚合入口。导出任务工具工厂并在 `get_builtin_tools` 中注册，保持 backend 注入风格一致。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/agent_engine/services/agent_runtime_service.py`  # [MODIFY] Agent 加载流程中初始化 `output/.task`，失败时给出明确错误日志并中断加载。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/tests/agent_engine/test_agent_runtime_service.py`  # [MODIFY] 增加 `load_agent` 后 `.task` 目录存在性断言。
- `/Users/loganhu/Documents/eclipse_workspace/LocalBrisk/backend/tests/agent_engine/test_task_tools.py`  # [NEW] 覆盖任务工具与任务板核心场景：创建、更新、认领、列表、异常输入与并发写入安全。

## Agent Extensions

- **code-explorer**（SubAgent）
- Purpose: 在实现前后快速核对多文件调用链、工具注册点和测试覆盖范围。
- Expected outcome: 明确受影响文件与回归边界，避免遗漏注册或断链。