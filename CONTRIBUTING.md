# Contributing to LocalBrisk

Thank you for your interest in contributing to LocalBrisk! Whether it's a bug report, feature request, documentation improvement, or code contribution — every bit helps.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Branch & Commit Conventions](#branch--commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## How to Contribute

1. **Fork** the repository and clone it locally.
2. Create a **feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. Make your changes, ensuring code quality and adding necessary comments/logs in **English**.
4. **Test** your changes locally (see [Development Guide](DEVELOPMENT.md) for setup).
5. Commit and push to your fork, then open a **Pull Request**.

## Development Setup

Please refer to the [Development Guide](DEVELOPMENT.md) for detailed instructions on setting up the backend, frontend, and Tauri desktop shell.

## Branch & Commit Conventions

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/short-description` | `feat/ontology-editor` |
| Bug fix | `fix/short-description` | `fix/agent-sandbox-crash` |
| Docs | `docs/short-description` | `docs/contributing-guide` |
| Refactor | `refactor/short-description` | `refactor/asset-loader` |

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional body]
```

Examples:
```
feat(agent): add streaming output for agent execution
fix(frontend): correct catalog tree rendering on resize
docs(readme): update ontology modeling description
```

## Pull Request Process

1. Ensure your PR targets the `main` branch (or the current development branch).
2. Fill in the PR template — describe **what** changed and **why**.
3. Keep PRs focused: one feature or fix per PR.
4. All comments, logs, and documentation within code should be in **English**.
5. A maintainer will review your PR and may request changes before merging.

## Reporting Issues

- Use the provided [Issue Templates](.github/ISSUE_TEMPLATE/) to file bugs or request features.
- Search existing issues first to avoid duplicates.
- Include clear steps to reproduce for bug reports.

---

Thank you for helping make LocalBrisk better!
