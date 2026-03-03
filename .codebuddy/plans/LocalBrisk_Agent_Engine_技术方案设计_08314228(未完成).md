---
name: LocalBrisk Agent Engine 技术方案设计
overview: 基于 DeepAgents/LangGraph 框架，为 LocalBrisk 设计并实现一个完整的本地 Agent 引擎系统，支持用户自定义 Agent 配置、调试运行和常驻服务发布。
todos:
  - id: agent-config-models
    content: 实现 Agent 配置模型和验证器，基于 Pydantic 定义强类型配置结构
    status: pending
  - id: langgraph-integration
    content: 集成 LangGraph 引擎，实现 Agent 图构建和执行调度核心功能
    status: pending
    dependencies:
      - agent-config-models
  - id: agent-runtime-service
    content: 开发 Agent 运行时服务，包括实例管理、状态跟踪和生命周期控制
    status: pending
    dependencies:
      - langgraph-integration
  - id: debug-monitoring-system
    content: 构建调试和监控系统，实现实时日志、状态监控和性能指标收集
    status: pending
    dependencies:
      - agent-runtime-service
  - id: frontend-debug-interface
    content: 使用 [subagent:code-explorer] 分析现有前端组件模式，开发 Agent 调试和管理界面
    status: pending
    dependencies:
      - debug-monitoring-system
  - id: daemon-service-management
    content: 实现 Agent 守护进程服务，支持常驻模式运行和自动故障恢复
    status: pending
    dependencies:
      - agent-runtime-service
  - id: skill-integration-system
    content: 使用 [skill:skill-creator] 指导实现技能管理系统，支持动态技能加载和管理
    status: pending
    dependencies:
      - daemon-service-management
---

## 用户需求

基于现有的 LocalBrisk 桌面应用（Python+Tauri+Vue 架构），实现用户自定义本地 Agent 系统的完整工作流：

1. 用户基于 agent_spec_example.md 的 YAML 配置模板配置 Agent
2. 配置完成后进行调试运行，验证 Agent 功能
3. 运行测试通过后，发布为常驻服务
4. 使用 LangGraph 或 DeepAgents 作为底层 Agent 执行框架

## 产品概述

在现有 LocalBrisk 系统基础上，新增 Agent 运行时引擎模块，实现从配置、调试到部署的完整 Agent 生命周期管理。系统将支持多 Agent 协作、动态调度、技能管理等高级功能。

## 核心功能

- Agent 配置验证与解析（基于 YAML 规范）
- Agent 运行时调试环境（实时日志、状态监控）
- Agent 执行引擎（LangGraph 集成）
- Agent 服务发布与管理（常驻服务模式）
- 多 Agent 协作与动态调度
- 技能与提示词管理
- 运行状态监控与日志管理

## 技术栈选择

基于现有项目架构，复用以下技术栈：

- **后端框架**: Python FastAPI（已有完整架构）
- **Agent 引擎**: LangGraph（优先选择，生态成熟）
- **前端框架**: Vue 3 + TypeScript + Tailwind CSS + Shadcn-Vue（现有技术栈）
- **桌面框架**: Tauri 2.0 + Rust（现有架构）
- **数据处理**: Polars + DuckDB（现有依赖）
- **配置解析**: PyYAML（Python端）+ serde_yaml（Rust端）

## 实现方案

### 核心策略

在现有 `backend/agent_engine/` 模块基础上，构建完整的 Agent 运行时系统。采用分层架构：配置层（YAML解析）→ 编排层（LangGraph集成）→ 执行层（Agent运行时）→ 监控层（状态管理）。

### 关键技术决策

1. **Agent 引擎选择**: 选择 LangGraph 而非 DeepAgents，因为 LangGraph 具有更成熟的生态系统、更好的状态管理和更灵活的工作流编排能力
2. **运行模式设计**: 支持调试模式（同步执行，实时日志）和服务模式（异步执行，后台运行）两种运行模式
3. **配置验证策略**: 基于 Pydantic 模型进行 YAML 配置的强类型验证，确保配置正确性
4. **多 Agent 协作**: 利用 LangGraph 的图结构特性实现 Agent 间的动态调度和状态传递

### 实现细节

**性能优化**:

- Agent 实例采用单例模式，避免重复初始化开销
- 使用异步 I/O 处理 Agent 间通信，提升并发性能
- 实现 Agent 状态缓存机制，减少重复计算

**日志管理**:

- 复用现有的 FastAPI 日志系统，按 Agent 实例分离日志流
- 实现结构化日志输出，支持日志级别过滤和实时查看
- 避免敏感信息泄露，对输入输出进行脱敏处理

**容错设计**:

- 实现 Agent 执行的超时控制和异常恢复机制
- 支持 Agent 配置热重载，无需重启服务
- 提供 Agent 执行的回滚和重试机制

## 架构设计

### 系统架构

基于现有 LocalBrisk 架构，在 `backend/agent_engine/` 模块中实现 Agent 运行时系统：

```mermaid
graph TB
    subgraph "Frontend (Vue 3)"
        A[Agent 配置界面] --> B[调试控制台]
        B --> C[服务管理面板]
    end
    
    subgraph "Backend (FastAPI)"
        D[Agent API 层] --> E[Agent 服务层]
        E --> F[配置验证器]
        E --> G[LangGraph 引擎]
        G --> H[Agent 运行时]
        H --> I[状态管理器]
    end
    
    subgraph "Tauri Layer"
        J[文件系统访问] --> K[进程管理]
    end
    
    A --> D
    F --> J
    I --> B
```

### 模块划分

- **配置管理模块**: YAML 解析、验证、热重载
- **执行引擎模块**: LangGraph 集成、Agent 实例管理
- **调度管理模块**: 多 Agent 协作、动态路由
- **监控管理模块**: 状态跟踪、日志收集、性能监控
- **服务管理模块**: 常驻服务、生命周期管理

### 数据流设计

用户配置 YAML → 配置验证 → LangGraph 图构建 → Agent 实例化 → 执行调度 → 状态更新 → 前端展示

## 目录结构

基于现有项目结构，主要在 `backend/agent_engine/` 目录下实现新功能：

```
backend/agent_engine/
├── __init__.py                    # [MODIFY] 模块初始化，导出核心类和函数
├── core/
│   ├── __init__.py               # [NEW] 核心模块初始化
│   ├── config.py                 # [NEW] Agent 配置模型定义。基于 Pydantic 定义 AgentConfig、LLMConfig 等配置类，实现 YAML 配置的强类型验证和序列化
│   ├── exceptions.py             # [NEW] Agent 异常定义。定义 AgentConfigError、AgentExecutionError 等专用异常类，提供详细的错误信息和处理建议
│   └── types.py                  # [NEW] Agent 类型定义。定义 AgentState、ExecutionResult、AgentMessage 等核心数据结构
├── engine/
│   ├── __init__.py               # [NEW] 引擎模块初始化
│   ├── langgraph_engine.py       # [NEW] LangGraph 引擎实现。集成 LangGraph 框架，实现 Agent 图构建、状态管理和执行调度
│   ├── agent_runtime.py          # [NEW] Agent 运行时管理。实现 Agent 实例生命周期管理、执行上下文管理和资源清理
│   └── scheduler.py              # [NEW] Agent 调度器。实现多 Agent 协作调度、动态路由和负载均衡
├── services/
│   ├── __init__.py               # [NEW] 服务模块初始化
│   ├── agent_executor.py         # [NEW] Agent 执行服务。提供 Agent 执行的核心服务，包括同步/异步执行、状态跟踪和结果处理
│   ├── config_validator.py       # [NEW] 配置验证服务。实现 YAML 配置的语法验证、语义检查和兼容性验证
│   ├── debug_service.py          # [NEW] 调试服务。提供 Agent 调试功能，包括断点设置、单步执行和状态检查
│   └── daemon_service.py         # [NEW] 守护进程服务。实现 Agent 的常驻服务模式，包括自动启动、健康检查和故障恢复
├── monitoring/
│   ├── __init__.py               # [NEW] 监控模块初始化
│   ├── logger.py                 # [NEW] Agent 日志管理。实现分级日志、结构化输出和实时日志流
│   ├── metrics.py                # [NEW] 性能指标收集。收集 Agent 执行时间、内存使用、成功率等关键指标
│   └── state_tracker.py          # [NEW] 状态跟踪器。实时跟踪 Agent 执行状态、上下文变化和异常情况
└── utils/
    ├── __init__.py               # [NEW] 工具模块初始化
    ├── yaml_parser.py            # [NEW] YAML 解析工具。提供 YAML 配置文件的解析、验证和格式化功能
    └── graph_builder.py          # [NEW] 图构建工具。基于 Agent 配置构建 LangGraph 执行图的工具函数

backend/app/api/endpoints/
├── agent_runtime.py              # [NEW] Agent 运行时 API。提供 Agent 启动、停止、状态查询等运行时管理接口
└── agent_debug.py                # [NEW] Agent 调试 API。提供调试模式启动、日志查看、状态监控等调试相关接口

frontend/src/views/
├── AgentDebug.vue                # [NEW] Agent 调试界面。提供可视化的 Agent 调试环境，包括配置编辑、执行控制和日志查看
├── AgentRuntime.vue              # [NEW] Agent 运行时管理界面。展示 Agent 运行状态、性能指标和服务管理功能
└── AgentService.vue              # [NEW] Agent 服务管理界面。提供 Agent 服务的启动、停止、配置和监控功能

frontend/src/components/agent/
├── ConfigEditor.vue              # [NEW] Agent 配置编辑器。基于 CodeMirror 实现的 YAML 配置编辑器，支持语法高亮和实时验证
├── ExecutionConsole.vue          # [NEW] 执行控制台。实时显示 Agent 执行日志、状态变化和调试信息
├── StateMonitor.vue              # [NEW] 状态监控组件。可视化展示 Agent 执行状态、性能指标和系统健康状况
└── ServicePanel.vue              # [NEW] 服务管理面板。提供 Agent 服务的启动、停止、重启和配置管理功能
```

## 关键代码结构

### Agent 配置模型

```python
# backend/agent_engine/core/config.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentLLMConfig(BaseModel):
    llm_model: str = Field(..., description="LLM 模型名称")
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(2000, gt=0)
    response_format: str = Field("text", pattern="^(text|json_object)$")

class AgentConfig(BaseModel):
    baseinfo: Dict[str, Any]
    llm_config: AgentLLMConfig
    instruction: Dict[str, Any]
    routing: Dict[str, Any]
    capabilities: Dict[str, Any]
    governance: Dict[str, Any]
```

### Agent 执行接口

```python
# backend/agent_engine/services/agent_executor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

class AgentExecutor(ABC):
    @abstractmethod
    async def execute(self, agent_config: AgentConfig, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent"""
        pass
    
    @abstractmethod
    async def debug_execute(self, agent_config: AgentConfig, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """调试模式执行 Agent"""
        pass
```

## 推荐的代理扩展

### SubAgent

- **code-explorer**
- 目的：深入探索现有代码库结构，分析 Agent 服务的集成点和依赖关系
- 预期结果：识别现有服务模式、API 设计规范和最佳实践，确保新增 Agent 功能与现有架构无缝集成

### Skill

- **skill-creator**
- 目的：指导创建 Agent 技能开发和管理的专用技能模块
- 预期结果：建立标准化的技能创建、验证和集成流程，支持用户自定义技能的动态加载