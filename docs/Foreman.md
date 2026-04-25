# Foreman 产品方案设计

> Status: proposal / 产品设计草案
>
> 本文面向 `Foreman` 对话能力的产品设计与后端落地方案，目标是在现有单 Agent 对话能力基础上，扩展出支持 **单聊**、**多 Agent 群聊**、以及 **后台 coordinator agent 自动编排** 的统一聊天体验。

---

## 1. 背景与目标

`Foreman` 的目标不是简单把多个 Agent 放进一个聊天窗口，而是让用户在同一个对话入口中，既可以：

- 直接与 **单个 Agent** 对话
- 创建 **Agent 群聊** 与多个 Agent 协同对话
- 在群聊中由 **后台 coordinator agent** 自动判断应该由谁来回答
- 在必要时自动纠正错误回答、重新分发任务、追加其他 Agent 的回复
- 在用户明确 `@某个 Agent` 时，优先满足用户的显式指令

也就是说，`Foreman` 要解决的问题是：

1. **统一入口**：用户不需要先决定“该找哪个 Agent”，而是可以先提问。
2. **智能分发**：系统自动把问题交给最合适的 Agent。
3. **多 Agent 协作**：复杂问题可以由多个 Agent 先后或并行参与。
4. **对话可控**：用户仍可通过 `@Agent` 直接指定回复对象。
5. **结果可纠偏**：当某个 Agent 回答错误、不完整或偏题时，coordinator 可以主动介入。

---

## 2. 产品范围

### 2.1 本期纳入范围

- `Foreman` 对话页支持两种模式：
  - 单 Agent 对话
  - 多 Agent 群聊
- 群聊支持从已有单聊升级而来
- 群聊内启用后台 `coordinator agent`
- 支持用户通过 `@Agent` 点名某个 Agent 回复
- 支持 coordinator 对错误答案进行自动纠偏与二次调度
- 支持统一的会话历史、成员管理、消息流式展示

### 2.2 本期不纳入范围

- 让多个 Agent 共享完全相同的原生运行时上下文
- 复杂权限系统（如 Agent 可见范围差异化）
- 超细粒度的 coordinator 可视化策略编排 UI
- 人工审核式工作流编排器
- 跨业务单元的混合群聊

---

## 3. 核心角色定义

### 3.1 用户

发起问题、创建群聊、添加成员、`@Agent` 定向提问、查看回复结果。

### 3.2 普通 Agent

群聊中的业务执行成员。每个 Agent 仍保有自己的能力边界、上下文线程、执行历史。

### 3.3 Coordinator Agent

群聊模式下的后台编排角色，不作为普通聊天成员直接参与“日常抢答”，而是承担以下职责：

- 识别当前用户问题适合由哪个 Agent 回答
- 决定是单 Agent 回复还是多 Agent 协作回复
- 在发现错误、遗漏、冲突时，触发纠偏
- 在用户没有明确 `@` 的情况下，负责默认路由
- 在用户明确 `@` 某个 Agent 时，调整调度策略并做兜底校验

### 3.4 显示原则

- 普通 Agent：作为群成员显示在右侧成员区
- Coordinator：**默认不作为普通群成员展示**，而是以“自动协调已开启”的系统能力存在
- 如果后续需要增强可解释性，可在消息流中展示简洁的系统状态，例如：
  - `Coordinator assigned the task to ResearchAgent`
  - `Coordinator requested a correction from PlannerAgent`

注意：这里的可视化信息应是 **调度结论**，不是 coordinator 的完整内部推理过程。

---

## 4. 用户场景

### 4.1 单 Agent 对话

用户在 `Foreman` 或 Agent 对话界面选择一个 Agent 后，直接发起问题。

预期表现：

- 会话类型为单聊
- 用户消息仅路由给当前 Agent
- 不启用 coordinator 自动调度
- 回复链路与现有单 Agent runtime 基本一致

适用场景：

- 明确知道该问哪个 Agent
- 任务简单，不需要多 Agent 协作
- 用户希望控制对话对象，减少干扰

### 4.2 创建 Agent 群聊

用户可以：

- 直接新建一个多 Agent 群聊
- 在已有单聊中添加更多 Agent，使单聊升级为群聊

预期表现：

- 会话升级后保留原会话 `conversation_id`
- 原有单聊历史保留
- 新成员被加入群成员列表
- coordinator 自动启用

### 4.3 群聊模式下默认提问

用户在群聊中直接输入消息，但没有 `@` 任一成员。

预期表现：

- coordinator 先读取当前消息、最近会话历史、群成员能力画像
- coordinator 选择一个或多个 Agent 来执行
- 只有被选中的 Agent 参与本轮回复
- 如果首轮回复质量不达标，coordinator 可自动触发补充回复或纠偏

### 4.4 群聊模式下 `@Agent`

用户在群聊消息中显式 `@` 某个 Agent。

预期表现：

- coordinator 将该 Agent 视为 **首选回复对象**
- 默认先让被点名 Agent 执行
- 若该 Agent 回答明显错误、缺失关键结论，coordinator 可追加其他 Agent 参与
- 最终系统行为要兼顾：
  - **优先满足用户指令**
  - **必要时保证结果正确性**

### 4.5 回答纠偏

当某个 Agent 回复后，coordinator 发现以下问题之一：

- 回答明显偏题
- 与已知上下文冲突
- 缺少关键步骤
- 任务本应由其他 Agent 处理
- 当前结果需要其他 Agent 交叉验证

则 coordinator 可以触发二次编排，例如：

- 要求原 Agent 重新回答
- 让另一名 Agent 补充说明
- 让另一名 Agent 替代回答
- 让多个 Agent 分工后汇总

---

## 5. 产品目标与原则

### 5.1 目标

- 让用户在一个会话里完成“提问—分发—协作—纠偏—收敛”全过程
- 降低用户选择 Agent 的成本
- 提高复杂问题的一次性解决率
- 保持前端体验简单，避免把编排复杂度暴露给用户

### 5.2 原则

- **简单优先**：普通用户看到的是聊天，不是工作流系统。
- **显式优先**：用户 `@Agent` 的指令优先于默认自动路由。
- **纠偏受控**：coordinator 可以纠偏，但不能无限循环调度。
- **历史统一**：群聊要有统一主时间线，而不是多个 Agent 历史拼接的错觉。
- **执行可复用**：尽量复用现有单 Agent runtime、thread 和 SSE 协议。

---

## 6. 信息架构

### 6.1 会话类型

| 类型 | 定义 | coordinator | 成员数量 |
|------|------|-------------|----------|
| Direct Chat | 用户与单个 Agent 的对话 | 关闭 | 1 |
| Group Chat | 用户与多个 Agent 的对话 | 开启 | >= 2 |

### 6.2 会话组成

每个 `Foreman` 会话由以下部分构成：

- **会话元信息**
  - `conversation_id`
  - 标题
  - 会话类型（direct / group）
  - 创建时间 / 更新时间
  - 最近一条摘要
- **成员信息**
  - 成员 Agent 列表
  - 每个成员绑定的 `business_unit_id`
  - 每个成员绑定的 `thread_id`
- **主时间线**
  - 用户消息
  - Agent 回复消息
  - 系统状态消息
  - 执行中间状态
- **编排状态**
  - coordinator 是否启用
  - 当前轮次是否为 `@指定回复`
  - 最近一次调度决策

### 6.3 群聊升级规则

当用户在单聊中增加成员时：

- 会话类型由 `direct` 升级为 `group`
- 原单聊成员继续保留原 `thread_id`
- 新增成员获得新的成员线程绑定
- 历史主时间线不拆分、不迁移、不重建
- coordinator 自此启用

---

## 7. 核心交互流程

### 7.1 单聊发送消息

1. 用户打开单 Agent 会话
2. 输入问题并发送
3. 前端调用单会话流式接口
4. 后端直接路由到目标 Agent runtime
5. Agent 输出流式返回给前端
6. 主时间线写入用户消息和 Agent 回复

特点：

- 路径短
- 响应快
- 行为与现有单 Agent 模式基本一致

### 7.2 新建群聊

1. 用户点击新建群聊
2. 选择多个 Agent
3. 系统创建群会话
4. 为每个成员生成成员绑定与独立 `thread_id`
5. 系统默认启用 coordinator
6. 前端进入群聊详情页

### 7.3 群聊默认提问

1. 用户在群聊中发送消息
2. 消息未包含 `@Agent`
3. 后端先把用户消息写入主时间线
4. coordinator 读取：
   - 当前用户问题
   - 最近历史
   - 成员能力画像
   - 最近调度状态
5. coordinator 输出调度计划：
   - 本轮由谁答
   - 是否需要多人协作
   - 回复顺序 / 并发策略
6. 后端按计划调用对应 Agent runtime
7. 各 Agent 输出被聚合并流式推送到前端
8. coordinator 对结果做轮次检查
9. 如需纠偏，则进入补充调度
10. 结果写入主时间线并结束本轮

### 7.4 群聊 `@Agent`

1. 用户输入 `@ResearchAgent 请先分析这个需求`
2. 后端识别到显式 mention
3. coordinator 将 `ResearchAgent` 设为首要执行者
4. `ResearchAgent` 先输出结果
5. coordinator 判断：
   - 是否可以直接结束
   - 是否需要其他 Agent 补充
6. 若需要，则追加下一轮任务
7. 最终将所有可见结果写回主时间线

### 7.5 自动纠偏

自动纠偏是群聊模式的核心差异点，触发条件包括但不限于：

- 被点名 Agent 明显超出能力范围
- 当前回复与历史结论冲突
- 用户问题本质上需要其他 Agent 的能力
- 首轮回复不够完整，无法交付

系统处理原则：

- 优先做 **轻量纠偏**，如补充一名 Agent
- 尽量避免连续多轮抢答，防止时间线噪声过大
- 对同一轮问题设置最大纠偏次数
- 超过阈值时结束自动纠偏，并提示用户继续明确指令

---

## 8. Coordinator Agent 设计

### 8.1 定位

`Coordinator Agent` 是群聊模式下的后台编排器，本质上是一个系统级 Agent，不直接承担最终业务回答，而负责：

- 路由
- 纠偏
- 协作编排
- 收敛结果

### 8.2 输入

coordinator 的输入至少包括：

- 用户当前消息
- 最近 N 轮会话历史
- 群成员列表
- 每个成员的能力画像 / 描述
- 当前消息中的 `@mention`
- 最近一次调度记录
- 已发生的错误或异常事件

### 8.3 输出

coordinator 的输出不是面向用户的自然语言正文，而是结构化编排结果，例如：

- `selected_agents`
- `dispatch_mode`（single / sequential / parallel）
- `priority_agent`
- `requires_correction`
- `correction_target`
- `finish_reason`

### 8.4 责任边界

coordinator 可以决定：

- 哪个 Agent 回答
- 是否补充其他 Agent
- 是否要求重答
- 是否提前结束本轮

coordinator 不应承担：

- 长篇业务内容的主要输出
- 直接替代业务 Agent 的专业回答
- 无限循环式的调度尝试

### 8.5 调度优先级

建议优先级如下：

1. 用户显式 `@Agent`
2. 当前消息与最近轮次的上下文连续性
3. Agent 能力匹配度
4. 历史纠偏记录
5. 默认路由策略

### 8.6 纠偏策略

建议 MVP 只支持以下三种纠偏动作：

- **retry_same_agent**：让原 Agent 基于补充提示重答
- **handoff_to_other_agent**：转交给另一名更匹配的 Agent
- **append_supporting_agent**：让第二名 Agent 做补充或校验

不建议在首版支持复杂树状工作流，否则会显著增加前后端复杂度。

### 8.7 可见性策略

为了兼顾可解释性与简洁性，建议：

- 不暴露 coordinator 的完整内部推理
- 仅暴露必要的系统状态摘要
- 例如前端可显示：
  - `Coordinator selected CodeAgent`
  - `Coordinator asked ReviewAgent to verify the answer`

---

## 9. 产品行为规则

### 9.1 单聊规则

- 单聊只允许一个业务 Agent
- 单聊不启用 coordinator
- 用户不能在单聊里 `@` 其他未加入 Agent
- 若用户尝试新增成员，则单聊升级为群聊

### 9.2 群聊规则

- 群聊成员数必须大于等于 2
- 群聊默认开启 coordinator
- 用户可以继续添加成员
- 用户可以通过 `@Agent` 点名
- 若 `@` 多个 Agent，则 coordinator 视为多目标执行请求

### 9.3 回复归属规则

- 每条业务回复都必须有明确发送者（某个 Agent）
- coordinator 的系统状态不与业务回复混淆
- 主时间线中必须区分：
  - user message
  - agent message
  - system status
  - execution event

### 9.4 失败处理规则

- 某个 Agent 执行失败时，不应直接让整个群聊崩溃
- coordinator 可以决定：
  - 重试当前 Agent
  - 跳过并交给其他 Agent
  - 终止本轮并提示用户

---

## 10. 前端体验设计

### 10.1 左侧会话区

展示所有单聊与群聊会话：

- 单聊显示 Agent 名称
- 群聊显示群名或成员摘要
- 可标识最近活跃状态

### 10.2 中间聊天区

统一展示主时间线：

- 用户消息
- Agent 回复
- 系统状态消息
- 正在输入/执行中的状态

群聊模式下需要支持：

- 区分不同 Agent 的身份标签
- 展示当前被调度中的 Agent
- 展示可选的系统调度状态摘要

### 10.3 右侧成员区

展示当前群成员：

- Agent 名称
- 简短能力描述
- 当前在线/执行状态（如需要）

不建议把 coordinator 混入普通成员列表，否则用户会误以为它是一个可直接对话的业务 Agent。

### 10.4 输入区

支持：

- 普通发送
- `@Agent` 提示与自动补全
- 发送中状态
- 群聊模式下显示“自动协调已开启”轻提示

---

## 11. 后端落地方案

### 11.1 总体思路

最稳妥的实现方式不是重写现有单 Agent runtime，而是在其上新增一层 `Foreman` 编排层：

```text
Frontend Foreman UI
    -> Foreman Runtime API
        -> ForemanRuntimeService
            -> Coordinator decision layer
            -> AgentRuntimeService (existing)
            -> ForemanSessionStore
```

即：

- **`AgentRuntimeService`** 继续负责单 Agent 执行
- **`ForemanRuntimeService`** 负责多 Agent 会话与统一编排
- **`ForemanSessionStore`** 负责会话、成员、主时间线持久化
- **Coordinator layer** 负责群聊调度与纠偏

### 11.2 为什么不直接改造单 Agent runtime

因为当前单 Agent runtime 的核心假设是：

- 一个请求对应一个 Agent
- 上下文以 `thread_id` 绑定到该 Agent
- 历史按 Agent 维度持久化

而 `Foreman` 群聊需要的是：

- 一个会话包含多个 Agent 成员
- 每个成员有独立线程
- 用户看到的是统一主时间线
- 需要 coordinator 做跨成员调度

因此更适合新增一层编排服务，而不是破坏现有 runtime 的边界。

### 11.3 推荐模块划分

建议新增：

- `app/api/endpoints/foreman_runtime.py`
- `agent_engine/services/foreman_runtime_service.py`
- `agent_engine/services/foreman_session_store.py`
- `agent_engine/services/foreman_coordinator_service.py`

职责说明：

- `foreman_runtime.py`
  - 提供会话、成员、历史、流式执行接口
- `ForemanRuntimeService`
  - 聚合业务流程，负责一次完整聊天轮次
- `ForemanSessionStore`
  - 持久化主会话信息、成员绑定、主时间线
- `ForemanCoordinatorService`
  - 调用 coordinator agent 或规则层，输出结构化调度结果

---

## 12. 数据模型建议

### 12.1 Conversation

| 字段 | 说明 |
|------|------|
| `conversation_id` | 会话 ID |
| `conversation_type` | `direct` / `group` |
| `title` | 会话标题 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |
| `coordinator_enabled` | 是否启用 coordinator |
| `last_message_preview` | 最近消息摘要 |

### 12.2 ConversationMember

| 字段 | 说明 |
|------|------|
| `member_id` | 成员 ID |
| `conversation_id` | 所属会话 |
| `business_unit_id` | 业务单元 |
| `agent_name` | Agent 名称 |
| `thread_id` | 该成员在线程中的上下文 ID |
| `joined_at` | 加入时间 |
| `is_active` | 是否有效 |

### 12.3 ConversationMessage

| 字段 | 说明 |
|------|------|
| `message_id` | 消息 ID |
| `conversation_id` | 所属会话 |
| `role` | `user` / `agent` / `system` |
| `sender_id` | 发送者 ID |
| `sender_name` | 发送者名称 |
| `content` | 文本内容 |
| `mentioned_agents` | 被点名成员 |
| `created_at` | 创建时间 |
| `round_id` | 所属轮次 |

### 12.4 ExecutionRound

| 字段 | 说明 |
|------|------|
| `round_id` | 本轮执行 ID |
| `conversation_id` | 所属会话 |
| `user_message_id` | 触发本轮的用户消息 |
| `dispatch_mode` | 单人 / 串行 / 并行 |
| `selected_agents` | 本轮入选 Agent |
| `correction_count` | 已纠偏次数 |
| `status` | running / completed / failed |
| `finished_at` | 结束时间 |

### 12.5 CoordinatorDecision

| 字段 | 说明 |
|------|------|
| `decision_id` | 决策 ID |
| `round_id` | 所属轮次 |
| `decision_type` | route / retry / handoff / append |
| `target_agents` | 目标 Agent |
| `reason_summary` | 简短理由摘要 |
| `created_at` | 创建时间 |

---

## 13. API 设计建议

### 13.1 会话管理

- `POST /api/foreman/conversations`
  - 创建单聊或群聊
- `GET /api/foreman/conversations`
  - 获取会话列表
- `GET /api/foreman/conversations/{conversation_id}`
  - 获取会话详情
- `DELETE /api/foreman/conversations/{conversation_id}`
  - 删除会话

### 13.2 成员管理

- `POST /api/foreman/conversations/{conversation_id}/members`
  - 向会话添加成员
  - 若当前是单聊，则升级为群聊
- `DELETE /api/foreman/conversations/{conversation_id}/members/{member_id}`
  - 移除成员

### 13.3 消息与流式执行

- `POST /api/foreman/conversations/{conversation_id}/messages/stream`
  - 发起一次用户消息并流式接收结果
  - 请求中包含：
    - `content`
    - `mentions`
    - `client_message_id`

### 13.4 历史与上下文

- `GET /api/foreman/conversations/{conversation_id}/history`
  - 获取统一主时间线
- `DELETE /api/foreman/conversations/{conversation_id}/context`
  - 清理该会话的上下文
  - 包括主时间线上下文和成员线程上下文

---

## 14. 流式协议建议

### 14.1 复用现有 SSE 协议

建议复用现有 `StreamMessage` / SSE 能力，不额外设计全新前端传输协议。

在 `Foreman` 场景下新增或扩展的事件语义可以包括：

- `ROUND_STARTED`
- `COORDINATOR_DECISION`
- `AGENT_SELECTED`
- `AGENT_MESSAGE`
- `AGENT_CORRECTION`
- `ROUND_COMPLETED`

如果不希望改动现有协议类型，也可以通过现有：

- `STATUS`
- `THOUGHT`
- `ERROR`
- `DONE`

承载这些语义，只在 `payload` 中增加 `conversation_id`、`agent_name`、`round_id`、`decision_type` 等字段。

### 14.2 前端需要感知的信息

前端至少需要拿到：

- 当前是哪位 Agent 正在回复
- 当前是否由 coordinator 触发了补充调度
- 当前轮次是否结束
- 当前消息属于哪个会话 / 哪个轮次

---

## 15. 一次完整执行的后端流程

以群聊默认提问为例：

1. 前端调用 `POST /messages/stream`
2. 后端创建 `round_id`
3. 写入用户消息到主时间线
4. 调用 `ForemanCoordinatorService.plan_round(...)`
5. 获得首轮调度计划
6. 依次或并行调用现有 `AgentRuntimeService.execute_agent_stream(...)`
7. 将各 Agent 的输出转成统一 Foreman 流事件
8. 写入主时间线
9. coordinator 评估是否需要纠偏
10. 若需要且未超阈值，则触发下一轮调度
11. 结束本轮并输出 `DONE`

---

## 16. MVP 建议

### 16.1 MVP 范围

第一阶段建议只做：

- 单聊 + 群聊统一会话模型
- 群聊成员管理
- 群聊默认自动路由
- `@Agent` 定向回复
- 最多一次自动纠偏
- 统一历史与流式输出

### 16.2 MVP 不做

第一阶段不建议做：

- 多轮复杂自动协商
- coordinator 汇总多 Agent 长文报告
- 非常细的调度配置面板
- coordinator 自定义脚本编排

### 16.3 为什么这样切分

因为首版最重要的是先验证三件事：

1. 用户是否真的需要群聊形态
2. coordinator 自动分发是否比手动切换 Agent 更高效
3. 自动纠偏是否能提升答案质量而不是制造噪音

---

## 17. 风险与应对

### 17.1 风险：群聊噪音过高

多个 Agent 连续输出会让时间线变乱。

应对：

- 默认优先单 Agent 回复
- 只在必要时追加其他 Agent
- 对自动纠偏次数设上限

### 17.2 风险：用户不理解为什么是某个 Agent 回答

应对：

- 展示简洁的系统调度状态
- 在 UI 中明确“自动协调已开启”

### 17.3 风险：coordinator 过度干预

应对：

- 用户显式 `@Agent` 时优先满足用户意图
- 将纠偏限制在轻量补充或一次转交

### 17.4 风险：后端实现复杂度快速膨胀

应对：

- 复用现有单 Agent runtime
- 新增 Foreman 编排层，不破坏旧能力
- MVP 只做有限调度动作

---

## 18. 验收标准

满足以下条件，可认为 `Foreman` 首版设计达标：

- 用户可以在同一入口下创建单聊与群聊
- 单聊能够稳定调用单 Agent 回复
- 群聊中 coordinator 能对未 `@` 的问题做自动分发
- 群聊中用户可以 `@` 某个 Agent 定向提问
- 当首轮答案明显不合适时，coordinator 能自动触发一次纠偏
- 前端可以清晰识别是谁在回复、谁被调度、当前轮次是否结束
- 会话具有统一历史，不依赖用户理解多个 Agent 子线程

---

## 19. 结论

`Foreman` 的本质不是“多人同时聊天”，而是一个 **以聊天界面承载的多 Agent 编排系统**。

从产品视角看，它要做到：

- 对用户足够简单
- 对复杂问题足够智能
- 对结果质量具备基本纠偏能力
- 对显式用户意图保持可控

从实现视角看，最合理的方案是：

- 保留现有单 Agent runtime 作为执行底座
- 新增 `Foreman` 会话与编排层
- 在群聊模式下引入后台 `coordinator agent`
- 用统一主时间线把“用户—Agent—调度”串起来

这将是 `Foreman` 从“前端本地群聊原型”演进为“可真实交付的多 Agent 产品能力”的关键一步。
