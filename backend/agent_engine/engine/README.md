# `agent_engine/engine` 设计说明

## 1. 目录定位

`backend/agent_engine/engine` 是 **Agent 运行时装配层**。

当前这层已经刻意收口为一条很直接的主链：

- 从 Agent 目录读取配置；
- 把配置整理成统一的 `AgentBuildContext`；
- 基于 `OpenAI Agents SDK` 组装 Agent；
- 给 Agent 挂上当前需要的 tools 和 handoffs；
- 把构建结果交给上层 `AgentRuntimeService` 管理生命周期。

这里不再承担虚拟 workspace、旧引擎兼容、额外 backend 抽象等复杂职责。

---

## 2. 当前设计目标

这层代码当前重点追求三件事：

- **简单**：减少无效抽象，尽量让构建链路一眼能看懂；
- **集中**：把 `OpenAI Agents SDK` 相关逻辑收敛到少数模块；
- **可维护**：让 tools、handoffs、模型配置的接入边界足够清楚。

---

## 3. 目录结构与职责

### `openai_agents_engine.py`

这是当前的**核心运行时引擎**。

主要职责：

- 检查 `agents` 包是否可用；
- 调用 `load_agent_context()` 读取运行时上下文；
- 调用 `build_openai_model_bundle()` 把 YAML 模型配置转换为 SDK model；
- 调用 `build_builtin_tools(agent_path=...)` 构建内建工具；
- 调用 `OpenAIToolAdapter.adapt_tools()` 转成 SDK `FunctionTool`；
- 调用 `build_openai_skills()` 把 `skills` 构造成 skill agent tools；
- 调用 `build_openai_handoffs()` 构建 SDK handoff Agent；
- 创建 SDK `Agent`，并包装成 `OpenAIAgentRuntime`；
- 管理 SQLite session 与少量 runtime 资源清理。

现在这层已经**不再创建 `workspace_backend`**，本地文件工具直接绑定 `agent_path` 工作。

### `agent_context_loader.py`

这是**运行时无关的上下文装配器**，负责把 Agent 目录中的离散配置整理成 `AgentBuildContext`。

主要职责：

- 解析 `agent_spec.yaml`；
- 读取 `models/` 下模型配置；
- 解析启用的 memories 与 skills；
- 确保 `output/` 目录存在；
- 读取 business unit 级别的 asset bundle 配置；
- 计算配置指纹 `compute_agent_context_fingerprint()`，供上层做热重载判断。

### `handoff_registry.py`

负责把 built-in subagent 定义转换成 `OpenAI Agents SDK` handoff Agent。

当前做的事情很直接：

- 从 `subagents/registry.py` 拿到标准化 subagent 定义；
- 必要时把 subagent tools 转成 SDK tools；
- 创建 handoff 用的 SDK `Agent` 列表。

这里已经删掉了无实际价值的 `parent_backend` 透传参数。

### `subagents/`

这里是**内建子代理定义层**。

当前 registry 的职责很单纯：

- 维护可扩展的 builder 列表；
- 让每个 builder 返回统一结构的 subagent definition；
- 再由 handoff 层转成 SDK Agent。

目前内建示例里包含 `data_analysis_agent`，主要服务于 Text2SQL / 数据分析场景。

### `__init__.py`

负责导出 engine 层公共入口，屏蔽内部实现细节。

---

## 4. 当前核心调用链

```text
AgentRuntimeService
  -> get_openai_agents_engine()
  -> OpenAIAgentsEngine.build_agent()
      -> load_agent_context()
      -> build_openai_model_bundle()
      -> build_builtin_tools(agent_path=...)
      -> OpenAIToolAdapter.adapt_tools()
      -> build_openai_handoffs()
      -> Agent(...)
      -> OpenAIAgentRuntime
```

这条链路现在比之前更短：

- **没有 `workspace_factory.py`**；
- **没有 `workspace_service.py`**；
- **没有虚拟路径解析链**；
- **没有多余的 backend 透传参数**。

---

## 5. `OpenAI Agents SDK` 在这里怎么用

### 5.1 SDK 依赖检查

以下模块会动态 import `agents` 包：

- `openai_agents_engine.py`
- `handoff_registry.py`
- `tools/openai_tool_adapter.py`
- `llm/provider_adapter.py`

这样可以把依赖检查集中处理，并在缺依赖时返回更明确的错误。

### 5.2 模型接入方式

模型接入位于 `llm/provider_adapter.py`。

当前使用到的 SDK 类型主要有：

- `AsyncOpenAI`
- `OpenAIChatCompletionsModel`
- `ModelSettings`

处理流程：

1. 从 `agent_spec.yaml` 与 `models/*.yaml` 找到 active model；
2. 读取 `model_id`、`endpoint_provider`、`api_base_url`、`temperature`、`max_tokens`；
3. 创建 SDK client 和 SDK model；
4. 返回 `OpenAIModelBundle` 给 engine 使用。

### 5.3 Agent 构建方式

`OpenAIAgentsEngine.build_agent()` 最终会创建 SDK `Agent`。

核心组装项包括：

- `name`
- `instructions`
- `model`
- `tools`
- `model_settings`
- `handoffs`

其中 `instructions` 来自以下几部分：

- `instruction`（纯字符串模板，支持 `{{agent_name}}`/`{{agent_path}}`/`{{now}}` 变量渲染）；
- `baseinfo.description`；
- asset bundle 简要提示；
- memory 内容（自动加载 `memories/*.md`）；
- 工具使用约束。

skill 不再直接参与这里的 `instructions` 拼装，而是通过独立 skill agent 进入 `tools` 集合。

### 5.4 Tool 接入方式

工具接入现在也被简化了。

当前模式是：

- runtime 在构建时直接把 `agent_path` 传给工具工厂；
- 本地文件工具直接基于这个 `agent_path` 解析相对路径；
- 然后统一由 `OpenAIToolAdapter` 转换成 SDK `FunctionTool`。

也就是说，现在不再需要：

- `workspace_backend`
- `WorkspaceService`
- 虚拟挂载路径解析

### 5.5 Handoff 接入方式

`handoff_registry.py` 会把 built-in subagent 定义转成 SDK `Agent`，再作为父 Agent 的 `handoffs` 传入。

设计重点是：

- handoff 复用当前 subagent registry；
- 子代理工具也走同一套 tool 适配逻辑；
- handoff 只保留真正参与构建的参数。

### 5.6 Session 与执行方式

`OpenAIAgentRuntime` 对 SDK 的运行做了统一包装，主要负责：

- `Runner.run()`
- `Runner.run_streamed()`
- `SQLiteSession`

session 默认保存在：

- `output/.openai_sessions.sqlite`

---

## 6. 配置文件如何影响运行时

当前最关键的运行时输入包括：

- `agent_spec.yaml`
- `models/*.yaml`
- `memories/*.md`
- `skills/*/SKILL.md`
- `skills/*/*.yaml`

`agent_context_loader.compute_agent_context_fingerprint()` 会把这些关键配置纳入指纹；
上层 `AgentRuntimeService` 再据此判断是否需要重建 runtime。

所以这层天然支持：

- **配置修改后热重载**；
- **无需重启应用即可让新配置生效**。

---

## 7. 现在删掉了什么，为什么删

这轮简化里，主要删掉了几类低价值代码：

- **`default_prompt.py`**：不再单独维护默认 prompt 模块，改为在 `AgentService` 中直接生成最小默认 `AGENTS.md`；
- **`workspace_factory.py` / `workspace_service.py`**：不再为本地文件工具维护一层虚拟文件系统抽象；
- **`path_resolver.py`**：随着虚拟路径链路移除，这层辅助解析也没有保留价值；
- **`parent_backend` 透传参数**：从 handoff/subagent 构建链路中删除未使用字段。

这些删除的核心目的只有一个：**让运行时主链更短、更直接、更容易理解。**

---

## 8. 扩展建议

### 新增一个运行时工具

推荐路径：

1. 在 `tools/` 中新增工具；
2. 让工具满足当前运行时工具约定（如 `name`、`description`、`args_schema`、`_run/_arun`）；
3. 在 `build_builtin_tools()` 中接入；
4. 由 `OpenAIToolAdapter` 自动转成 SDK tool。

### 新增一个 skill

推荐路径：

1. 在 `skills/<skill_name>/` 下放置 `SKILL.md`；
2. 如需更好的展示名或 tool 描述，可补充同目录 YAML；
3. 在 `agent_spec.yaml -> skills` 列表中声明该 skill；
4. runtime 会自动把它构造成 skill agent，并通过 `Agent.as_tool()` 暴露给主 Agent。

### 新增一个 handoff 子代理

推荐路径：

1. 在 `subagents/registry.py` 中新增 builder；
2. 返回稳定的 subagent definition；
3. 让 `handoff_registry.py` 自动转成 SDK handoff Agent。

### 新增运行时配置来源

- 如果是**运行时真正依赖的数据**，优先接到 `agent_context_loader.py`；
- 如果是**展示/管理视图需要的数据**，优先接到 `agent_service.py`。

---

## 9. 最小使用示例

```python
from agent_engine.engine.openai_agents_engine import get_openai_agents_engine

engine = get_openai_agents_engine()
runtime = await engine.build_agent(
    agent_path="/path/to/business_unit/agents/demo_agent",
    business_unit_id="demo_unit",
)

result = await runtime.run("Hello")
stream = await runtime.run_streamed("Please analyze this file")
```

如果需要完整的生命周期管理，更推荐通过 `AgentRuntimeService` 使用，因为它还负责：

- 缓存复用；
- 配置变更检测；
- 热重载；
- 流式事件适配；
- 会话历史管理；
- 资源回收。

---

## 10. 一句话总结

现在的 `engine/` 重点不再是“把很多抽象叠在一起”，而是把 **Agent 目录配置 -> OpenAI SDK Agent -> 可托管 runtime** 这条链路尽量做短，让上层只关心加载、执行、重载和卸载。