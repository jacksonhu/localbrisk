# DeepAgents Compatibility Guide / DeepAgents 兼容说明

> Important: this file no longer describes the **primary** LocalBrisk runtime.
>
> 重要说明：本文档不再描述 LocalBrisk 的**默认主运行时**。

LocalBrisk now uses **`OpenAIAgentsEngine` as the default runtime path**, while `DeepAgentsEngine` remains as a legacy compatibility path for migration, testing, and staged cleanup.

---

## 1. Current Positioning / 当前定位

| Topic | Current status |
|------|----------------|
| Default runtime | `OpenAIAgentsEngine` |
| Shared config loader | `agent_context_loader.py` |
| Legacy runtime | `DeepAgentsEngine` |
| Frontend stream protocol | `StreamMessage` |
| Hot reload behavior | fingerprint-based rebuild in `AgentRuntimeService` |

### 中文要点

- 默认运行时已经切到 **OpenAI Agents SDK**。
- `DeepAgentsEngine` 仍在代码库里，但角色变成了 **兼容路径**。
- 不论底层 runtime 是什么，前端仍统一消费 `StreamMessage`。

---

## 2. What Is Still Shared / 仍然共享的部分

Even though the default runtime changed, several important pieces are still shared conceptually or directly in code:

- **filesystem-first agent definition**
- **shared `AgentBuildContext` loading**
- **memory/skill/asset bundle mounting model**
- **runtime lifecycle ownership in `AgentRuntimeService`**
- **frontend streaming contract**

### 中文要点

- LocalBrisk 并没有推翻原来的“目录即运行定义”思路。
- 共享 loader、挂载模型、生命周期管理、前端流式协议仍然沿用并升级了原有设计。

---

## 3. Concept Mapping / 概念映射

The table below maps common DeepAgents concepts to the current LocalBrisk implementation:

| DeepAgents-oriented concept | Current LocalBrisk equivalent |
|----------------------------|-------------------------------|
| `create_deep_agent(...)` | `OpenAIAgentsEngine.build_agent(...)` |
| backend / filesystem backend | `create_workspace_backend(context)` |
| subagents | `handoff_registry.py` -> OpenAI handoffs |
| memory files | `instruction.user_prompt_templates` -> `memories/*.md` |
| skill directories | `capabilities.native_skills` -> `skills/<name>/SKILL.md` |
| long-running runtime state | `AgentRuntimeService` + `AgentRuntimeState` |
| conversation continuity | OpenAI `SQLiteSession` + LocalBrisk markdown history |
| reload after config change | `config_fingerprint` comparison |

### 中文要点

- 以前你从 DeepAgents 视角理解的 backend、subagent、memory、skill，现在都有对应的 LocalBrisk 当前实现映射。
- 最关键的变化是：**subagent 现在通过 handoff 适配，配置热重载通过 fingerprint 实现**。

---

## 4. When DeepAgents Still Matters / 什么时候还需要关心 DeepAgents

You may still need to inspect `DeepAgentsEngine` when:

- debugging legacy tests
- comparing behavior during migration
- validating shared loader assumptions
- understanding older tool abstractions still reflected in code comments or helper names

You should **not** describe it as the default runtime in user-facing documentation.

### 中文要点

- 看 DeepAgents 代码主要是为了兼容、迁移、排查历史逻辑。
- 面向用户的文档里，不应再把它描述成默认 runtime。

---

## 5. Key Behavioral Differences / 关键行为差异

### 5.1 Engine selection

- **Current default**: `AgentRuntimeService` calls `get_openai_agents_engine()`.
- **Legacy**: `DeepAgentsEngine` remains available but is not selected by default.

### 5.2 Session model

- **Current default**: OpenAI SDK sessions are persisted in `output/.openai_sessions.sqlite`.
- **Legacy mental model**: checkpoint-oriented execution with DeepAgents/LangGraph helpers.

### 5.3 History model

- **Current default**: LocalBrisk writes user-facing conversation history to `output/.chathistory/*.md`.
- **Important distinction**: chat history is not the same thing as SDK session persistence.

### 5.4 Reload model

- **Current default**: runtime reuse is guarded by `config_fingerprint`.
- **Legacy problem**: READY runtimes could previously be reused even when `agent_spec.yaml` changed.

### 中文要点

- 当前最大的变化有三点：**默认引擎、会话持久化方式、热重载机制**。
- 历史聊天文件和 SDK session 现在是分离设计。

---

## 6. Migration Checklist / 迁移检查清单

If you are updating old documentation or old mental models, apply this checklist:

1. Replace “DeepAgents is the runtime” with “OpenAI Agents SDK is the default runtime; DeepAgents is legacy compatibility”.
2. Replace “restart backend after changing `agent_spec.yaml`” with “the next request will rebuild automatically when the fingerprint changes”.
3. Replace “subagents only” wording with “handoffs are built from the existing subagent registry”.
4. Document both **session persistence** and **conversation history persistence**.
5. Point readers to `agent_context_loader.py` as the shared source of truth for runtime build inputs.

### 中文要点

- 更新旧文档时，最容易遗漏的是：**默认 runtime 已切换**、**热重载已具备**、**handoff 替代了旧的 subagent 叙事**。

---

## 7. Practical Recommendation / 实用建议

When contributors ask “how does the agent framework work now?”, start from these files instead of starting from DeepAgents docs:

- `agent_engine/services/agent_runtime_service.py`
- `agent_engine/engine/agent_context_loader.py`
- `agent_engine/engine/openai_agents_engine.py`
- `agent_engine/engine/handoff_registry.py`
- `app/api/endpoints/agent_runtime.py`

Use DeepAgents docs only as a **compatibility reference**, not as the primary architecture source.

### 中文要点

- 如果要理解“现在的 Agent 框架怎么工作”，应该先看 runtime service、shared loader、OpenAI engine、handoff registry 和 runtime API。
- DeepAgents 文档现在更适合作为“兼容参考”，而不是“架构主文档”。
