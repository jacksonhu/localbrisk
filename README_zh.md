# LocalBrisk — 你的电脑，就是一个 Agent 公司

<p align="center">
  <strong>🚀 项目初创，快速迭代中 — 寻找首批共建者，一起定义本地 AI 的未来</strong>
</p>

[English](README.md) | **中文** | [Development Guide](DEVELOPMENT.md) | [开发指南](DEVELOPMENT_zh.md)

> **Local-First, Privacy-Safe — 把你的笔记本变成一家全自主运转的 AI 智能体公司。**

LocalBrisk 是一款跨平台桌面工作站，让你在**自己的设备上**构建、编排并运行 AI 智能体。通过**本体建模（Ontology Modeling）**，它将本地文件、云端数据库与领域知识统一为一张语义图谱，供智能体推理调用。数据不出设备、无需云端依赖——一个应用，让你的电脑化身为自治的 AI 组织。
![LocalBrisk Overview](./img.png)
### 为什么选择 LocalBrisk？

- **本地 Agent 运行沙箱**：每个 Agent 在完全隔离的本地沙箱中运行（独立 venv + 文件系统后端 + 工具权限边界），代码执行和数据处理**永不离开你的设备**。
- **本地文件 & 远程数据联邦分析**：本地敏感文件（Parquet / CSV / Excel）与远程数据库（MySQL / PostgreSQL）统一纳入同一 AssetBundle，Agent 通过联邦虚拟文件系统原地查询——**无需将任何本地文件上传到云端**。
- **本地数据 & 云端数据一体的本体建模**：在一份 `ontology.yaml` 中统一描述本地文件和云端数据源之间的关系与动作，Agent 基于完整的知识图谱进行推理——**不区分数据的物理位置**。
- **配置即代码，天然 Git 友好**：所有 Agent 定义、本体模型、记忆提示词、技能包和资产配置都是 `~/.localbrisk/App_Data/Catalogs/` 下的**纯 YAML / Markdown 文件**。没有数据库，没有私有格式——你可以直接 `git init`，进行版本管理、分支开发，并通过任何 Git 托管服务在团队间共享。
- **你的电脑，就是一个 Agent 公司**：每个 BusinessUnit 代表一个业务单元；在其中，多个 Agent 扮演不同角色——数据分析师、研究助理、代码审查员、运维监控员。你的一台本地电脑就是一个**自治的 AI 智能体组织**，专业化的 Agent 们协同工作、通过同一套本体共享数据资产、执行跨职能工作流——全部在本地完成，无需云端。

### 业务场景：电商公司 Agent 组织

> 你的电脑就是一个 **Agent 公司**。你是 **CEO**——通过自然语言指挥每个部门、管理数字资产、编排跨部门工作流。
```
🖥️ WORKSPACE（你 = CEO）
│
├── 📁 Market_sales                          ── 事业部：销售与营销部
│   ├── 🤖 Sales_analyst                     ── Agent：分析订单与客户数据
│   │   ├── 📁 Skills        (sql_gen, report_builder)
│   │   ├── 📁 Memories       (sales_playbook.md, kpi_definitions.md)
│   │   ├── 📁 Models         (deepseek-chat ✅, gpt-4o)
│   │   ├── 📁 MCPs           (web_search, python_executor)
│   │   └── 📁 output/        ← 沙箱工作空间（隔离）
│   ├── 🤖 Ad_optimizer                      ── Agent：优化广告投放与 ROI
│   │   ├── 📁 Skills        (ab_test, channel_analysis)
│   │   ├── 📁 Memories       (campaign_history.md)
│   │   ├── 📁 Models         (qwen-max ✅)
│   │   └── 📁 output/        ← 沙箱工作空间
│   ├── 🗄️ sales_db          🔌 external     ── 资产包：MySQL 远程数据库
│   │   ├── 📊 orders                         （同步的表元数据）
│   │   ├── 📊 customers
│   │   ├── 📊 products
│   │   └── 📄 ontology.yaml                  （外键: orders→customers，派生: monthly_revenue）
│   └── 🗄️ marketing_docs       local        ── 资产包：本地文件
│       ├── 📂 campaigns/                      （PDF/PPT 投放方案）
│       ├── 📂 competitor_reports/             （Excel/CSV 市场数据）
│       └── 📊 ad_spend.csv
│
├── 📁 Supply_chain                          ── 事业部：供应链部
│   ├── 🤖 Inventory_mgr                     ── Agent：需求预测与库存管理
│   │   ├── 📁 Skills        (forecast, reorder_alert)
│   │   ├── 📁 Models         (deepseek-chat ✅)
│   │   └── 📁 output/        ← 沙箱工作空间
│   ├── 🤖 Logistics_bot                     ── Agent：物流追踪与路线优化
│   │   ├── 📁 Skills        (tracking, route_calc)
│   │   └── 📁 output/        ← 沙箱工作空间
│   ├── 🗄️ warehouse_db      🔌 external     ── 资产包：PostgreSQL 远程仓储数据库
│   │   ├── 📊 inventory
│   │   ├── 📊 sku_master
│   │   └── 📄 ontology.yaml                  （外键: inventory→sku_master）
│   └── 🗄️ shipping_docs        local        ── 资产包：本地合同与路线
│       ├── 📂 contracts/                      （PDF 供应商合同）
│       └── 📊 routes.parquet
│
├── 📁 Finance                               ── 事业部：财务部
│   ├── 🤖 Finance_analyst                   ── Agent：损益分析与财务报表
│   │   ├── 📁 Skills        (pivot_table, trend_analysis)
│   │   ├── 📁 Models         (gpt-4o ✅)
│   │   └── 📁 output/        ← 沙箱工作空间
│   ├── 🤖 Tax_assistant                     ── Agent：税务计算与发票处理
│   │   ├── 📁 Skills        (tax_calc, invoice_ocr)
│   │   └── 📁 output/        ← 沙箱工作空间
│   ├── 🗄️ accounting_db     🔌 external     ── 资产包：MySQL 财务数据库
│   │   ├── 📊 general_ledger
│   │   ├── 📊 accounts_payable
│   │   ├── 📊 accounts_receivable
│   │   └── 📄 ontology.yaml                  （派生: monthly_pnl ← 总账分录）
│   └── 🗄️ tax_docs             local        ── 资产包：本地税务文档
│       ├── 📂 invoices/                       （扫描的发票 PDF）
│       └── 📊 tax_rates.csv
│
└── 🔧 共享基础设施（不在树中显示，但驱动一切）
├── DuckDB 计算引擎                        （跨事业部 SQL 分析）
├── LLM 模型网关                           （OpenAI / DeepSeek / 本地模型）
└── Git 版本化 Catalogs/                   （所有配置 = 纯 YAML/MD 文件）
```

| 概念 | 在 LocalBrisk 中 | 在本场景中 |
|------|------------------|-----------|
| **你** | WORKSPACE 运营者 | CEO——用自然语言指挥所有部门 |
| **BusinessUnit** | 顶层组织文件夹 | 部门：销售、供应链、财务 |
| **Agent** | 拥有独立沙箱的 AI 员工 | 角色：销售分析师、库存管理员、税务助手… |
| Agent 子资源 | Skills / Memories / Models / MCPs / output | 每个 Agent 的能力、知识、模型配置和隔离工作空间 |
| **AssetBundle** | 数据资产集合 | 部门数据：远程数据库表（🗄️ external）+ 本地文件（📂 local） |
| **Ontology** | 每个 bundle 内的 `ontology.yaml` | 资产间的语义关系与可执行动作 |

**要点说明：**
- **你 = CEO**：点击任意 Agent 打开 Chat 窗口，用自然语言指挥它查询数据、生成报告、触发动作——无需编码。
- **BusinessUnit = 部门**：每个事业部是一个组织边界，拥有独立的员工（Agent）和数据（AssetBundle）。
- **Agent = 员工角色**：每个 Agent 拥有专属的技能、记忆和模型——如同聘请了一位领域专家。
- **联邦数据**：外部资产包（远程数据库）与本地资产包（你的文件）并列共存——Agent 原地查询两者，**数据零上传**。
- **沙箱隔离**：每个 Agent 的 `output/` 是私有工作空间，共享资产以只读方式挂载。
- **本体贯穿一切**：`ontology.yaml` 定义表间关系、数据血缘和可执行动作——Agent 在完整图谱上推理。

---

## 产品定位

| 关键词 | 说明 |
|--------|------|
| **完全本地化** | 数据物理隔离，模型可本地推理，隐私零风险 |
| **本地 Agent 沙箱** | 每个 Agent 在隔离沙箱中运行（venv + CompositeBackend），代码执行和文件 I/O 不出设备 |
| **联邦分析** | 本地文件与远程数据库联合查询——敏感数据无需上传云端 |
| **一体化本体建模** | 一份语义模型横跨本地 & 云端资产，Agent 在完整知识图谱上推理 |
| **统一资产管理** | 通过 BusinessUnit → Agent / AssetBundle → 叶子资产 的三层架构，统一组织数据、知识与智能体 |
| **一键安装可用** | 极简安装包，内置轻量化推理引擎，无需配置复杂环境 |
| **多模型支持** | 同时支持 OpenAI / Claude / 通义千问 / DeepSeek / Gemini / 智谱 / Moonshot 等 API，以及本地模型 |
| **智能体即服务** | 每个 Agent 拥有独立的 Memory、Skill、Model、MCP(Tool)，支持流式对话与多步推理 |
| **本地 Agent 公司** | 每个 BusinessUnit 是一个业务组织，多个角色化 Agent 协同——你的电脑就是一个自治 AI 公司 |

---

## 技术架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户桌面 (macOS / Windows / Linux)           │
│                                                                  │
│  ┌──────────────┐   Tauri IPC   ┌──────────────┐               │
│  │  Vue 3 前端   │◄────────────►│  Rust Tauri   │               │
│  │  :1420        │              │  主进程        │               │
│  └──────┬───────┘              └──────┬───────┘               │
│         │ HTTP / SSE                   │ Sidecar spawn/kill     │
│         ▼                              ▼                        │
│  ┌─────────────────────────────────────────────┐               │
│  │           Python FastAPI 后端  :8765          │               │
│  │  ┌───────────┐ ┌───────────┐ ┌────────────┐ │               │
│  │  │ 业务服务层  │ │Agent 引擎  │ │ 计算引擎    │ │               │
│  │  │ (CRUD)    │ │(LangGraph) │ │ (DuckDB)   │ │               │
│  │  └───────────┘ └───────────┘ └────────────┘ │               │
│  └─────────────────────────────────────────────┘               │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────┐               │
│  │   ~/.localbrisk/App_Data/Catalogs/ (文件系统) │  ◄── 纯文件   │
│  │     ├── {bu}/agents/       (YAML + MD)        │    天然 Git   │
│  │     ├── {bu}/asset_bundles/ (YAML)            │    友好       │
│  │     └── ontology.yaml                         │               │
│  │   ~/.localbrisk/localbrisk.db (DuckDB)        │               │
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

> **配置即代码**：整个 `Catalogs/` 目录由纯 YAML 和 Markdown 文件组成——没有私有二进制格式。你可以直接 `git init` 该目录，对 Agent 定义、本体模型、记忆提示词和技能包进行版本控制，然后 push 到任意 Git 远程仓库，在团队间共享与协作。

### 三层协作

| 层级 | 技术栈 | 职责 |
|------|--------|------|
| **UI 层** | Vue 3 + Vite + Tailwind CSS + Radix-Vue + vue-i18n + CodeMirror + ECharts + Mermaid | 响应式界面、配置编辑、数据可视化、文档预览 |
| **桌面外壳** | Tauri 2.0 (Rust) | 窗口管理、原生菜单、Sidecar 进程调度、文件操作、设置持久化 |
| **后端服务** | Python FastAPI + LangGraph + LangChain + DeepAgents + Polars + DuckDB | AI Agent 引擎、数据计算、资产管理、模型网关 |

### 打包与分发

- **Python 后端** → PyInstaller 打包为单一可执行文件
- **整体应用** → Tauri Bundler 输出 `.app` / `.dmg` (macOS)、`.msi` / `.exe` (Windows)、`.AppImage` / `.deb` (Linux)

---

## 领域模型

```
BusinessUnit (业务单元)
├── Agent (智能体)
│   ├── memories/          # 记忆/提示词 (.md)
│   ├── skills/            # 技能目录
│   ├── models/            # 模型配置 (.yaml) — 本地模型 / API 端点
│   ├── mcps/              # MCP 工具配置 — Python函数 / MCP Server / 远程API
│   └── output/            # 工作记录与会话历史
│       ├── .conversation_history/
│       ├── .checkpoints/
│       └── {session}/
└── AssetBundle (资源包: local | external)
    ├── tables/            # 表映射 (Parquet / CSV / JSON / Delta / 远程DB)
    ├── volumes/           # 文档存储 (本地 / S3)
    ├── functions/         # 自定义函数
    ├── notes/             # 笔记
    └── ontology.yaml      # 本体定义 — 描述资产间的关系与可执行动作
```

所有配置均以 YAML 文件落盘（`config.yaml`、`agent_spec.yaml`、`bundle.yaml`、`ontology.yaml`），**目录即模型**，便于版本管理与导入导出。

### 本体建模（Ontology）

当前系统的数据资产（Tables、Volumes、Functions）仅通过目录层级组织，缺乏**横向关系表达**。本体层在 AssetBundle 级别引入语义建模能力，让 Agent 能理解数据之间的关联并自动编排执行动作。

#### 设计理念

```
                    ┌─────────────┐
                    │  Ontology   │  ← 语义描述层（关系 + 动作）
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      ┌─────────┐    ┌─────────┐    ┌───────────┐
      │  Table   │    │ Volume  │    │ Function  │
      │ (数据)   │◄──►│ (文档)   │◄──►│ (动作)     │
      └─────────┘    └─────────┘    └───────────┘
```

- **Entity（实体）**：对 AssetBundle 内已有资产的语义标注（类型、角色、领域归属）
- **Relationship（关系）**：表达实体之间的关联（外键、派生、依赖、引用等）
- **Action（动作）**：绑定到关系或实体上的可执行操作（Function / SQL / Agent Skill）

#### 物理存储

本体定义以 `ontology.yaml` 文件存放在 AssetBundle 根目录下：

```
asset_bundles/{bundle_name}/
├── bundle.yaml
├── ontology.yaml          # 本体定义文件
├── tables/
├── functions/
└── volumes/
```

#### ontology.yaml 示例

```yaml
# AssetBundle 本体定义
version: "1.0"
namespace: "financial_research"

# ==================== 实体声明 ====================
entities:
  - name: orders                        # 引用 tables/orders.yaml
    asset_type: table
    semantic_type: fact_table            # 语义类型: fact_table / dimension / metric / document / function
    domain: sales                        # 业务域标签
    description: "订单交易事实表"

  - name: customers
    asset_type: table
    semantic_type: dimension
    domain: crm
    description: "客户维度表"

  - name: products
    asset_type: table
    semantic_type: dimension
    domain: product

  - name: monthly_revenue
    asset_type: table
    semantic_type: metric
    domain: finance
    description: "月度营收汇总指标表"

  - name: calculate_growth_rate
    asset_type: function
    semantic_type: function
    domain: finance
    description: "计算同比/环比增长率"

  - name: q4_report
    asset_type: volume
    semantic_type: document
    domain: finance

# ==================== 关系定义 ====================
relationships:
  # 外键关系 — 表间 join 路径
  - name: order_customer_fk
    type: foreign_key                    # foreign_key / derived_from / depends_on / references / contains
    source: orders
    target: customers
    properties:
      source_column: customer_id
      target_column: id
      join_type: left

  - name: order_product_fk
    type: foreign_key
    source: orders
    target: products
    properties:
      source_column: product_id
      target_column: id

  # 派生关系 — 指标由哪些源表计算得出
  - name: revenue_derived_from_orders
    type: derived_from
    source: monthly_revenue
    target: orders
    properties:
      aggregation: "SUM(amount) GROUP BY month"
      schedule: daily

  # 依赖关系 — 函数需要哪些表作为输入
  - name: growth_rate_depends_on_revenue
    type: depends_on
    source: calculate_growth_rate
    target: monthly_revenue

  # 引用关系 — 文档引用了哪些数据
  - name: report_references_revenue
    type: references
    source: q4_report
    target: monthly_revenue

# ==================== 动作定义 ====================
actions:
  # 绑定到实体的动作
  - name: refresh_monthly_revenue
    description: "刷新月度营收汇总"
    trigger: manual | schedule | on_change   # 触发方式
    target_entity: monthly_revenue
    action_type: sql                          # sql / function / skill / pipeline
    action_config:
      sql: |
        INSERT INTO monthly_revenue
        SELECT DATE_TRUNC('month', order_date) AS month,
               SUM(amount) AS revenue
        FROM orders
        GROUP BY 1

  - name: calc_yoy_growth
    description: "计算年同比增长率"
    trigger: manual
    target_entity: monthly_revenue
    action_type: function
    action_config:
      function_ref: calculate_growth_rate    # 引用 functions/ 下的函数
      parameters:
        metric_column: revenue
        time_column: month
        period: year

  # 绑定到关系的动作（当关系发生变化时触发）
  - name: validate_order_customer_integrity
    description: "校验订单-客户引用完整性"
    trigger: on_change
    target_relationship: order_customer_fk
    action_type: sql
    action_config:
      sql: |
        SELECT o.id, o.customer_id
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE c.id IS NULL
```

#### 关系类型一览

| 类型 | 含义 | 典型场景 |
|------|------|---------|
| `foreign_key` | 外键引用，表间 join 路径 | orders.customer_id → customers.id |
| `derived_from` | 派生/计算来源 | 指标表由事实表聚合得出 |
| `depends_on` | 执行依赖 | 函数需要某张表作为输入 |
| `references` | 内容引用 | 文档/笔记引用了某张数据表 |
| `contains` | 包含/嵌套 | Volume 包含多个子文档 |

#### 动作类型一览

| 类型 | 说明 | 执行方式 |
|------|------|---------|
| `sql` | SQL 脚本 | 通过 DuckDB Compute Engine 执行 |
| `function` | 自定义函数 | 引用 functions/ 下的 Python 函数 |
| `skill` | Agent 技能 | 调用 Agent 的 Skill 执行 |
| `pipeline` | 多步编排 | 按顺序执行多个 action |

#### Agent 如何利用本体

1. **自动发现 Join 路径**：Agent 通过 `foreign_key` 关系自动推断多表关联 SQL
2. **理解数据血缘**：通过 `derived_from` 关系追溯指标来源，回答"这个数据是怎么算出来的"
3. **智能编排动作**：Agent 根据 `depends_on` 关系自动排序执行步骤
4. **知识关联**：通过 `references` 关系将文档与数据打通，回答"哪些报告用到了这张表"

---

## 项目目录结构

```
LocalBrisk/
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/              # HomeView (唯一页面: 导航 + 树 + 详情)
│   │   ├── components/
│   │   │   ├── catalog/        # Catalog 面板、创建对话框
│   │   │   ├── detail/         # Agent/Model/Table/Volume/Skill/Memory 详情
│   │   │   ├── common/         # 通用组件 (Dialog/Form/Toast/ConfigEditor)
│   │   │   ├── viewer/         # 文件查看器 (Markdown/PDF/Office/Excel/Image)
│   │   │   ├── layout/         # 导航按钮
│   │   │   └── settings/       # 设置与关于弹窗
│   │   ├── services/           # API (Python后端) + Tauri IPC + 文件服务
│   │   ├── stores/             # 状态管理 (businessUnitStore + artifactStore)
│   │   ├── composables/        # 组合函数 (SSE/表单/异步/配置/文件浏览/Toast)
│   │   ├── types/              # TypeScript 类型 (领域模型/运行时/流式协议)
│   │   └── i18n/               # 国际化 (zh-CN, en, zh-TW, ja)
│   └── package.json
│
├── src-tauri/                  # Tauri 桌面壳 (Rust)
│   ├── src/
│   │   ├── main.rs             # 入口: 插件注册 + 菜单 + Sidecar
│   │   ├── backend.rs          # Sidecar 进程管理 (启动/健康检查/停止)
│   │   ├── commands.rs         # Tauri 命令 (应用信息/设置)
│   │   ├── file_ops.rs         # 文件操作命令
│   │   ├── menu.rs             # 原生菜单
│   │   └── settings.rs         # 设置持久化
│   ├── binaries/               # 打包后的 Python 后端可执行文件
│   └── tauri.conf.json         # 窗口/打包/权限配置
│
├── backend/                    # Python FastAPI 后端
│   ├── main.py                 # FastAPI 入口 (端口 8765)
│   ├── run.py                  # PyInstaller 打包入口
│   ├── app/
│   │   ├── api/endpoints/      # REST API 端点
│   │   │   ├── business_unit   # 业务单元全量 CRUD
│   │   │   ├── agent_runtime   # Agent 流式执行 (SSE)
│   │   │   ├── model_runtime   # Model 直连执行
│   │   │   ├── llm_providers   # 模型提供商目录
│   │   │   ├── compute_engine  # DuckDB SQL 执行
│   │   │   └── health          # 健康检查
│   │   ├── core/               # 配置/日志/国际化/中间件/常量
│   │   ├── models/             # Pydantic 数据模型
│   │   └── services/           # 业务服务层 + 数据库连接器
│   ├── agent_engine/           # AI Agent 引擎
│   │   ├── core/               # 流式协议 (StreamMessage)、配置模型
│   │   ├── engine/             # DeepAgentsEngine (LangGraph)
│   │   ├── services/           # AgentRuntimeService (生命周期管理)
│   │   ├── llm/                # LLMClientFactory + Provider 注册表
│   │   └── tools/              # 运行时工具集
│   ├── compute_engine/         # DuckDB 计算服务
│   └── tests/                  # 单元测试
│
├── build.sh / build.bat        # 一键构建脚本
├── dev.sh                      # 开发启动脚本
└── DEVELOPMENT.md              # 开发指南
```

---

## 核心功能

### Agent 智能对话

- 每个 Agent 配置独立的模型、记忆、技能和 MCP 工具
- 流式执行（SSE），前端实时渲染思考过程、任务列表与制品产出
- 支持断线重连快照恢复
- 会话历史本地持久化

### 统一资产管理

- BusinessUnit 下可管理多个 AssetBundle（本地/外部数据源）
- 支持 MySQL / PostgreSQL / SQLite / DuckDB 外部连接与元数据同步
- 表数据预览、文档（PDF/Office/Markdown/Excel）在线查看
- 技能以 zip 包导入，Memory 以 Markdown 编辑

### 本体建模（Ontology）

- 在 AssetBundle 级别定义数据资产间的语义关系（`ontology.yaml`）
- **五种关系类型**：外键（foreign_key）、派生（derived_from）、依赖（depends_on）、引用（references）、包含（contains）
- **四种动作类型**：SQL 脚本、自定义函数、Agent 技能、多步 Pipeline
- Agent 运行时自动加载本体，实现 Join 路径推断、数据血缘追溯、智能动作编排
- 动作可配置触发方式：手动、定时、数据变更触发

### 本地计算引擎

- DuckDB 嵌入式分析数据库，支持 SQL 查询执行并返回表格数据
- 执行历史审计记录
- 查询类 SQL 安全限制（仅 SELECT/WITH/SHOW/DESCRIBE/PRAGMA）

### 多模型支持

| 类型 | 支持的提供商 |
|------|------------|
| API 端点 | OpenAI, Claude, 通义千问, 百度千帆, Gemini, DeepSeek, 智谱, Moonshot |
| 本地模型 | Qwen, DeepSeek, Llama, Mistral, ChatGLM, 百川, InternLM (规划中) |

### 国际化

前后端统一支持 4 种语言：简体中文 (默认)、English、繁體中文、日本語

---

## 快速开始

### 环境要求

- **Node.js** >= 18
- **Rust** >= 1.70
- **Python** >= 3.10

### 安装依赖

```bash
# 前端依赖
cd frontend && npm install && cd ..

# Python 后端依赖
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 开发模式

```bash
# 一键启动 (Python 后端 + Tauri 前端)
./dev.sh

# 仅启动后端
./dev.sh --backend-only

# 仅启动前端
./dev.sh --frontend-only

# 更新 Python 依赖后启动
./dev.sh --update-deps
```

开发时前端运行在 `http://localhost:1420`，后端运行在 `http://127.0.0.1:8765`。

### 构建发布

```bash
# 一键打包: PyInstaller → Sidecar → Tauri Build
./build.sh        # macOS/Linux
build.bat         # Windows
```

构建产物：

| 平台 | 产物路径 |
|------|---------|
| macOS | `src-tauri/target/release/bundle/macos/` 和 `dmg/` |
| Windows | `src-tauri/target/release/bundle/msi/` 和 `nsis/` |
| Linux | `src-tauri/target/release/bundle/appimage/` 和 `deb/` |

---

## API 概览

后端以 FastAPI 提供 RESTful API，开发模式下可访问 `http://127.0.0.1:8765/docs` 查看 Swagger 文档。

| 路由前缀 | 说明 |
|----------|------|
| `/health` | 健康检查 & 就绪探针 |
| `/api/business_units` | 业务单元及子资源 CRUD |
| `/api/runtime/{bu}/agents/{agent}` | Agent 加载 / 流式执行 / 状态 / 取消 / 卸载 |
| `/api/runtime/{bu}/agents/{agent}/models/{model}` | Model 加载 / 执行 / 流式执行 |
| `/api/llm` | LLM 提供商与模型目录 |
| `/api/compute` | DuckDB SQL 执行 |
| `/api/i18n/locales` | 支持的语言列表 |

---

## 前后端通信机制

| 通道 | 用途 |
|------|------|
| **HTTP (Fetch)** | 前端 ↔ Python 后端（业务 API、模型调用） |
| **SSE (Server-Sent Events)** | Agent/Model 流式执行，实时推送 THOUGHT/TASK_LIST/ARTIFACT/STATUS/ERROR/DONE |
| **Tauri IPC (invoke)** | 前端 ↔ Rust 主进程（应用信息、文件操作、设置管理） |
| **Sidecar** | Rust 主进程 → Python 后端（进程启停、健康检查） |

### StreamMessage 流式协议

Agent 执行产出的每条消息均为 `StreamMessage`，包含类型字段供前端分区渲染：

| 类型 | 渲染位置 |
|------|---------|
| `THOUGHT` | 左侧思考面板（打字机效果） |
| `TASK_LIST` | 左侧任务列表 |
| `ARTIFACT` | 右侧制品展示 |
| `STATUS` | 瞬时状态提示 |
| `ERROR` | 错误信息 |
| `DONE` | 执行完成 |

---

## 数据存储

| 存储类型 | 路径 | 用途 |
|----------|------|------|
| 文件系统 (YAML + 目录) | `~/.localbrisk/App_Data/Catalogs/` | 业务单元、Agent、AssetBundle 配置与资产 |
| DuckDB | `~/.localbrisk/localbrisk.db` | 计算引擎、SQL 执行历史 |
| Tauri Store | 应用数据目录 | 用户设置（语言、后端保活等） |
| 日志 | `~/Library/Logs/LocalBrisk/app.log` | 后端按天滚动日志（保留 7 天） |

---

## 设计语言

**「Clear & Float」（纯净与漂浮）**

- 纯白 (#FFFFFF) 主卡片 + 浅灰 (#F5F5F7) 背景
- 全局 12px 圆角
- 微弱阴影悬浮感 (shadow-sm)
- 字色深灰 (#333333)，微软雅黑 / Segoe UI

---

## 路线图

| 阶段 | 目标 |
|------|------|
| Phase 1 | 框架搭建，YAML 配置与 i18n 集成 |
| Phase 2 | 三层递归发现机制（BusinessUnit → Agent/AssetBundle → Assets） |
| Phase 3 | Polars + LangGraph 混合资产统一访问，Agent 流式执行 |
| Phase 4 | 视觉美化、本地模型支持、多语言完善 |
| Phase 5 | 本体建模（Ontology）— 数据关系语义化、Action 动作引擎、Agent 自动编排 |
| Phase 6 | 本地 Agent 公司 — BusinessUnit 内多 Agent 协作、角色化任务分派、跨 Agent 工作流编排 |

---

## 许可

Copyright © 2026 LocalBrisk Team. All rights reserved.
