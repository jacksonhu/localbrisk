# Roadmap

> **Last updated: 2026-03-31**
>
> This roadmap reflects our current plans and priorities. It may evolve as the project grows and community feedback comes in. Contributions are welcome at every phase!

## Current Status: Phase 5 — Ontology Modeling

---

## Phase 1 — Foundation ✅

- [x] Project scaffolding (Tauri + Vue 3 + FastAPI sidecar)
- [x] YAML-based configuration system
- [x] i18n integration (English / Chinese)
- [x] Three-panel layout (Catalog · Detail · Chat)

## Phase 2 — Catalog Discovery ✅

- [x] Three-tier recursive discovery: BusinessUnit → Agent / AssetBundle → Assets
- [x] File system watcher for live catalog refresh
- [x] YAML-driven Agent & AssetBundle definitions

## Phase 3 — Agent Execution ✅

- [x] Polars + DuckDB unified asset access layer
- [x] LangGraph-powered Agent streaming execution
- [x] Local Agent sandbox (isolated venv + file system + tool permissions)
- [x] Federated query across local files and remote databases

## Phase 4 — Polish & Local Models ✅

- [x] UI visual refinement and responsive layout
- [x] Local model support (Ollama, llama.cpp compatible)
- [x] i18n refinement and community translation workflow

## Phase 5 — Ontology Modeling 🚧 *In Progress*

- [ ] `ontology.yaml` schema: entities, relationships, actions
- [ ] Ontology graph visualization (interactive node-edge editor)
- [ ] Action engine: ontology-driven tool invocation
- [ ] Agent auto-orchestration based on ontology reasoning
- [ ] Cross-source semantic joins (local files ↔ cloud databases)

## Phase 6 — Local Agent Company 📋 *Planned*

- [ ] Multi-Agent collaboration within a BusinessUnit
- [ ] Role-based task delegation (analyst, reviewer, monitor, etc.)
- [ ] Cross-Agent workflow orchestration
- [ ] Shared memory and context passing between Agents
- [ ] Agent performance dashboard

## Phase 7 — Ecosystem & Community 📋 *Planned*

- [ ] Skill marketplace: publish & install reusable Agent skill packages
- [ ] Plugin system for custom tools and data connectors
- [ ] One-click Agent template sharing via Git
- [ ] Community showcase & example catalog
- [ ] CI/CD pipeline for Agent testing & deployment

---

## How to Influence the Roadmap

- **Open an Issue** with the `enhancement` label to propose a feature.
- **Start a Discussion** to share ideas or vote on priorities.
- **Submit a PR** — code contributions directly move items forward.

We actively prioritize based on community demand. Your input matters!

---

# 路线图

> **最后更新：2026-03-31**
>
> 本路线图反映当前计划与优先级，可能随项目发展和社区反馈而调整。欢迎在任何阶段参与贡献！

## 当前阶段：Phase 5 — 本体建模

---

## Phase 1 — 基础框架 ✅

- [x] 项目脚手架（Tauri + Vue 3 + FastAPI sidecar）
- [x] 基于 YAML 的配置系统
- [x] 国际化集成（中文 / 英文）
- [x] 三栏布局（目录 · 详情 · 对话）

## Phase 2 — 目录发现 ✅

- [x] 三层递归发现：BusinessUnit → Agent / AssetBundle → Assets
- [x] 文件系统监听，实时刷新目录树
- [x] YAML 驱动的 Agent 与 AssetBundle 定义

## Phase 3 — Agent 执行 ✅

- [x] Polars + DuckDB 统一资产访问层
- [x] LangGraph 驱动的 Agent 流式执行
- [x] 本地 Agent 沙箱（隔离 venv + 文件系统 + 工具权限）
- [x] 本地文件与远程数据库联邦查询

## Phase 4 — 打磨与本地模型 ✅

- [x] UI 视觉优化与响应式布局
- [x] 本地模型支持（Ollama、llama.cpp 兼容）
- [x] 国际化完善与社区翻译流程

## Phase 5 — 本体建模 🚧 *进行中*

- [ ] `ontology.yaml` 模式：实体、关系、动作
- [ ] 本体图谱可视化（交互式节点-边编辑器）
- [ ] 动作引擎：基于本体驱动的工具调用
- [ ] Agent 基于本体推理的自动编排
- [ ] 跨源语义关联（本地文件 ↔ 云端数据库）

## Phase 6 — 本地 Agent 公司 📋 *规划中*

- [ ] BusinessUnit 内多 Agent 协作
- [ ] 角色化任务分派（分析师、审查员、监控员等）
- [ ] 跨 Agent 工作流编排
- [ ] Agent 间共享记忆与上下文传递
- [ ] Agent 运行看板

## Phase 7 — 生态与社区 📋 *规划中*

- [ ] 技能市场：发布与安装可复用 Agent 技能包
- [ ] 插件系统：自定义工具与数据连接器
- [ ] 通过 Git 一键共享 Agent 模板
- [ ] 社区案例展示与示例目录
- [ ] Agent 测试与发布 CI/CD 流水线

---

## 如何影响路线图

- **提 Issue**：使用 `enhancement` 标签提出功能建议。
- **发起 Discussion**：分享想法或对优先级投票。
- **提交 PR**——代码贡献直接推动进展。

我们会根据社区需求动态调整优先级，你的声音很重要！
