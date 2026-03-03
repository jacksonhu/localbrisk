# DeepAgents SDK 使用指南

> 基于 LangChain 的深度 Agent 框架使用方法总结

## 1. 概述

### 1.1 什么是 DeepAgents

DeepAgents 是 LangChain 推出的一个**开箱即用的智能代理框架**，它是一个基于 LangGraph 构建的 Agent 框架，提供了一套完整的 Agent 开发工具集，主要特点包括：

- **Planning（规划）** — 通过 `write_todos` / `read_todos` 工具进行任务分解和进度跟踪
- **Filesystem（文件系统）** — 提供 `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep` 等文件操作工具
- **Shell access（Shell 访问）** — 通过 `execute` 工具运行命令（支持沙箱环境）
- **Sub-agents（子代理）** — 通过 `task` 工具委派工作，实现隔离的上下文窗口
- **Smart defaults（智能默认值）** — 预设的 Prompts 教导模型如何有效使用这些工具
- **Context management（上下文管理）** — 对话过长时自动摘要，大输出保存到文件

### 1.2 核心理念

DeepAgents 的核心设计理念是通过以下四个方面让 Agent 能够处理更复杂、更长周期的任务：

1. **规划工具** - 让 Agent 能够分解和追踪复杂任务
2. **子代理** - 隔离上下文，处理独立的子任务
3. **文件系统访问** - 持久化中间结果和上下文
4. **详细的 Prompt 模板** - 指导 Agent 有效使用工具

## 2. 快速开始

### 2.1 安装

```bash
pip install deepagents
# 或使用 uv
uv add deepagents
```

### 2.2 最简示例

```python
from deepagents import create_deep_agent

# 使用默认配置创建 Agent
agent = create_deep_agent()

# 调用 Agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Research LangGraph and write a summary"}]
})
```

### 2.3 依赖说明

DeepAgents 的核心依赖包括：
- `langchain-core>=1.2.7`
- `langchain>=1.2.7`
- `langchain-anthropic>=1.3.1` (默认模型)
- `langchain-google-genai>=4.2.0` (可选 Gemini 支持)

## 3. API 详解

### 3.1 `create_deep_agent()` 函数

这是创建 DeepAgent 的主要入口函数：

```python
def create_deep_agent(
    model: str | BaseChatModel | None = None,              # 模型配置
    tools: Sequence[BaseTool | Callable | dict] | None = None,  # 自定义工具
    *,
    system_prompt: str | SystemMessage | None = None,      # 系统提示
    middleware: Sequence[AgentMiddleware] = (),            # 中间件
    subagents: list[SubAgent | CompiledSubAgent] | None = None,  # 子代理列表
    skills: list[str] | None = None,                       # 技能路径列表
    memory: list[str] | None = None,                       # 记忆文件路径列表
    response_format: ResponseFormat | None = None,         # 响应格式
    context_schema: type[Any] | None = None,               # 上下文 Schema
    checkpointer: Checkpointer | None = None,              # 检查点保存器
    store: BaseStore | None = None,                        # 持久化存储
    backend: BackendProtocol | BackendFactory | None = None,  # 文件系统后端
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,  # 人工审核配置
    debug: bool = False,                                    # 调试模式
    name: str | None = None,                                # Agent 名称
    cache: BaseCache | None = None,                         # 缓存
) -> CompiledStateGraph
```

#### 参数详解

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | `str \| BaseChatModel` | 使用的 LLM 模型，默认 `claude-sonnet-4-5-20250929`。支持 `provider:model` 格式快速切换 |
| `tools` | `Sequence[BaseTool]` | 自定义工具列表，会与内置工具合并使用 |
| `system_prompt` | `str \| SystemMessage` | 自定义系统提示，会与基础提示拼接 |
| `middleware` | `Sequence[AgentMiddleware]` | 额外的中间件，在标准中间件栈之后应用 |
| `subagents` | `list[SubAgent]` | 子代理配置列表 |
| `skills` | `list[str]` | 技能目录路径列表（使用 POSIX 路径格式） |
| `memory` | `list[str]` | AGENTS.md 记忆文件路径列表 |
| `backend` | `BackendProtocol` | 文件存储后端，支持多种实现 |
| `interrupt_on` | `dict[str, bool]` | 配置需要人工审核的工具 |

### 3.2 内置工具说明

DeepAgents 默认提供以下工具：

| 工具名 | 功能 | 说明 |
|--------|------|------|
| `write_todos` | 任务管理 | 创建和管理待办事项列表 |
| `read_todos` | 任务查看 | 读取当前待办事项状态 |
| `ls` | 列出目录 | 列出指定目录下的文件 |
| `read_file` | 读取文件 | 支持分页读取大文件 |
| `write_file` | 写入文件 | 创建新文件 |
| `edit_file` | 编辑文件 | 精确字符串替换 |
| `glob` | 文件搜索 | 使用 glob 模式搜索文件 |
| `grep` | 内容搜索 | 搜索文件内容中的文本 |
| `execute` | 执行命令 | 在沙箱环境执行 shell 命令 |
| `task` | 子代理调用 | 委派任务给子代理 |

## 4. 核心概念

### 4.1 子代理（SubAgents）

子代理是 DeepAgents 的核心特性之一，用于处理复杂的多步骤任务。

#### SubAgent 配置

```python
from typing import TypedDict

class SubAgent(TypedDict):
    name: str                    # 唯一标识符
    description: str             # 功能描述（用于主代理决策）
    system_prompt: str           # 子代理的系统提示
    tools: NotRequired[list]     # 可选：子代理专用工具
    model: NotRequired[str]      # 可选：使用不同的模型
    middleware: NotRequired[list] # 可选：额外中间件
    interrupt_on: NotRequired[dict] # 可选：人工审核配置
```

#### 使用示例

```python
from deepagents import create_deep_agent

# 定义研究子代理
research_agent = {
    "name": "research-agent",
    "description": "用于深度研究复杂主题，每次只处理一个主题",
    "system_prompt": "你是一个专业的研究员，善于深入分析问题...",
    "tools": [tavily_search, think_tool],
}

# 定义代码审查子代理
code_reviewer = {
    "name": "code-reviewer",
    "description": "用于审查代码质量和安全性",
    "system_prompt": "你是一个资深代码审查员...",
}

# 创建带子代理的主代理
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-5-20250929",
    subagents=[research_agent, code_reviewer],
)
```

#### 子代理使用场景

- **并行研究任务**：多个研究员同时研究不同主题
- **隔离上下文**：防止主线程上下文过载
- **专业化分工**：不同子代理处理不同领域任务
- **复杂任务分解**：将大任务拆分为独立的小任务

### 4.2 技能系统（Skills）

技能系统实现了**渐进式披露**模式，主代理只看到技能的名称和描述，完整指令仅在需要时加载。

#### 技能目录结构

```
/skills/
├── query-writing/
│   └── SKILL.md          # 必需：包含 YAML frontmatter
└── schema-exploration/
    └── SKILL.md
```

#### SKILL.md 格式

```markdown
---
name: query-writing
description: 用于编写和执行 SQL 查询 - 从简单单表查询到复杂的多表 JOIN
license: MIT
---

# Query Writing Skill

## When to Use This Skill
使用此技能来回答需要编写 SQL 查询的问题...

## Workflow
1. 识别需要的表
2. 获取表结构
3. 编写查询
4. 执行并格式化结果
```

#### 使用技能

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-5-20250929",
    skills=["./skills/"],  # 技能目录路径
    backend=FilesystemBackend(root_dir="/path/to/project")
)
```

### 4.3 记忆系统（Memory）

记忆系统通过 `AGENTS.md` 文件为 Agent 提供持久化的上下文和指令。

#### AGENTS.md 示例

```markdown
# Text-to-SQL Agent Instructions

You are a Deep Agent designed to interact with a SQL database.

## Your Role
1. 探索可用的数据库表
2. 检查相关表的 Schema
3. 生成语法正确的 SQL 查询
4. 执行查询并分析结果

## Safety Rules
**NEVER execute these statements:**
- INSERT, UPDATE, DELETE, DROP, ALTER
```

#### 使用记忆

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-5-20250929",
    memory=["./AGENTS.md"],  # 记忆文件路径
    backend=FilesystemBackend(root_dir="./")
)
```

### 4.4 后端系统（Backends）

DeepAgents 提供多种文件存储后端：

| 后端类型 | 说明 | 使用场景 |
|----------|------|----------|
| `StateBackend` | 临时存储在 Agent 状态中 | 默认，无持久化需求 |
| `FilesystemBackend` | 真实文件系统存储 | 需要持久化文件，支持 `virtual_mode` 参数 |
| `StoreBackend` | LangGraph Store 存储 | 跨会话持久化 |
| `CompositeBackend` | 组合多个后端 | 混合存储策略 |

> **注意**: `FilesystemBackend(virtual_mode=False)` 提供真实文件系统访问（读写），`virtual_mode=True` 提供虚拟只读访问。

#### 后端使用示例

```python
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend

# 使用文件系统后端（真实读写）
backend = FilesystemBackend(root_dir="/workspace", virtual_mode=False)

# 使用虚拟模式（只读）
readonly_backend = FilesystemBackend(root_dir="/docs", virtual_mode=True)

# 使用组合后端（临时 + 持久化）
backend = CompositeBackend(
    default=StateBackend(),
    routes={"/memories/": StoreBackend()}
)

agent = create_deep_agent(backend=backend)
```

## 5. 中间件系统

### 5.1 内置中间件

DeepAgents 默认使用以下中间件栈：

1. `TodoListMiddleware` - 待办事项管理
2. `MemoryMiddleware` - 记忆加载（如配置）
3. `SkillsMiddleware` - 技能加载（如配置）
4. `FilesystemMiddleware` - 文件系统工具
5. `SubAgentMiddleware` - 子代理支持
6. `SummarizationMiddleware` - 自动摘要（防止上下文溢出）
7. `AnthropicPromptCachingMiddleware` - Prompt 缓存
8. `PatchToolCallsMiddleware` - 工具调用修补

### 5.2 自定义中间件

```python
from langchain.agents.middleware.types import AgentMiddleware

class CustomMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        # 在模型调用前后执行自定义逻辑
        return handler(request)

agent = create_deep_agent(
    middleware=[CustomMiddleware()]
)
```

## 6. 实战示例

### 6.1 深度研究 Agent

```python
from datetime import datetime
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# 定义研究子代理
research_sub_agent = {
    "name": "research-agent",
    "description": "深度研究子代理，一次只处理一个研究主题",
    "system_prompt": f"""你是一个专业研究员。
当前日期: {datetime.now().strftime('%Y-%m-%d')}

研究指南：
1. 使用 tavily_search 进行网络搜索
2. 每次搜索后使用 think_tool 进行战略反思
3. 简单查询最多 2-3 次搜索
4. 复杂查询最多 5 次搜索
""",
    "tools": [tavily_search, think_tool],
}

# 创建主研究 Agent
agent = create_deep_agent(
    model=init_chat_model("anthropic:claude-sonnet-4-5-20250929", temperature=0.0),
    tools=[tavily_search, think_tool],
    system_prompt="""你是一个研究编排者。
    
研究工作流程：
1. 保存用户的研究请求
2. 使用 write_todos 规划研究步骤
3. 委派研究任务给子代理（最多并行 3 个）
4. 综合子代理的研究结果
5. 向用户呈现最终报告
""",
    subagents=[research_sub_agent],
)

# 执行研究
result = agent.invoke({
    "messages": [{
        "role": "user", 
        "content": "研究量子计算的最新进展及其对密码学的影响"
    }]
})
```

### 6.2 Text-to-SQL Agent

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

# 连接数据库
db = SQLDatabase.from_uri("sqlite:///chinook.db", sample_rows_in_table_info=3)

# 初始化模型
model = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0)

# 创建 SQL 工具集
toolkit = SQLDatabaseToolkit(db=db, llm=model)
sql_tools = toolkit.get_tools()

# 创建 Agent
agent = create_deep_agent(
    model=model,
    memory=["./AGENTS.md"],           # Agent 身份和指令
    skills=["./skills/"],              # SQL 相关技能
    tools=sql_tools,                   # SQL 工具
    backend=FilesystemBackend(root_dir="./")
)

# 执行查询
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "哪位员工创造的收入最多？按国家分析"
    }]
})
```

### 6.3 自定义模型

```python
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent

# 方式1: 使用 provider:model 格式
agent = create_deep_agent(
    model="openai:gpt-4o"
)

# 方式2: 使用 init_chat_model
model = init_chat_model(model="anthropic:claude-sonnet-4-5-20250929", temperature=0.0)
agent = create_deep_agent(model=model)

# 方式3: 使用 Google Gemini
model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")
agent = create_deep_agent(model=model)
```

### 6.4 人工介入审核

```python
from deepagents import create_deep_agent

# 配置需要人工审核的工具
agent = create_deep_agent(
    interrupt_on={
        "edit_file": True,      # 编辑文件前暂停
        "execute": True,        # 执行命令前暂停
    },
    checkpointer=checkpointer  # 需要配置 checkpointer
)
```

## 7. 高级用法

### 7.1 流式输出

```python
# DeepAgent 返回的是 LangGraph CompiledStateGraph
# 支持 LangGraph 的所有特性

for event in agent.stream({
    "messages": [{"role": "user", "content": "..."}]
}):
    print(event)
```

### 7.2 与 LangGraph Studio 集成

DeepAgents 完全兼容 LangGraph 生态，可以：
- 使用 LangGraph Studio 可视化调试
- 使用 Checkpointer 进行状态持久化
- 部署到 LangGraph Server

### 7.3 MCP 支持

DeepAgents 支持通过 `langchain-mcp-adapters` 使用 MCP 工具：

```python
# 参考 langchain-mcp-adapters 文档集成 MCP 工具
from langchain_mcp_adapters import MCPToolkit

# 将 MCP 工具添加到 Agent
agent = create_deep_agent(
    tools=mcp_toolkit.get_tools()
)
```

## 8. 最佳实践

### 8.1 Agent 设计原则

1. **明确任务分解**：复杂任务使用 `write_todos` 规划
2. **合理使用子代理**：独立、上下文密集的任务委派给子代理
3. **技能渐进披露**：只在需要时加载详细技能指令
4. **持久化中间结果**：使用文件系统保存重要的中间状态

### 8.2 子代理使用指南

**应该使用子代理的场景：**
- 复杂的多步骤任务
- 独立且可并行的任务
- 需要集中推理或大量 token 的任务
- 只关心最终结果而非中间步骤

**不应使用子代理的场景：**
- 简单的几步操作
- 需要查看中间推理过程
- 拆分会增加延迟而无益处

### 8.3 Prompt 设计建议

1. **清晰的角色定义**：在 AGENTS.md 中明确 Agent 的角色和职责
2. **具体的工作流程**：在技能文件中描述详细的步骤
3. **安全规则**：明确禁止的操作（如 DML 语句）
4. **示例驱动**：提供具体的使用示例

## 9. 常见问题

### Q1: 如何处理长上下文？
DeepAgents 内置 `SummarizationMiddleware`，当对话过长时会自动进行摘要。你也可以通过子代理隔离上下文。

### Q2: 如何添加自定义工具？
```python
from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """自定义工具描述"""
    return "result"

agent = create_deep_agent(tools=[my_custom_tool])
```

### Q3: 如何调试 Agent？
1. 设置 `debug=True`
2. 集成 LangSmith 追踪
3. 使用 LangGraph Studio 可视化

### Q4: 支持哪些模型？
支持所有 LangChain 兼容的 LLM，包括：
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- 以及其他 LangChain 支持的模型

## 10. 参考资源

- [DeepAgents 官方文档](https://docs.langchain.com/oss/python/deepagents/overview)
- [API 参考](https://reference.langchain.com/python/deepagents/)
- [GitHub 仓库](https://github.com/langchain-ai/deepagents)
- [LangGraph 文档](https://docs.langchain.com/oss/python/langgraph/overview)
- [示例项目](https://github.com/langchain-ai/deepagents/tree/main/examples)

---

*本文档基于 DeepAgents v0.3.9 编写*
