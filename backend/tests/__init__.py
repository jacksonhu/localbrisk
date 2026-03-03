"""
LocalBrisk Backend 单元测试

目录结构:
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # 全局测试配置和 fixtures
├── agent_engine/            # Agent Engine 相关测试
│   ├── __init__.py
│   ├── conftest.py          # Agent Engine 测试专用 fixtures
│   ├── test_agent_loader.py # 配置加载器测试
│   └── test_deepagents_engine.py  # DeepAgents 引擎测试
├── test_catalog_api.py      # Catalog API 测试
├── test_catalog_service.py  # Catalog 服务测试
├── test_connectors.py       # 连接器测试
├── test_metadata_sync.py    # 元数据同步测试
└── test_models.py           # 模型测试
"""
