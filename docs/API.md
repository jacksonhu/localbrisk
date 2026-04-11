# LocalBrisk Backend API Overview / LocalBrisk 后端 API 总览

> Base URL (dev): `http://127.0.0.1:8765`
>
> Swagger (dev only): `http://127.0.0.1:8765/docs`

This document summarizes the **current backend API shape** with extra detail for the agent runtime endpoints.

本文档基于**当前后端实现**整理，重点补充 Agent runtime 相关接口。

---

## 1. Route Groups / 路由分组

All API routers are mounted under `/api`.

| Route group | Purpose |
|------------|---------|
| `/health` | process health and readiness |
| `/api/business_units` | BusinessUnit and nested resource CRUD |
| `/api/runtime` | agent runtime and model runtime |
| `/api/llm` | LLM provider and model catalog |
| `/api/compute` | DuckDB execution |
| `/api/i18n/locales` | supported locales |

### 中文要点

- 所有业务 API 都挂在 `/api` 下。
- Agent 框架相关接口主要集中在 `/api/runtime`。

---

## 2. Agent Runtime Endpoints / Agent 运行时接口

### 2.1 Endpoint table

| Method | Path | Purpose |
|-------|------|---------|
| `POST` | `/api/runtime/{business_unit_id}/agents/{agent_name}/load` | load or rebuild a runtime instance |
| `POST` | `/api/runtime/{business_unit_id}/agents/{agent_name}/execute/stream` | execute agent with SSE streaming |
| `GET` | `/api/runtime/{business_unit_id}/agents/{agent_name}/execution/{execution_id}/snapshot` | fetch reconnect snapshot |
| `GET` | `/api/runtime/{business_unit_id}/agents/{agent_name}/status` | query runtime status |
| `POST` | `/api/runtime/{business_unit_id}/agents/{agent_name}/cancel` | request cancellation |
| `GET` | `/api/runtime/{business_unit_id}/agents/{agent_name}/history` | load local conversation history |
| `DELETE` | `/api/runtime/{business_unit_id}/agents/{agent_name}/context` | clear local session/history for one thread |
| `DELETE` | `/api/runtime/{business_unit_id}/agents/{agent_name}/unload` | unload current runtime instance |
| `GET` | `/api/runtime/agents/loaded` | list loaded runtimes |

### 中文要点

- `load` 会加载或在必要时自动重建 runtime。
- `execute/stream` 是核心 SSE 执行接口。
- `history` / `context` 分别用于查询历史与清理上下文。

---

## 3. Request and Response Examples / 请求与响应示例

### 3.1 Load agent

**Request**

```http
POST /api/runtime/sales/agents/sales_analyst/load
```

**Response**

```json
{
  "message": "Agent sales_analyst loaded successfully",
  "agent_name": "sales_analyst",
  "business_unit_id": "sales",
  "status": "ready"
}
```

### 3.2 Execute agent with SSE

**Request**

```http
POST /api/runtime/sales/agents/sales_analyst/execute/stream
Content-Type: application/json
```

```json
{
  "input": "Summarize revenue trend for Q1 and create a chart.",
  "context": {
    "thread_id": "q1-review",
    "request_id": "req-123",
    "session_id": "sess-123"
  }
}
```

**Response**

- `Content-Type: text/event-stream`
- body contains SSE frames generated from `StreamMessage.to_sse()`

### 3.3 Query conversation history

**Request**

```http
GET /api/runtime/sales/agents/sales_analyst/history?thread_id=q1-review
```

**Response**

```json
{
  "agent_name": "sales_analyst",
  "thread_id": "q1-review",
  "history_file": "sales_analyst_q1-review.md",
  "turns": []
}
```

### 3.4 Clear conversation context

**Request**

```http
DELETE /api/runtime/sales/agents/sales_analyst/context?thread_id=q1-review
```

**Response**

```json
{
  "message": "conversation context cleared",
  "success": true
}
```

### 中文要点

- `execute/stream` 请求体只需要 `input`，`context` 可选。
- `thread_id` 会影响会话隔离与历史文件归档。
- `history` 返回的是本地持久化的线程历史，不是底层 SDK 原始对象。

---

## 4. StreamMessage Protocol / StreamMessage 协议

The frontend renders streamed execution through a normalized message schema.

| Type | Meaning |
|------|---------|
| `THOUGHT` | reasoning or progress text |
| `TASK_LIST` | structured task list |
| `ARTIFACT` | generated artifact or file result |
| `STATUS` | transient status update |
| `ERROR` | structured error |
| `DONE` | execution completed |

Example SSE payload:

```json
{
  "type": "STATUS",
  "payload": {
    "message": "Agent execution started"
  },
  "execution_id": "q1-review",
  "timestamp": 1712812800.0,
  "seq": 1
}
```

### 中文要点

- 前端不直接依赖底层 runtime 事件格式，而是依赖统一的 `StreamMessage`。
- 这也是 OpenAI runtime 和 legacy runtime 能共用前端渲染层的关键原因。

---

## 5. Runtime Behavior Notes / Runtime 行为说明

### 5.1 Thread default

If `thread_id` is not provided, LocalBrisk uses `agent_name` as the default thread identifier.

### 5.2 Session persistence

For the default OpenAI runtime, `thread_id` maps to a persisted SDK session stored under:

- `output/.openai_sessions.sqlite`

### 5.3 History persistence

Conversation history is stored separately in markdown files under:

- `output/.chathistory/`

### 5.4 Snapshot scope

Execution snapshots returned by the snapshot endpoint are runtime-memory data intended for reconnect recovery.

### 5.5 Hot reload

A new request may automatically rebuild the runtime if the configuration fingerprint changed (for example after editing `agent_spec.yaml` or model files).

### 中文要点

- `thread_id` 同时影响 session 和 history 的分线程行为。
- session 与 history 是分离持久化。
- 修改 `agent_spec.yaml` 后，下一次请求可能自动触发 runtime 重建。

---

## 6. Other Important Route Groups / 其他重要接口组

### 6.1 BusinessUnit routes

`/api/business_units` manages the filesystem-backed resource tree, including:

- BusinessUnits
- Agents
- models / memories / skills / MCP resources
- AssetBundles and nested assets

### 6.2 Model runtime routes

`/api/runtime/{business_unit_id}/agents/{agent_name}/models/{model_name}` provides direct model execution paths separate from full agent orchestration.

### 6.3 LLM catalog routes

`/api/llm` exposes provider/model metadata used by the UI and runtime configuration flows.

### 6.4 Compute routes

`/api/compute` exposes DuckDB-backed SQL execution.

### 中文要点

- `business_units` 负责控制面资源管理。
- `runtime` 负责 Agent/Model 运行。
- `llm` 提供模型目录，`compute` 提供 DuckDB 能力。

---

## 7. Recommendation / 使用建议

For the most accurate and complete API contract, use this document together with:

- Swagger at `http://127.0.0.1:8765/docs` in development mode
- `backend/app/api/endpoints/agent_runtime.py`
- `backend/app/api/__init__.py`

### 中文要点

- 本文档适合作为结构化总览。
- 如果要看最精确的字段与错误语义，请结合 Swagger 和对应 endpoint 源码一起看。
