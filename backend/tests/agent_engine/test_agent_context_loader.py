"""Unit tests for the shared agent context loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_business_unit_agent_dir(tmp_path: Path) -> dict:
    """Create a BusinessUnit-like structure with one external asset bundle."""
    business_unit_dir = tmp_path / "test_unit"
    agent_dir = business_unit_dir / "agents" / "test_data_analyst"
    asset_bundle_dir = business_unit_dir / "asset_bundles" / "sales_bundle"
    tables_dir = asset_bundle_dir / "tables"
    models_dir = agent_dir / "models"
    skills_dir = agent_dir / "skills" / "test_skill"
    output_dir = agent_dir / "output"

    tables_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    agent_spec = {
        "baseinfo": {"name": "test_data_analyst", "description": "Test agent"},
        "active_model": "test_model",
        "llm_config": {"temperature": 0.2, "max_tokens": 1024},
    }
    model_config = {
        "model_type": "endpoint",
        "endpoint_provider": "openai",
        "api_base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "model_id": "gpt-4o-mini",
        "temperature": 0.2,
    }
    bundle_yaml = {
        "bundle_type": "external",
        "connection": {
            "type": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "db_name": "sales_db",
            "username": "demo",
            "password": "secret",
        },
    }
    table_yaml = {
        "baseinfo": {"name": "orders", "description": "Order facts"},
        "schema_name": "sales_db",
        "primary_keys": ["id"],
        "columns": [
            {"name": "id", "data_type": "bigint", "nullable": False, "is_primary_key": True, "comment": "PK"},
            {"name": "amount", "data_type": "decimal(10,2)", "nullable": False, "is_primary_key": False, "comment": "Amount"},
        ],
    }

    with open(agent_dir / "agent_spec.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(agent_spec, file, allow_unicode=True, sort_keys=False)
    with open(models_dir / "test_model.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(model_config, file, allow_unicode=True, sort_keys=False)
    with open(skills_dir / "SKILL.md", "w", encoding="utf-8") as file:
        file.write("# Test Skill\n\nSkill content.")
    with open(asset_bundle_dir / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(bundle_yaml, file, allow_unicode=True, sort_keys=False)
    with open(tables_dir / "orders.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(table_yaml, file, allow_unicode=True, sort_keys=False)

    return {
        "business_unit_dir": business_unit_dir,
        "agent_path": str(agent_dir),
    }


class TestAgentContextLoader:
    """Shared context loader behavior tests."""

    @pytest.mark.asyncio
    async def test_load_agent_context_success(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_agent_context

        context = await load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert context is not None
        assert context.agent_name == "test_data_analyst"
        assert context.business_unit_id == "test_unit"
        assert Path(context.agent_path).exists()

    @pytest.mark.asyncio
    async def test_load_agent_context_with_model(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_agent_context

        context = await load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert context.model_config is not None
        assert context.model_config.get("endpoint_provider") == "openai"
        assert context.model_config.get("model_id") == "gpt-4"

    @pytest.mark.asyncio
    async def test_load_agent_context_output_created(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_agent_context

        output_dir = Path(temp_agent_dir["agent_path"]) / "output"
        if output_dir.exists():
            output_dir.rmdir()

        context = await load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert Path(context.output_path).exists()

    @pytest.mark.asyncio
    async def test_load_agent_context_with_asset_bundles(self, temp_business_unit_agent_dir):
        from agent_engine.engine.agent_context_loader import load_agent_context

        context = await load_agent_context(temp_business_unit_agent_dir["agent_path"], "test_unit")

        assert len(context.asset_bundles) == 1
        bundle = context.asset_bundles[0]
        assert bundle.bundle_name == "sales_bundle"
        assert bundle.bundle_type == "external"
        assert bundle.bundle_path.endswith("sales_bundle")

    def test_compute_agent_context_fingerprint_changes_when_active_model_changes(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import compute_agent_context_fingerprint, load_agent_spec

        agent_path = Path(temp_agent_dir["agent_path"])
        initial_fingerprint = compute_agent_context_fingerprint(agent_path, "test_unit")

        spec = load_agent_spec(agent_path)
        spec["active_model"] = "gpt5"
        (agent_path / "agent_spec.yaml").write_text(
            yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (agent_path / "models" / "gpt5.yaml").write_text(
            yaml.safe_dump(
                {
                    **temp_agent_dir["data"]["model_config"],
                    "model_id": "gpt-5",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        updated_fingerprint = compute_agent_context_fingerprint(agent_path, "test_unit")

        assert updated_fingerprint != initial_fingerprint

    def test_compute_agent_context_fingerprint_ignores_unselected_skills(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import compute_agent_context_fingerprint, load_agent_spec

        agent_path = Path(temp_agent_dir["agent_path"])
        spec = load_agent_spec(agent_path)
        spec["capabilities"] = {"native_skills": [{"name": "test_skill"}]}
        (agent_path / "agent_spec.yaml").write_text(
            yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        baseline = compute_agent_context_fingerprint(agent_path, "test_unit")
        ignored_skill_dir = agent_path / "skills" / "ignored_skill"
        ignored_skill_dir.mkdir(parents=True, exist_ok=True)
        (ignored_skill_dir / "SKILL.md").write_text("# Ignored Skill\n\nShould not affect runtime.", encoding="utf-8")

        assert compute_agent_context_fingerprint(agent_path, "test_unit") == baseline

    def test_load_memories_prefers_instruction_templates(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_memories, load_agent_spec

        agent_path = Path(temp_agent_dir["agent_path"])
        memories_dir = agent_path / "memories"
        memories_dir.mkdir(exist_ok=True)
        (memories_dir / "AGENTS.md").write_text("# Default memory", encoding="utf-8")
        (memories_dir / "project.md").write_text("# Project memory", encoding="utf-8")
        (memories_dir / "ignored.md").write_text("# Ignored memory", encoding="utf-8")

        spec_path = agent_path / "agent_spec.yaml"
        spec = load_agent_spec(agent_path)
        spec["instruction"] = {
            "user_prompt_templates": [
                {"name": "project"},
                {"name": "AGENTS.md"},
            ]
        }
        spec_path.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")

        memories = load_memories(agent_path, agent_spec=load_agent_spec(agent_path))

        assert memories == ["/memories/project.md", "/memories/AGENTS.md"]

    def test_load_skills_returns_empty_when_native_skills_not_declared(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_skills

        agent_path = Path(temp_agent_dir["agent_path"])
        skills = load_skills(agent_path)

        assert skills == []

    def test_load_skills_reads_only_declared_native_skills(self, temp_agent_dir):
        from agent_engine.engine.agent_context_loader import load_agent_spec, load_skills

        agent_path = Path(temp_agent_dir["agent_path"])
        skills_dir = agent_path / "skills"
        extra_skill_dir = skills_dir / "extra_skill"
        extra_skill_dir.mkdir(parents=True, exist_ok=True)
        (extra_skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: extra_skill\n"
            "description: Generate diagrams from structured specifications.\n"
            "license: Proprietary\n"
            "---\n\n"
            "# Extra Skill\n\nPerform chart generation.",
            encoding="utf-8",
        )
        (extra_skill_dir / "extra_skill.yaml").write_text(
            yaml.safe_dump(
                {
                    "display_name": "Charts Skill",
                    "description": "This YAML description should be ignored.",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        spec_path = agent_path / "agent_spec.yaml"
        spec = load_agent_spec(agent_path)
        spec["capabilities"] = {
            "native_skills": [
                {"name": "extra_skill"},
            ]
        }
        spec_path.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")

        skills = load_skills(agent_path, agent_spec=load_agent_spec(agent_path))

        assert [skill.name for skill in skills] == ["extra_skill"]
        assert skills[0].skill_path == str(extra_skill_dir)
        assert skills[0].display_name == "Charts Skill"
        assert skills[0].description == "Generate diagrams from structured specifications."
        assert skills[0].tool_name == "skill_extra_skill"
        assert skills[0].instructions.startswith("# Extra Skill")
        assert "Perform chart generation." in skills[0].instructions
        assert "description:" not in skills[0].instructions
