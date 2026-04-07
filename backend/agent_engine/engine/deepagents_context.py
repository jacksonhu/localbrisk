"""Context loading helpers for DeepAgents engine."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import yaml

from app.core.constants import AGENT_MEMORIES_DIR, AGENT_SKILLS_DIR, ASSET_BUNDLES_DIR, ASSET_BUNDLE_CONFIG_FILE, VOLUMES_DIR

logger = logging.getLogger(__name__)


@dataclass
class SkillConfig:
    """Skill mount configuration for DeepAgents backend."""

    name: str
    absolute_path: str
    mount_path: str


@dataclass
class AssetBundleBackendConfig:
    """Asset bundle backend configuration for DeepAgents backend."""

    bundle_name: str
    bundle_type: str
    bundle_path: str
    mount_path: str
    volumes: List[Dict[str, Any]]


@dataclass
class AgentBuildContext:
    """All configuration required to build a deep agent."""

    business_unit_path: str
    agent_path: str
    agent_name: str
    business_unit_id: str
    agent_spec: Dict[str, Any]
    model_config: Optional[Dict[str, Any]]
    memories: List[str]
    skills: List[SkillConfig]
    output_path: str
    asset_bundles: List[AssetBundleBackendConfig] | None = None

    def __post_init__(self):
        if self.asset_bundles is None:
            self.asset_bundles = []


async def load_agent_context(
    agent_path: str,
    business_unit_id: str,
    model_resolver: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, Any]]]]] = None,
) -> AgentBuildContext:
    """Load all configuration needed to build a deep agent."""
    expanded_agent_path = os.path.expanduser(agent_path)
    path = Path(expanded_agent_path)
    if not path.exists():
        raise ValueError(f"Agent directory does not exist: {agent_path}")

    spec_path = path / "agent_spec.yaml"
    if not spec_path.exists():
        raise ValueError(f"agent_spec.yaml does not exist: {spec_path}")

    with open(spec_path, "r", encoding="utf-8") as file:
        agent_spec = yaml.safe_load(file)

    agent_name = agent_spec.get("baseinfo", {}).get("name", path.name)
    model_config = await load_active_model(path, agent_spec, business_unit_id, agent_name, model_resolver)
    memories = load_memories(path)
    skills = load_skills(path)
    output_path = str(path / "output")
    os.makedirs(output_path, exist_ok=True)
    asset_bundles = load_asset_bundles(path.parent.parent, business_unit_id)

    return AgentBuildContext(
        business_unit_path=str(path.parent.parent),
        agent_path=expanded_agent_path,
        agent_name=agent_name,
        business_unit_id=business_unit_id,
        agent_spec=agent_spec,
        model_config=model_config,
        memories=memories,
        skills=skills,
        output_path=output_path,
        asset_bundles=asset_bundles,
    )


async def load_active_model(
    agent_path: Path,
    agent_spec: Dict[str, Any],
    business_unit_id: str,
    agent_name: str,
    model_resolver: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, Any]]]]] = None,
) -> Optional[Dict[str, Any]]:
    """Load the active model configuration for an agent."""
    active_model = agent_spec.get("active_model") or agent_spec.get("llm_config", {}).get("llm_model")
    if not active_model:
        logger.warning("Agent %s has no active model configured", agent_name)
        return None

    models_dir = agent_path / "models"
    model_file = models_dir / f"{active_model}.yaml"
    if model_file.exists():
        with open(model_file, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    if model_resolver is None:
        return None

    try:
        return await model_resolver(business_unit_id, agent_name, active_model)
    except Exception as exc:
        logger.error("Failed to resolve model config for %s/%s/%s: %s", business_unit_id, agent_name, active_model, exc)
        return None


def load_memories(agent_path: Path) -> List[str]:
    """Load enabled memories for an agent."""
    memories: List[str] = []
    memories_dir = agent_path / AGENT_MEMORIES_DIR
    if not memories_dir.exists():
        return memories

    for markdown_file in sorted(memories_dir.glob("*.md")):
        if markdown_file.name.startswith("."):
            continue
        memory_name = markdown_file.stem
        metadata_file = memories_dir / f".{memory_name}.meta.yaml"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as file:
                metadata = yaml.safe_load(file) or {}
        if not metadata.get("enabled", True):
            continue
        memories.append(f"/memories/{memory_name}.md")
    return memories


def load_skills(agent_path: Path) -> List[SkillConfig]:
    """Load available skills for an agent."""
    skills: List[SkillConfig] = []
    skills_dir = agent_path / AGENT_SKILLS_DIR
    if not skills_dir.exists():
        return skills

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        skills.append(
            SkillConfig(
                name=skill_dir.name,
                absolute_path=str(skill_dir),
                mount_path=f"/{AGENT_SKILLS_DIR}/{skill_dir.name}/",
            )
        )
    return skills


def load_asset_bundles(business_unit_path: Path, business_unit_id: str) -> List[AssetBundleBackendConfig]:
    """Load asset bundle backend configuration for a business unit."""
    bundles: List[AssetBundleBackendConfig] = []
    bundles_dir = business_unit_path / ASSET_BUNDLES_DIR
    if not bundles_dir.exists():
        return bundles

    for bundle_dir in bundles_dir.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
            continue
        bundle = load_single_bundle_config(bundle_dir, business_unit_id)
        if bundle is not None:
            bundles.append(bundle)
    return bundles


def load_single_bundle_config(bundle_path: Path, business_unit_id: str) -> Optional[AssetBundleBackendConfig]:
    """Load backend configuration for a single asset bundle."""
    del business_unit_id
    bundle_yaml = bundle_path / ASSET_BUNDLE_CONFIG_FILE
    if not bundle_yaml.exists():
        return None

    try:
        with open(bundle_yaml, "r", encoding="utf-8") as file:
            bundle_config = yaml.safe_load(file) or {}
    except Exception as exc:
        logger.error("Failed to read asset bundle config %s: %s", bundle_yaml, exc)
        return None

    bundle_type = bundle_config.get("bundle_type", "local")
    volumes = load_volumes_config(bundle_path / VOLUMES_DIR) if bundle_type == "local" else []
    return AssetBundleBackendConfig(
        bundle_name=bundle_path.name,
        bundle_type=bundle_type,
        bundle_path=str(bundle_path),
        mount_path=f"/{bundle_path.name}",
        volumes=volumes,
    )


def load_volumes_config(volumes_dir: Path) -> List[Dict[str, Any]]:
    """Load volume config files for a local asset bundle."""
    volumes: List[Dict[str, Any]] = []
    if not volumes_dir.exists():
        return volumes

    for volume_file in volumes_dir.glob("*.yaml"):
        if volume_file.name.startswith("."):
            continue
        try:
            with open(volume_file, "r", encoding="utf-8") as file:
                volume_config = yaml.safe_load(file) or {}
        except Exception as exc:
            logger.error("Failed to read volume config %s: %s", volume_file, exc)
            continue

        volume_type = volume_config.get("volume_type", "local")
        volume_info: Dict[str, Any] = {
            "name": volume_file.stem,
            "volume_type": volume_type,
            "file_path": str(volume_file),
        }
        if volume_type == "local":
            volume_info["storage_location"] = volume_config.get("storage_location", "")
        elif volume_type == "s3":
            volume_info.update(
                {
                    "s3_endpoint": volume_config.get("s3_endpoint"),
                    "s3_bucket": volume_config.get("s3_bucket"),
                    "s3_access_key": volume_config.get("s3_access_key"),
                    "s3_secret_key": volume_config.get("s3_secret_key"),
                }
            )
        volumes.append(volume_info)
    return volumes
