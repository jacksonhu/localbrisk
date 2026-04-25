# LocalBrisk Backend Architecture / LocalBrisk 后端架构

## 1. Scope / 范围

This document describes the **current backend architecture that is already implemented** under `backend/`. It focuses on the Python/FastAPI side, especially the agent runtime framework, the configuration-as-code model, streaming execution, persistence, and runtime reload behavior.

### 中文速览

- 本文档描述的是 **已经落地的当前实现**，不是早期规划稿。
- 重点覆盖 `backend/` 内的 Python/FastAPI 后端，尤其是 Agent 运行框架、配置即代码、流式执行、持久化和热重载。
- 前端与 Tauri 壳层只在接口边界处简要提及，不展开实现细节。

---

## 2. Backend Shape / 后端分层

The backend is organized around three major planes:

| Plane | Key modules | Responsibility |
|------|-------------|----------------|
| **Control plane** | `app/api`, `app/services`, `app/models` | BusinessUnit / Agent / AssetBundle CRUD, filesystem-backed metadata management |
| **Runtime plane** | `agent_engine/engine`, `agent_engine/services`, `agent_engine/tools` | Agent build, runtime lifecycle, streaming execution, session/history management |
| **Compute plane** | `compute_engine`, `app/api/endpoints/compute_engine.py` | Embedded DuckDB execution, result shaping, query audit/history |

Supporting concerns are provided by `app/core` for logging, configuration, i18n, constants, middleware, and service startup/shutdown behavior.

### 中文速览

- **控制面**：`BusinessUnit / Agent / AssetBundle` 等目录化资源的 CRUD。
- **运行面**：Agent 构建、会话管理、SSE 流式执行、历史记录与取消/卸载。
- **计算面**：DuckDB 本地计算与 SQL 审计。
- **基础能力**：`app/core` 提供日志、配置、国际化、中间件与常量。

---

## 3. Current Agent Framework / 当前 Agent 框架

### 3.1 Primary runtime

`AgentRuntimeService` now resolves its engine through `get_openai_agents_engine()` and therefore uses **`OpenAIAgentsEngine` as the default runtime path**.

Main responsibilities of the current runtime stack:

- `AgentRuntimeService`: lifecycle orchestration, execution state, cancellation, snapshot handling, history access, unload/reload behavior.
- `agent_context_loader.py`: framework-neutral loading of `agent_spec.yaml`, active model, enabled memories, enabled skills, output directory, and mounted asset bundles.
- `OpenAIAgentsEngine`: turns the shared build context into an OpenAI Agents SDK runtime.
- `OpenAIAgentRuntime`: keeps the SDK agent plus persisted `SQLiteSession` handles.
- `handoff_registry.py`: adapts the existing built-in subagent registry into **OpenAI Agents handoffs**.

### 3.2 Compatibility path

`DeepAgentsEngine` is still present, but it is now a **legacy compatibility path** kept for staged cleanup, compatibility work, and test migration. It is no longer the default runtime selected by `AgentRuntimeService`.

### 中文速览

- 当前默认运行时已经切到 **`OpenAIAgentsEngine`**。
- `agent_context_loader.py` 是两套运行时共享的上下文加载器。
- `DeepAgentsEngine` 仍保留，但定位已经变成 **兼容/迁移路径**，不再是默认执行路径。
- `handoff_registry.py` 会把现有内置 subagent 注册表转换成 **OpenAI Agents handoffs**。

---

## 4. Agent Build Pipeline / Agent 构建链路

At a high level, one runtime build follows this sequence:

```text
HTTP/SSE request
  -> AgentRuntimeService
  -> compute_agent_context_fingerprint(...)
  -> load_agent_context(...)
  -> OpenAIAgentsEngine.build_agent(...)
  -> workspace backend + built-in tools + handoffs
  -> OpenAIAgentRuntime
  -> RuntimeEventAdapter / StreamMessage protocol
```

Detailed steps:

1. A request reaches `/api/runtime/{business_unit_id}/agents/{agent_name}/...`.
2. `AgentRuntimeService` resolves the agent directory and computes a **configuration fingerprint**.
3. If reuse is allowed, the already-loaded runtime is returned; otherwise a rebuild is triggered.
4. `load_agent_context(...)` loads:
   - `agent_spec.yaml`
   - the resolved model from `llm_config.llm_model`
   - auto-loaded memory files from `memories/`
   - enabled skills from `skills/`
   - writable `output/`
   - BusinessUnit-level asset bundles
5. `OpenAIAgentsEngine.build_agent(...)` creates:
   - the model bundle
   - the workspace backend
   - built-in tools bound to the workspace
   - OpenAI SDK handoffs from the subagent registry
   - a session-aware `OpenAIAgentRuntime`
6. Streaming output is normalized into `StreamMessage` packets for the frontend.

### 中文速览

- 请求进入 runtime API 后，先做 **配置指纹计算**。
- 然后通过共享 loader 装载 `agent_spec.yaml`、模型、memory、skill、asset bundle。
- `OpenAIAgentsEngine` 再把这些配置拼装成可执行的 OpenAI Agents runtime。
- 最终所有流式事件都会被归一成前端消费的 `StreamMessage`。

---

## 5. Configuration-as-Code Contract / 配置即代码约定

The runtime is built directly from the filesystem. One agent directory typically looks like this:

```text
Catalogs/{business_unit}/
├── config.yaml
├── agents/{agent_name}/
│   ├── agent_spec.yaml
│   ├── models/*.yaml
│   ├── memories/*.md
│   ├── skills/{skill_name}/SKILL.md
│   └── output/
└── asset_bundles/{bundle_name}/
    ├── bundle.yaml
    ├── ontology.yaml
    └── volumes/*.yaml
```

Key runtime rules:

- `agent_spec.yaml` is the entry point and must be a YAML object.
- `llm_config.llm_model` is the sole model selector.
- `instruction` is a plain string template; `memories/*.md` are auto-loaded at runtime.
- `skills` (top-level list) resolves directories from `skills/`.
- BusinessUnit `asset_bundles/` metadata is loaded and exposed to the runtime workspace.

### 中文速览

- 当前运行时就是直接从目录结构构建出来的，**没有独立数据库保存 Agent 定义**。
- `llm_config.llm_model` 是唯一的模型选择字段。
- `instruction` 是纯字符串模板；`memories/*.md` 在运行时自动加载。
- `skills`（顶层列表）对应 `skills/<name>/SKILL.md`。

---

## 6. Runtime Lifecycle and Hot Reload / 生命周期与热重载

`AgentRuntimeState` now contains `config_fingerprint`, and `AgentRuntimeService.load_agent()` compares that fingerprint before reusing an in-memory runtime.

The fingerprint currently includes metadata from:

- `agent_spec.yaml`
- `models/`
- `memories/`
- `skills/`
- BusinessUnit `asset_bundles/`

Reload semantics:

- **Unchanged fingerprint**: reuse the loaded runtime.
- **Changed fingerprint + READY**: close old resources and rebuild automatically on the next request.
- **Changed fingerprint + RUNNING**: keep the current execution alive, and apply the new config to the following request.
- **Manual unload**: still available through the runtime API.

This behavior fixes the previous issue where changing `agent_spec.yaml` (for example `llm_config.llm_model`) did not take effect because the old READY runtime was reused blindly.

### 中文速览

- 现在 runtime 会记录 `config_fingerprint`，复用前先比较文件签名。
- `agent_spec.yaml`、模型、memory、skill、asset bundle 变更都会影响签名。
- **READY** 状态下配置变更会自动重建。
- **RUNNING** 状态下不会打断当前执行，而是下一次请求再切新配置。

---

## 7. Streaming, Sessions, and History / 流式执行、会话与历史

### 7.1 Streaming protocol

The frontend consumes a unified `StreamMessage` protocol with the following message types:

- `THOUGHT`
- `TASK_LIST`
- `ARTIFACT`
- `STATUS`
- `ERROR`
- `DONE`

For the OpenAI runtime path, runtime events are adapted through `RuntimeEventAdapter`. The legacy path still uses `MessageTranslator` and `AgentExecutionStreamer`.

### 7.2 Session persistence

`OpenAIAgentRuntime` caches SDK sessions and persists them in:

- `output/.openai_sessions.sqlite`

This enables session-aware execution keyed by `thread_id`.

### 7.3 Conversation history

Conversation history is persisted separately by `ConversationHistoryStore` in markdown files under:

- `output/.chathistory/`

Each thread is stored as a markdown container with embedded JSON. Execution snapshots used for reconnect recovery are kept **in memory** by `AgentRuntimeService`.

### 中文速览

- 前端只认统一的 `StreamMessage` 协议。
- OpenAI runtime 会把 SDK session 持久化到 `output/.openai_sessions.sqlite`。
- 对话历史单独写入 `output/.chathistory/*.md`。
- 断线重连快照是运行时内存数据，不是长期持久化存储。

---

## 8. API Boundaries / API 边界

Route registration is centralized in `app/api/__init__.py`:

| Route group | Purpose |
|------------|---------|
| `/api/health` | health and readiness |
| `/api/business_units` | BusinessUnit and nested resource CRUD |
| `/api/runtime` | agent runtime and model runtime |
| `/api/llm` | provider/model catalog |
| `/api/compute` | DuckDB execution |

Important agent runtime endpoints include:

- `POST /api/runtime/{business_unit_id}/agents/{agent_name}/load`
- `POST /api/runtime/{business_unit_id}/agents/{agent_name}/execute/stream`
- `GET /api/runtime/{business_unit_id}/agents/{agent_name}/execution/{execution_id}/snapshot`
- `GET /api/runtime/{business_unit_id}/agents/{agent_name}/status`
- `POST /api/runtime/{business_unit_id}/agents/{agent_name}/cancel`
- `GET /api/runtime/{business_unit_id}/agents/{agent_name}/history`
- `DELETE /api/runtime/{business_unit_id}/agents/{agent_name}/context`
- `DELETE /api/runtime/{business_unit_id}/agents/{agent_name}/unload`

### 中文速览

- API 分组已经从旧的 Catalog/Schema 叙事迁移到 `business_units` + `runtime` + `compute`。
- Agent 框架相关的核心接口都在 `/api/runtime/...` 下。
- 历史查询、清理上下文、取消执行、卸载 runtime 都已经具备独立端点。

---

## 9. Storage and Persistence / 存储与持久化

| Storage | Path | Purpose |
|--------|------|---------|
| Filesystem catalogs | `~/.localbrisk/App_Data/Catalogs/` | BusinessUnit / Agent / AssetBundle definitions |
| Agent output workspace | `agents/{agent}/output/` | generated artifacts, tasks, session DB, chat history |
| DuckDB | `~/.localbrisk/localbrisk.db` | local compute engine and SQL history |
| Logs | platform-specific app log path | rolling backend logs |

### 中文速览

- 领域配置仍以文件系统为主。
- Agent 运行副产物全部集中在各自的 `output/` 下。
- DuckDB 只负责本地计算与历史记录，不承担 Agent 定义存储。

---

## 10. Observability and Safety / 可观测性与安全

Implemented backend protections and operational patterns include:

- structured runtime events via `emit_runtime_event(...)`
- scoped logging context for request/session/agent correlation
- controlled SQL execution paths in the compute engine
- conversation history separation from session state
- explicit resource cleanup through `close_agent_resources(...)`
- path resolution helpers to keep runtime operations inside expected directories

### 中文速览

- 运行时有结构化事件与日志上下文，便于排查问题。
- 资源清理已经统一收敛到 `close_agent_resources(...)`。
- SQL 执行与文件路径访问都有限制边界。

---

## 11. Architecture Status / 架构状态结论

The backend now has a clear direction:

- **default runtime = OpenAI Agents SDK**
- **shared loader = filesystem-first, framework-neutral**
- **legacy runtime = DeepAgents compatibility path**
- **reload model = fingerprint-based automatic rebuild**

This is the architectural baseline that other documentation should follow.

### 中文速览

- 当前后端架构基线已经明确：**默认 OpenAI runtime，共享 loader，DeepAgents 兼容保留，指纹热重载**。
- 后续文档、测试和功能描述都应以这个基线为准。
