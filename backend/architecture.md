# LocalBrisk Backend 技术架构设计文档

## 1. 文档目标与范围

本文档用于系统化说明 `LocalBrisk` 后端（`backend`）的技术架构设计，覆盖：

- 系统分层与模块职责
- 关键运行流程（Agent 运行、Model 运行、Compute SQL 执行）
- 数据与存储架构（文件系统 + DuckDB）
- API 设计与边界划分
- 可观测性、配置管理与安全设计
- 演进建议与风险点

> 范围仅包含 `backend` 目录下 Python/FastAPI 侧实现，不包含前端与 Tauri 壳层实现细节。

---

## 2. 架构总览

后端采用 **FastAPI + 领域服务 + 引擎适配层** 的结构，整体可概括为“**控制面（Catalog/配置）+ 运行面（Agent/Model）+ 计算面（DuckDB）**”三面协同。

### 2.1 分层视图

1. **接口层（API Layer）**
   - 目录：`app/api/endpoints`
   - 负责 HTTP/SSE 协议处理、参数校验、错误映射、响应模型。

2. **业务服务层（Application Service Layer）**
   - 目录：`app/services`
   - 负责 BusinessUnit/AssetBundle/Agent/Model/MCP/Memory 等领域对象的 CRUD 与组合业务。

3. **引擎层（Agent Engine Layer）**
   - 目录：`agent_engine`
   - 负责 Agent 构建、LLM 客户端创建、流式执行、运行状态管理、消息协议转换。

4. **计算层（Compute Engine Layer）**
   - 目录：`compute_engine`
   - 负责 DuckDB 生命周期管理、SQL 执行、结果表格化返回与执行历史记录。

5. **基础设施层（Infrastructure Layer）**
   - 配置：`app/core/config.py`
   - 日志：`app/core/logging.py`
   - 国际化：`app/core/i18n.py` + `app/core/middleware.py`
   - 常量与目录约定：`app/core/constants.py`

---

## 3. 技术栈与依赖

## 3.1 核心框架

- **Web 框架**：FastAPI
- **ASGI Server**：Uvicorn
- **数据模型**：Pydantic v2
- **配置管理**：pydantic-settings

## 3.2 AI 与运行时

- **LangGraph / LangChain / DeepAgents**：Agent 运行图与工具执行
- **langchain-openai**：兼容 OpenAI 格式客户端
- **ModelRegistry**：统一管理 endpoint/local provider 元数据

## 3.3 数据处理

- **DuckDB**：本地持久化分析数据库（`~/.localbrisk/localbrisk.db`）
- **Polars**：数据处理依赖（已引入）
- **PyYAML**：配置文件与元数据落盘

---

## 4. 目录与模块设计

## 4.1 后端顶层结构

- `main.py`：FastAPI 主入口，路由注册，启动/关闭生命周期。
- `run.py`：打包场景启动入口（PyInstaller 友好）。
- `app/`：业务接口与服务。
- `agent_engine/`：智能体执行引擎。
- `compute_engine/`：DuckDB 计算服务。
- `tests/`：单元测试。

## 4.2 `app` 模块

- `app/api`
  - `health.py`：健康/就绪检查。
  - `business_unit.py`：BusinessUnit 与其子资源（AssetBundle/Agent/Model/MCP/Memory/Skill）管理。
  - `agent_runtime.py`：Agent 加载、流式执行、状态、取消、上下文清理等。
  - `model_runtime.py`：单模型加载/执行（同步 + 流式）与状态管理。
  - `llm_providers.py`：模型提供商与模型能力检索。
  - `compute_engine.py`：DuckDB SQL 执行入口。

- `app/services`
  - `base_service.py`：目录扫描、YAML 读写、`baseinfo` 标准化能力。
  - `business_unit_service.py`：聚合根服务，委派 AssetBundleService 与 AgentService。
  - `asset_bundle_service.py`：资产包与表预览等数据资产能力。
  - `agent_service.py`：Agent/Memory/Skill/Model/MCP 的落盘管理与目录初始化。

- `app/models`
  - 统一定义 BusinessUnit、AssetBundle、Agent、Model、MCP、Memory 等 Pydantic 模型。

- `app/core`
  - `config.py`：环境变量与路径配置。
  - `logging.py`：统一日志（控制台 + 按天滚动文件）。
  - `middleware.py` + `i18n.py`：语言自动选择与多语翻译。
  - `constants.py`：资源目录规范与文件命名常量。

## 4.3 `agent_engine` 模块

- `core/`：流式协议、配置模型、异常定义。
- `engine/`：`DeepAgentsEngine`（构建并返回可执行 Agent 图）。
- `services/`：`AgentRuntimeService`（生命周期 + 执行状态 + 断线快照）。
- `llm/`：`LLMClientFactory` 与 provider/model 注册表。
- `tools/`：运行时工具集合。
- `utils/`：YAML 解析、路径解析等辅助能力。

## 4.4 `compute_engine` 模块

- `duckdb_service.py`：
  - DuckDB 单例连接管理（初始化/获取/关闭）
  - SQL 执行与结果转换（`columns + rows`）
  - 查询类 SQL 表格化包装（`table` 字段）
  - 执行历史记录（`sql_execution_history`）

---

## 5. 数据与存储架构

## 5.1 文件系统为主的领域存储

系统采用 **“目录即模型”** 的方式持久化业务对象：

- 根目录：`settings.CATALOGS_DIR`（默认 `~/.localbrisk/App_Data/Catalogs`）
- BusinessUnit 下组织：
  - `config.yaml`
  - `agents/{agent_name}/agent_spec.yaml`
  - `agents/{agent_name}/memories|skills|models|mcps|output`
  - `asset_bundles/{bundle_name}/bundle.yaml`
  - `asset_bundles/{bundle_name}/tables|functions|volumes|notes`

此设计优势：

- 配置可读可编辑，便于本地化与版本管理
- 易于导入导出（如 skill zip）
- 与 Agent 生态（prompt/skill/tool）天然契合

## 5.2 DuckDB 持久化计算存储

`compute_engine` 使用 DuckDB 作为独立计算存储：

- 连接生命周期绑定应用 startup/shutdown
- 关键表：
  - `compute_registry`：通用键值配置
  - `sql_execution_history`：SQL 执行审计（脚本、成功标识、耗时、影响行数、错误）

SQL 执行能力：

- `execute_sql_script(...)`：通用 SQL 执行
- `execute_query_sql_script(...)`：仅允许查询类语句（`SELECT/WITH/SHOW/DESCRIBE/PRAGMA`），并返回标准表格结构

---

## 6. 关键运行流程

## 6.1 应用启动流程

1. 初始化日志系统（`setup_logging()`）
2. 创建 FastAPI 应用，注册 CORS / i18n 中间件
3. 注册 `/api` 路由
4. startup 钩子初始化 DuckDB（`init_duckdb_service`）
5. shutdown 钩子关闭 DuckDB 连接

## 6.2 Agent 流式执行流程（SSE）

1. 客户端调用 `POST /api/runtime/{bu}/agents/{agent}/execute/stream`
2. API 层创建 `StreamingResponse`
3. `AgentRuntimeService.execute_agent_stream(...)` 驱动执行
4. 若未加载则先 `load_agent`，并确保 `DeepAgentsEngine` 可用
5. 将 LangGraph/DeepAgents 的流式事件翻译为统一 `StreamMessage`：
   - `THOUGHT / TASK_LIST / ARTIFACT / STATUS / ERROR / DONE`
6. 前端按消息类型分区域渲染（思考、任务、制品、状态）
7. 过程快照保留在 `ExecutionSnapshot`，支持断线恢复查询

## 6.3 Model 直连执行流程

1. `model_runtime` API 接收请求
2. 通过 `ModelExecutorService` 按 Agent 下 model 配置执行
3. 支持同步一次性结果与 SSE 流式结果
4. 支持状态查询、取消与卸载

## 6.4 SQL 计算流程

1. 调用 `POST /api/compute/sql/execute`
2. 参数进入 `DuckDBService.execute_sql_script`
3. SQL 执行后返回：
   - `columns`
   - `rows`
   - `affected_rows`
   - `truncated`
   - `execution_ms`
4. 无论成功失败都记录到 `sql_execution_history`

---

## 7. API 设计与领域边界

## 7.1 API 领域分组

- `/api/health/*`：基础健康/就绪
- `/api/business_units/*`：控制面 CRUD（业务单元及子资源）
- `/api/runtime/*`：运行面（Agent + Model）
- `/api/llm/*`：提供商/模型目录服务
- `/api/compute/*`：计算面 SQL 执行

## 7.2 接口设计特点

- 使用 Pydantic response_model 统一约束输入输出
- 业务错误映射为 HTTP 状态码（400/404/500/503）
- 运行时流式接口采用 SSE，利于前端实时增量渲染
- 同一聚合内资源路径分层清晰（BU → Agent → Model/MCP/Memory）

---

## 8. 可观测性与运维设计

## 8.1 日志体系

- 启动即初始化全局日志
- 支持开发/生产两档日志级别
- 文件日志按天滚动，默认保留 7 天
- 对第三方库日志做级别收敛，减少噪音

## 8.2 健康探针

- `/health`：进程健康
- `/api/health/ready`：服务就绪
- `/`：基础可达性

## 8.3 运行状态可见性

- Agent/Model 均支持状态查询
- Agent 执行快照支持断线重连恢复
- SQL 执行历史支持计算行为审计

---

## 9. 安全设计要点

## 9.1 SQL 安全

- DuckDB SQL 支持参数化占位（`?` + `params`）
- 对查询型脚本提供语句前缀限制（避免误写入/误删除场景）

## 9.2 文件路径安全

- `get_output_file_content` 对 `relative_path` 做标准化与目录边界校验：
  - 禁止绝对路径
  - 禁止目录穿越（`..`）
  - 通过 `resolve + relative_to` 验证目标文件位于 `output` 根目录内

## 9.3 错误隔离

- API 层捕获并结构化异常，避免内部栈信息无序泄漏
- 运行时异常转换为 `ERROR` 消息包，保障流式协议闭环

---

## 10. 扩展性设计

## 10.1 LLM Provider 扩展

- 通过 `ModelRegistry` 增加 provider/model 元数据即可在前后端统一暴露
- `LLMClientFactory` 按 `model_type` 与 provider 分支构建客户端

## 10.2 Agent 能力扩展

- 技能、记忆、MCP、模型均采用目录化资源管理
- `agent_service` 提供统一增删改查与启停开关逻辑
- `agent_engine/tools` 可按工具协议持续扩展

## 10.3 Compute 扩展

- 可在 `compute_engine` 增加查询模板、权限控制、结果缓存与异步任务队列
- 可引入 SQL 语法分级策略（只读/写入/DDL）实现多级授权

---

## 11. 架构优势与当前风险

## 11.1 优势

- 模块边界清晰：控制面、运行面、计算面解耦
- 文件系统模型直观，便于本地化与调试
- SSE 流式协议完善，适配智能体执行场景
- DuckDB 本地分析能力补齐“数据计算”闭环

## 11.2 风险与改进建议

1. **DuckDB schema 兼容性**
   - 不同 DuckDB 版本 DDL 兼容差异需持续回归（例如 identity 语法差异）

2. **SQL 权限模型可加强**
   - 目前 `/sql/execute` 为通用执行入口，建议增加只读模式端点或白名单策略

3. **本地模型分支尚未完成**
   - `LLMClientFactory._create_local_client` 仍为未实现状态，建议尽快补齐

4. **测试资产中存在历史命名痕迹**
   - 部分测试描述仍出现 `catalog/schema` 旧术语，建议统一术语到 `business_unit/asset_bundle`

---

## 12. 部署与运行建议

- 使用 `run.py` 作为打包后入口，开发态可直接 `uvicorn main:app`
- 通过环境变量覆盖关键配置：
  - `LOCALBRISK_HOST`
  - `LOCALBRISK_PORT`
  - `LOCALBRISK_DEV_MODE`
  - 以及 `LOCALBRISK_` 前缀的 settings 字段
- 启动前确保：
  - `~/.localbrisk/App_Data/Catalogs` 可写
  - DuckDB 文件路径可创建
  - Agent 依赖（langchain/deepagents）可导入

---

## 13. 总结

当前后端架构已形成“**文件化配置管理 + 可流式 Agent 运行时 + 本地 DuckDB 计算**”的完整闭环，具备较强的本地部署友好性与可扩展性。后续建议重点投入在 **SQL 权限分级、本地模型支持补齐、术语统一与回归测试增强**，以进一步提升稳定性与工程一致性。
