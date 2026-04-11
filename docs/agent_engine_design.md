# Agent Runtime Framework Design / Agent 运行时框架设计

> Status: this document reflects the **current implementation**, not an early proposal.
>
> 状态说明：本文描述的是 **当前已经落地的实现**，不是历史规划稿。

## 1. Design Goal / 设计目标

LocalBrisk needs an agent framework that can be built directly from local files, mounted into an isolated workspace, streamed to the frontend, and reloaded automatically when agent configuration changes.

The implemented design therefore prioritizes:

- **filesystem-first configuration**
- **one shared build context for multiple runtimes**
- **session-aware execution**
- **stable frontend streaming protocol**
- **safe runtime rebuild when configuration changes**

### 中文要点

- 目标不是单纯“跑起来一个 Agent”，而是要支持 **本地文件配置、隔离工作区、流式 UI、会话持久化、自动热重载**。
- 设计上优先保证共享上下文、运行时可切换、前端协议稳定。

---

## 2. Runtime Status / 当前运行时状态

### 2.1 Primary path

The production/default path is:

```text
AgentRuntimeService -> OpenAIAgentsEngine -> OpenAIAgentRuntime
```

### 2.2 Shared loading layer

Both the primary runtime and the legacy compatibility runtime rely on the same loader:

- `agent_context_loader.py`

That loader normalizes everything needed for runtime build:

- `agent_spec.yaml`
- active model config
- enabled memories
- enabled skills
- writable output path
- mounted asset bundles

### 2.3 Legacy path

`DeepAgentsEngine` still exists, but it is now kept mainly for:

- staged cleanup
- test migration
- compatibility work
- preserving conceptual continuity for older code paths

### 中文要点

- 当前默认路径是 **OpenAI Agents runtime**。
- `agent_context_loader.py` 是真正的共享核心。
- `DeepAgentsEngine` 仍保留，但主要是兼容/迁移用途，不再是默认路径。

---

## 3. Component Map / 组件地图

| Component | Role | Notes |
|----------|------|-------|
| `AgentRuntimeService` | runtime lifecycle coordinator | load, execute, cancel, status, snapshot, unload, history |
| `AgentRuntimeState` | in-memory state per loaded agent | includes `config_fingerprint` |
| `agent_context_loader.py` | framework-neutral context loader | resolves spec, model, memories, skills, bundles |
| `OpenAIAgentsEngine` | default runtime builder | creates tools, handoffs, sessions, SDK agent |
| `OpenAIAgentRuntime` | session-aware runtime wrapper | wraps SDK `Agent` + `SQLiteSession` cache |
| `handoff_registry.py` | handoff adapter | converts built-in subagent registry into OpenAI handoffs |
| `RuntimeEventAdapter` | OpenAI runtime streaming adapter | converts SDK runtime events into `StreamMessage` |
| `ConversationHistoryStore` | history persistence | stores thread history in markdown files |
| `DeepAgentsEngine` | legacy runtime builder | retained for migration and compatibility |

### 中文要点

- `AgentRuntimeService` 负责整个生命周期。
- `agent_context_loader.py` 负责把目录结构转换成统一构建上下文。
- `OpenAIAgentsEngine` 负责把上下文组装成真正可跑的 runtime。
- `handoff_registry.py` 负责把旧的 subagent 定义适配成 OpenAI handoff。

---

## 4. Directory Contract / 目录契约

The framework is built from the BusinessUnit directory tree:

```text
{business_unit}/
├── config.yaml
├── agents/{agent_name}/
│   ├── agent_spec.yaml
│   ├── models/
│   │   └── {model_name}.yaml
│   ├── memories/
│   │   └── *.md
│   ├── skills/
│   │   └── {skill_name}/SKILL.md
│   ├── prompts/
│   │   └── *.md
│   └── output/
└── asset_bundles/{bundle_name}/
    ├── bundle.yaml
    ├── ontology.yaml
    └── volumes/*.yaml
```

Runtime resolution rules:

- `active_model` or `llm_config.llm_model` selects the active model file.
- `instruction.user_prompt_templates` selects memory files under `memories/`.
- `capabilities.native_skills` selects skill directories under `skills/`.
- asset bundle metadata is loaded from the BusinessUnit root and exposed to the runtime workspace.

### 中文要点

- Agent 的运行定义就是目录结构本身。
- `agent_spec.yaml` 只是入口，不是全部配置。
- 模型、memory、skill、asset bundle 都是运行时构建的一部分。

---

## 5. Build Flow / 构建流程

### 5.1 Load / reload entry

`AgentRuntimeService.load_agent(...)` is the only supported entry for building or rebuilding an in-memory runtime instance.

### 5.2 Build sequence

```text
1. Resolve agent path
2. Compute current config fingerprint
3. Compare with loaded AgentRuntimeState
4. Reuse or rebuild
5. Load AgentBuildContext
6. Build OpenAI runtime
7. Mark state READY
```

### 5.3 OpenAI runtime assembly

`OpenAIAgentsEngine.build_agent(...)` performs these steps:

1. load `AgentBuildContext`
2. validate that one model config can be resolved
3. build the OpenAI-compatible model bundle
4. assemble instructions from:
   - base agent description
   - system prompt fields
   - mounted asset bundle hints
   - memory markdown
   - skill markdown
5. create the workspace backend
6. create built-in tools bound to the workspace
7. build handoffs from the subagent registry
8. return `OpenAIAgentRuntime`

### 中文要点

- 所有构建都从 `load_agent(...)` 进入。
- OpenAI runtime 的拼装步骤已经固定：**上下文 → 模型 → 指令 → workspace → tools → handoffs → runtime**。

---

## 6. Execution Lifecycle / 执行生命周期

### 6.1 Streaming execution

Primary execution path:

```text
POST /api/runtime/{bu}/agents/{agent}/execute/stream
  -> AgentRuntimeService.execute_agent_stream(...)
  -> ensure READY runtime
  -> mark RUNNING
  -> stream messages
  -> persist history turn
  -> mark READY again
```

### 6.2 Snapshot recovery

Execution snapshots are stored in memory by `AgentRuntimeService` and can be retrieved through:

- `GET /api/runtime/{bu}/agents/{agent}/execution/{execution_id}/snapshot`

### 6.3 Thread and session behavior

- `thread_id` defaults to `agent_name` when omitted.
- For the OpenAI runtime, `thread_id` maps to a persisted SDK session.
- LocalBrisk also stores a frontend-oriented history file for each thread.

### 中文要点

- 执行入口是 runtime SSE 接口。
- `thread_id` 既影响 SDK session，也影响本地历史文件的归档。
- 快照恢复是内存级恢复；聊天历史是文件级持久化。

---

## 7. Hot Reload Design / 热重载设计

The framework now uses **fingerprint-based reload** instead of naive READY-state reuse.

### 7.1 Fingerprint inputs

`compute_agent_context_fingerprint(...)` currently includes:

- `agent_spec.yaml`
- `models/`
- `memories/`
- `skills/`
- `prompts/`
- BusinessUnit `asset_bundles/`

### 7.2 Reload rules

- same fingerprint -> reuse runtime
- changed fingerprint + READY -> unload old resources, rebuild automatically
- changed fingerprint + RUNNING -> keep current execution, rebuild on next request

### 7.3 Why it matters

This ensures changes such as switching `active_model` in `agent_spec.yaml` actually take effect without requiring a manual full restart.

### 中文要点

- 热重载已经不是简单的“状态不是空就复用”。
- 现在会对配置文件做签名，只有签名相同才复用。
- 改 `active_model` 这类配置后，下一次请求就能自动吃到新配置。

---

## 8. Session, History, and Artifacts / 会话、历史与产物

### 8.1 Session DB

OpenAI SDK sessions are stored in:

- `output/.openai_sessions.sqlite`

### 8.2 Chat history

Conversation turns are rendered into markdown files under:

- `output/.chathistory/`

### 8.3 Task and artifact workspace

Generated runtime files live under the agent output workspace, including:

- `output/.task/`
- any execution artifacts produced by tools

### 中文要点

- SDK session 和前端历史不是同一份数据。
- session 放在 SQLite，history 放在 Markdown 容器文件里。
- 所有运行期副产物都应落在各自 Agent 的 `output/` 下。

---

## 9. Compatibility Notes / 兼容说明

Important migration facts for contributors:

- Do not describe the framework as “DeepAgents-only” anymore.
- Do not assume `agent_spec.yaml` changes require a backend restart.
- Do not assume the runtime chooses engines dynamically at request time; it currently defaults to `OpenAIAgentsEngine`.
- Do remember that `DeepAgentsEngine` is still part of the codebase and tests.

### 中文要点

- 文档和设计说明不能再把框架写成“只有 DeepAgents”。
- `agent_spec.yaml` 修改后已经支持自动重建，不需要再默认建议重启后端。
- 当前默认运行时是固定选 `OpenAIAgentsEngine`，不是运行时临时随机切换。

---

## 10. Maintenance Checklist / 维护清单

When updating this framework, documentation should stay aligned with these files first:

- `agent_engine/services/agent_runtime_service.py`
- `agent_engine/engine/agent_context_loader.py`
- `agent_engine/engine/openai_agents_engine.py`
- `agent_engine/engine/handoff_registry.py`
- `app/api/endpoints/agent_runtime.py`

If these files change materially, update:

- `README.md`
- `README_zh.md`
- `backend/architecture.md`
- `docs/API.md`
- `docs/agent_spec_example.yaml`

### 中文要点

- 这几个核心文件是 agent 文档的“事实来源”。
- 只要 runtime service、loader、engine、handoff 或 runtime API 发生明显变化，就应同步更新上面的文档集合。
