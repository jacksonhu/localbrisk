# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Ontology modeling foundation (`ontology.yaml` schema design)
- ROADMAP.md with detailed phase breakdown
- CONTRIBUTING.md / CONTRIBUTING_zh.md contribution guides
- CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
- GitHub Issue & PR templates
- GitHub Actions CI (frontend lint + backend lint)
- CHANGELOG.md

### Changed
- README / README_zh: refreshed tagline and project description
- README License section updated to reference Apache 2.0

---

## [0.1.0] — 2026-03-31

### Added
- Initial project release
- Tauri 2.0 + Vue 3 + FastAPI sidecar architecture
- Three-panel desktop layout (Catalog · Detail · Chat)
- YAML-based Agent and AssetBundle configuration
- Three-tier recursive catalog discovery (BusinessUnit → Agent/AssetBundle → Assets)
- Polars + DuckDB unified local asset access
- LangGraph-powered Agent streaming execution
- Local Agent sandbox with isolated venv and tool permissions
- Federated query across local files (Parquet/CSV/Excel) and remote databases (MySQL/PostgreSQL)
- Local LLM support (Ollama, OpenAI-compatible endpoints)
- i18n support (English / Chinese)
- Git-ready configuration-as-code (`~/.localbrisk/App_Data/Catalogs/`)
