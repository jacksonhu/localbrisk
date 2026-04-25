"""Agent Engine test fixtures.

Provides temporary agent directory structures conforming to the simplified
``agent_spec.yaml`` schema (string ``instruction``, top-level ``skills``,
``llm_config.llm_model`` as the only source of the active model).
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


# ============================================================================
# Test data builders
# ============================================================================

def create_test_agent_data() -> Dict[str, Any]:
    """Build a representative agent config payload used to seed fixtures."""
    return {
        "agent_spec": {
            "baseinfo": {
                "name": "test_data_analyst",
                "description": "Test data analyst agent",
                "version": "1.0.0",
            },
            "instruction": (
                "You are agent {{agent_name}}\n"
                "Working directory: {{agent_path}}\n"
                "Current date: {{now}}"
            ),
            "llm_config": {
                "llm_model": "test_model",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            "skills": [],
        },
        "model_config": {
            "model_type": "endpoint",
            "endpoint_provider": "openai",
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "model_id": "gpt-4",
            "temperature": 0.7,
        },
        "memory_content": (
            "# Test Memory\n\n"
            "Reusable context for the data analyst agent.\n"
        ),
        "skill_config": {
            "baseinfo": {
                "name": "test_skill",
                "display_name": "Test Skill",
                "description": "Test skill",
            },
            "version": "1.0.0",
        },
    }


def _create_agent_directory(agent_dir: Path, data: Dict[str, Any]) -> None:
    """Materialize an agent directory tree that matches the new schema."""
    agent_dir.mkdir(parents=True, exist_ok=True)

    # 1. agent_spec.yaml
    with open(agent_dir / "agent_spec.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["agent_spec"], f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # 2. models/
    models_dir = agent_dir / "models"
    models_dir.mkdir(exist_ok=True)
    with open(models_dir / "test_model.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["model_config"], f, default_flow_style=False, allow_unicode=True)

    # 3. memories/ (auto-loaded at runtime; no per-file toggle)
    memories_dir = agent_dir / "memories"
    memories_dir.mkdir(exist_ok=True)
    (memories_dir / "AGENTS.md").write_text(data["memory_content"], encoding="utf-8")

    # 4. skills/<name>/SKILL.md + optional yaml metadata
    skills_dir = agent_dir / "skills"
    skills_dir.mkdir(exist_ok=True)
    test_skill_dir = skills_dir / "test_skill"
    test_skill_dir.mkdir(exist_ok=True)
    with open(test_skill_dir / "test_skill.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data["skill_config"], f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    (test_skill_dir / "SKILL.md").write_text(
        "# Test Skill\n\nThis is a test skill.",
        encoding="utf-8",
    )

    # 5. output/ (runtime artifacts go here)
    (agent_dir / "output").mkdir(exist_ok=True)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def temp_agent_dir():
    """Build a self-contained temp agent directory conforming to the new schema."""
    temp_dir = tempfile.mkdtemp(prefix="agent_test_")
    agent_dir = Path(temp_dir) / "test_data_analyst"

    data = create_test_agent_data()
    _create_agent_directory(agent_dir, data)

    yield {
        "temp_dir": temp_dir,
        "agent_path": str(agent_dir),
        "agent_name": "test_data_analyst",
        "data": data,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_agents_catalog():
    """Build a temp catalog tree that hosts multiple agents for scan-style tests."""
    temp_dir = tempfile.mkdtemp(prefix="catalog_test_")
    catalogs_dir = Path(temp_dir) / "App_Data" / "Catalogs" / "test_unit" / "agents"
    catalogs_dir.mkdir(parents=True, exist_ok=True)

    data = create_test_agent_data()

    agent_a_dir = catalogs_dir / "agent_a"
    agent_b_dir = catalogs_dir / "agent_b"

    data_a = {**data, "agent_spec": {**data["agent_spec"]}}
    data_a["agent_spec"]["baseinfo"] = {"name": "agent_a", "description": "Agent A"}

    data_b = {**data, "agent_spec": {**data["agent_spec"]}}
    data_b["agent_spec"]["baseinfo"] = {"name": "agent_b", "description": "Agent B"}

    _create_agent_directory(agent_a_dir, data_a)
    _create_agent_directory(agent_b_dir, data_b)

    yield {
        "temp_dir": temp_dir,
        "catalogs_dir": str(catalogs_dir.parent),
        "business_unit_id": "test_unit",
        "agents": {
            "agent_a": str(agent_a_dir),
            "agent_b": str(agent_b_dir),
        },
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def real_agent_path():
    """Return the path to a real local agent for optional integration tests."""
    agent_path = os.path.expanduser(
        "~/.localbrisk/App_Data/Catalogs/myunit/agents/Data_analyst"
    )
    exists = Path(agent_path).exists()
    return {
        "agent_path": agent_path,
        "business_unit_id": "myunit",
        "exists": exists,
    }
