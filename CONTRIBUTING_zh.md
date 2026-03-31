# 贡献指南

感谢你对 LocalBrisk 的关注！无论是提交 Bug、建议新功能、改进文档还是贡献代码，每一份参与都非常重要。

## 目录

- [行为准则](#行为准则)
- [如何参与](#如何参与)
- [开发环境搭建](#开发环境搭建)
- [分支与提交规范](#分支与提交规范)
- [Pull Request 流程](#pull-request-流程)
- [反馈问题](#反馈问题)

## 行为准则

本项目遵循 [Contributor Covenant 行为准则](CODE_OF_CONDUCT.md)，参与即表示你同意遵守该准则。

## 如何参与

1. **Fork** 本仓库并克隆到本地。
2. 从 `main` 创建**功能分支**：
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. 进行修改，确保代码质量，注释和日志统一使用**英文**。
4. 在本地**测试**你的改动（环境搭建请参考[开发指南](DEVELOPMENT_zh.md)）。
5. 提交并推送到你的 Fork，然后发起 **Pull Request**。

## 开发环境搭建

请参阅[开发指南](DEVELOPMENT_zh.md)，了解后端、前端和 Tauri 桌面壳的详细搭建步骤。

## 分支与提交规范

### 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feat/简短描述` | `feat/ontology-editor` |
| 修复 | `fix/简短描述` | `fix/agent-sandbox-crash` |
| 文档 | `docs/简短描述` | `docs/contributing-guide` |
| 重构 | `refactor/简短描述` | `refactor/asset-loader` |

### 提交信息

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <short summary>

[optional body]
```

示例：
```
feat(agent): add streaming output for agent execution
fix(frontend): correct catalog tree rendering on resize
docs(readme): update ontology modeling description
```

## Pull Request 流程

1. PR 目标分支为 `main`（或当前开发分支）。
2. 按照 PR 模板填写——说明**改了什么**以及**为什么改**。
3. 保持 PR 聚焦：一个 PR 只做一件事。
4. 代码中的注释、日志和文档统一使用**英文**。
5. 维护者会审查你的 PR，可能会要求修改后再合并。

## 反馈问题

- 使用仓库提供的 [Issue 模板](.github/ISSUE_TEMPLATE/) 提交 Bug 或功能建议。
- 提交前先搜索已有 Issue，避免重复。
- Bug 报告请包含清晰的复现步骤。

---

感谢你帮助 LocalBrisk 变得更好！
