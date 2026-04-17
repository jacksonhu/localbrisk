"""Framework-neutral agent context loading helpers."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

import yaml

from app.core.constants import (
    AGENT_CONFIG_FILE,
    AGENT_MEMORIES_DIR,
    AGENT_MODELS_DIR,
    AGENT_OUTPUT_DIR,
    AGENT_SKILLS_DIR,
    ASSET_BUNDLE_CONFIG_FILE,
    ASSET_BUNDLES_DIR,
    VOLUMES_DIR,
)

logger = logging.getLogger(__name__)


@dataclass
class SkillConfig:
    """Normalized runtime config for one native skill agent."""

    name: str
    skill_path: str
    display_name: str
    description: str
    tool_name: str
    instructions: str


@dataclass
class AssetBundleBackendConfig:
    """Normalized asset bundle configuration for runtime mounting."""

    bundle_name: str
    bundle_type: str
    bundle_path: str
    mount_path: str
    volumes: List[Dict[str, Any]]


@dataclass
class AgentBuildContext:
    """All configuration required to build one runtime agent instance."""

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

    def __post_init__(self) -> None:
        if self.asset_bundles is None:
            self.asset_bundles = []


def resolve_agent_path(agent_path: str | Path) -> Path:
    """Resolve and validate an agent directory path."""
    expanded = os.path.expanduser(str(agent_path))
    path = Path(expanded)
    if not path.exists():
        raise ValueError(f"Agent directory does not exist: {agent_path}")
    if not path.is_dir():
        raise ValueError(f"Agent path is not a directory: {agent_path}")
    return path


def _iter_config_files(root: Path, *, allowed_suffixes: tuple[str, ...], allowed_names: tuple[str, ...] = ()) -> Iterable[Path]:
    """Yield stable, sorted config files under one directory."""
    if not root.exists():
        return

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        lower_name = file_path.name.lower()
        if lower_name in allowed_names or lower_name.endswith(allowed_suffixes):
            yield file_path



def compute_agent_context_fingerprint(agent_path: str | Path, business_unit_id: Optional[str] = None) -> str:
    """Compute a stable fingerprint for files that affect one built agent runtime."""
    path = resolve_agent_path(agent_path)
    digest = hashlib.sha256()
    fingerprint_files: List[Path] = []

    spec_path = path / AGENT_CONFIG_FILE
    if spec_path.exists():
        fingerprint_files.append(spec_path)

    for directory in (path / AGENT_MODELS_DIR, path / "prompts", path / AGENT_MEMORIES_DIR):
        fingerprint_files.extend(
            _iter_config_files(directory, allowed_suffixes=(".yaml", ".yml", ".md", ".markdown"))
        )

    agent_spec = load_agent_spec(path) if spec_path.exists() else {}
    for skill_name in _extract_named_entries(agent_spec.get("capabilities", {}).get("native_skills", [])):
        fingerprint_files.extend(
            _iter_config_files(
                path / AGENT_SKILLS_DIR / skill_name,
                allowed_suffixes=(".yaml", ".yml"),
                allowed_names=("skill.md",),
            )
        )

    if business_unit_id:
        business_unit_path = path.parent.parent
        fingerprint_files.extend(
            _iter_config_files(
                business_unit_path / ASSET_BUNDLES_DIR,
                allowed_suffixes=(".yaml", ".yml"),
            )
        )

    base_path = path.parent.parent if business_unit_id else path
    file_count = 0
    for file_path in fingerprint_files:
        try:
            stat = file_path.stat()
        except FileNotFoundError:
            logger.debug("Skipping vanished config file during fingerprint computation: %s", file_path)
            continue

        try:
            relative_path = file_path.relative_to(base_path).as_posix()
        except ValueError:
            relative_path = str(file_path)

        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(b":")
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(b"\0")
        file_count += 1

    fingerprint = digest.hexdigest()
    logger.debug("Computed agent context fingerprint for %s with %s file(s)", path, file_count)
    return fingerprint



def load_agent_spec(agent_path: Path) -> Dict[str, Any]:
    """Load and validate ``agent_spec.yaml`` from an agent directory."""
    spec_path = agent_path / AGENT_CONFIG_FILE
    if not spec_path.exists():
        raise ValueError(f"{AGENT_CONFIG_FILE} does not exist: {spec_path}")

    with open(spec_path, "r", encoding="utf-8") as file:
        spec = yaml.safe_load(file) or {}

    if not isinstance(spec, dict):
        raise ValueError(f"{AGENT_CONFIG_FILE} must contain a YAML object: {spec_path}")
    return spec


def ensure_output_dir(agent_path: Path) -> str:
    """Ensure the standard agent output directory exists and return its path."""
    output_path = agent_path / AGENT_OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)
    return str(output_path)


def load_model_configs(agent_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load raw model YAML configs keyed by file stem."""
    models: Dict[str, Dict[str, Any]] = {}
    models_dir = agent_path / AGENT_MODELS_DIR
    if not models_dir.exists():
        return models

    for yaml_file in sorted(models_dir.glob("*.y*ml")):
        if yaml_file.name.startswith("."):
            continue
        try:
            with open(yaml_file, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
            if not isinstance(config, dict):
                logger.warning("Skipping model config with non-object payload: %s", yaml_file)
                continue
            models[yaml_file.stem] = config
        except Exception as exc:
            logger.warning("Failed to load model config %s: %s", yaml_file, exc)
    return models


async def load_agent_context(
    agent_path: str,
    business_unit_id: str,
    model_resolver: Optional[Callable[[str, str, str], Awaitable[Optional[Dict[str, Any]]]]] = None,
) -> AgentBuildContext:
    """Load the complete runtime context for one agent directory."""
    path = resolve_agent_path(agent_path)
    agent_spec = load_agent_spec(path)
    agent_name = agent_spec.get("baseinfo", {}).get("name", path.name)
    model_configs = load_model_configs(path)
    model_config = await load_active_model(
        path,
        agent_spec,
        business_unit_id,
        agent_name,
        model_resolver=model_resolver,
        model_configs=model_configs,
    )
    memories = load_memories(path, agent_spec=agent_spec)
    skills = load_skills(path, agent_spec=agent_spec)
    output_path = ensure_output_dir(path)
    asset_bundles = load_asset_bundles(path.parent.parent, business_unit_id)

    logger.info(
        "Loaded agent context: business_unit=%s agent=%s model=%s memories=%s skills=%s bundles=%s",
        business_unit_id,
        agent_name,
        bool(model_config),
        len(memories),
        len(skills),
        len(asset_bundles),
    )

    return AgentBuildContext(
        business_unit_path=str(path.parent.parent),
        agent_path=str(path),
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
    model_configs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Load the active model configuration for an agent."""
    active_model = agent_spec.get("active_model") or agent_spec.get("llm_config", {}).get("llm_model")
    if not active_model:
        logger.warning("Agent %s has no active model configured", agent_name)
        return None

    resolved_model_configs = model_configs if model_configs is not None else load_model_configs(agent_path)
    if active_model in resolved_model_configs:
        return resolved_model_configs[active_model]

    model_file = agent_path / AGENT_MODELS_DIR / f"{active_model}.yaml"
    if model_file.exists():
        with open(model_file, "r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return payload if isinstance(payload, dict) else None

    if model_resolver is None:
        logger.warning(
            "Active model '%s' for %s/%s was not found locally and no resolver is configured",
            active_model,
            business_unit_id,
            agent_name,
        )
        return None

    try:
        return await model_resolver(business_unit_id, agent_name, active_model)
    except Exception as exc:
        logger.error(
            "Failed to resolve model config for %s/%s/%s: %s",
            business_unit_id,
            agent_name,
            active_model,
            exc,
        )
        return None


def _extract_named_entries(entries: Any) -> List[str]:
    """Extract ordered names from a config list containing strings or objects."""
    if not isinstance(entries, list):
        return []

    names: List[str] = []
    seen: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = entry
        if not isinstance(name, str):
            continue
        normalized = name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(normalized)
    return names


def _iter_memory_files(memories_dir: Path) -> Iterable[Path]:
    """Yield visible markdown memory files in stable order."""
    for file_path in sorted(memories_dir.iterdir()):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        if file_path.suffix.lower() not in {".md", ".markdown"}:
            continue
        yield file_path


def _build_memory_lookup(memories_dir: Path) -> Dict[str, Path]:
    """Build a lookup that accepts both file names and stem names."""
    lookup: Dict[str, Path] = {}
    for memory_file in _iter_memory_files(memories_dir):
        lookup.setdefault(memory_file.name.lower(), memory_file)
        lookup.setdefault(memory_file.stem.lower(), memory_file)
    return lookup


def _iter_memory_lookup_keys(memory_name: str) -> Iterable[str]:
    """Yield normalized lookup keys for one configured memory entry."""
    normalized = memory_name.strip()
    if not normalized:
        return

    yielded: set[str] = set()
    candidates = [normalized.lower()]
    suffix = Path(normalized).suffix.lower()
    if suffix in {".md", ".markdown"}:
        candidates.append(Path(normalized).stem.lower())
    else:
        candidates.extend((f"{normalized}.md".lower(), f"{normalized}.markdown".lower()))

    for candidate in candidates:
        if candidate in yielded:
            continue
        yielded.add(candidate)
        yield candidate


def _resolve_configured_memory_files(memories_dir: Path, configured_names: List[str]) -> List[str]:
    """Resolve configured memory names into mounted memory paths."""
    memory_lookup = _build_memory_lookup(memories_dir)
    resolved: List[str] = []
    for memory_name in configured_names:
        for lookup_key in _iter_memory_lookup_keys(memory_name):
            memory_file = memory_lookup.get(lookup_key)
            if memory_file is not None:
                resolved.append(f"/{AGENT_MEMORIES_DIR}/{memory_file.name}")
                break
        else:
            logger.warning("Configured memory '%s' was not found under %s", memory_name, memories_dir)
    return resolved


def load_memories(agent_path: Path, agent_spec: Optional[Dict[str, Any]] = None) -> List[str]:
    """Load enabled memory files for an agent."""
    memories_dir = agent_path / AGENT_MEMORIES_DIR
    if not memories_dir.exists():
        return []

    configured_names = _extract_named_entries(
        (agent_spec or {}).get("instruction", {}).get("user_prompt_templates", [])
    )
    if configured_names:
        return _resolve_configured_memory_files(memories_dir, configured_names)

    memories: List[str] = []
    for markdown_file in sorted(list(memories_dir.glob("*.md")) + list(memories_dir.glob("*.markdown"))):
        if markdown_file.name.startswith("."):
            continue
        memory_name = markdown_file.stem
        metadata_file = memories_dir / f".{memory_name}.meta.yaml"
        metadata: Dict[str, Any] = {}
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as file:
                metadata = yaml.safe_load(file) or {}
        if not metadata.get("enabled", True):
            continue
        memories.append(f"/{AGENT_MEMORIES_DIR}/{markdown_file.name}")
    return memories


def load_skills(agent_path: Path, agent_spec: Optional[Dict[str, Any]] = None) -> List[SkillConfig]:
    """Load only native skills explicitly enabled in ``agent_spec.yaml``."""
    skills_dir = agent_path / AGENT_SKILLS_DIR
    if not skills_dir.exists():
        return []

    configured_names = _extract_named_entries((agent_spec or {}).get("capabilities", {}).get("native_skills", []))
    if not configured_names:
        return []

    skills: List[SkillConfig] = []
    for skill_name in configured_names:
        skill_dir = skills_dir / skill_name
        if not skill_dir.is_dir():
            logger.warning("Configured native skill directory was not found: %s", skill_dir)
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.warning("Skipping native skill without SKILL.md: %s", skill_dir)
            continue

        skill_front_matter, instructions = _read_skill_markdown(skill_md)
        if not instructions:
            logger.warning("Skipping native skill with empty SKILL.md body: %s", skill_md)
            continue

        skill_config = _load_skill_directory_config(skill_dir, skill_name)
        baseinfo = skill_config.get("baseinfo", {}) if isinstance(skill_config, dict) else {}
        display_name = _first_text(
            baseinfo.get("display_name"),
            skill_config.get("display_name") if isinstance(skill_config, dict) else None,
            skill_name,
        )
        description = _first_text(
            skill_front_matter.get("description"),
            f"Use the native skill '{display_name}' when the delegated task matches this capability.",
        )
        tool_name = _first_text(
            baseinfo.get("tool_name"),
            skill_config.get("tool_name") if isinstance(skill_config, dict) else None,
            _build_skill_tool_name(skill_name),
        )
        skills.append(
            SkillConfig(
                name=skill_name,
                skill_path=str(skill_dir),
                display_name=display_name,
                description=description,
                tool_name=tool_name,
                instructions=instructions,
            )
        )
    return skills


def _read_skill_markdown(skill_md: Path) -> tuple[Dict[str, Any], str]:
    """Read one SKILL.md file and split front matter metadata from body instructions."""
    raw_content = skill_md.read_text(encoding="utf-8").lstrip("\ufeff")
    if not raw_content.strip():
        return {}, ""

    lines = raw_content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw_content.strip()

    closing_index: Optional[int] = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        logger.warning("Failed to find closing front matter marker in %s", skill_md)
        return {}, raw_content.strip()

    front_matter_text = "\n".join(lines[1:closing_index]).strip()
    body = "\n".join(lines[closing_index + 1 :]).strip()
    if not front_matter_text:
        return {}, body

    try:
        payload = yaml.safe_load(front_matter_text) or {}
    except Exception as exc:
        logger.warning("Failed to parse SKILL.md front matter %s: %s", skill_md, exc)
        return {}, body

    if not isinstance(payload, dict):
        logger.warning("Skipping non-object SKILL.md front matter in %s", skill_md)
        return {}, body

    return payload, body


def _load_skill_directory_config(skill_dir: Path, skill_name: str) -> Dict[str, Any]:
    """Load one optional skill YAML config file from the skill directory."""
    candidate_paths = [
        skill_dir / f"{skill_name}.yaml",
        skill_dir / f"{skill_name}.yml",
        *sorted(skill_dir.glob("*.yaml")),
        *sorted(skill_dir.glob("*.yml")),
    ]
    seen: set[Path] = set()
    for candidate in candidate_paths:
        if candidate in seen or not candidate.exists() or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            with open(candidate, "r", encoding="utf-8") as file:
                payload = yaml.safe_load(file) or {}
        except Exception as exc:
            logger.warning("Failed to load native skill config %s: %s", candidate, exc)
            continue
        if isinstance(payload, dict):
            return payload
        logger.warning("Skipping native skill config with non-object payload: %s", candidate)
    return {}


def _first_text(*values: Any) -> str:
    """Return the first non-empty text value from a candidate list."""
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            return normalized
    return ""


def _build_skill_tool_name(skill_name: str) -> str:
    """Build a stable SDK tool name for one native skill."""
    normalized_chars = [char.lower() if char.isalnum() else "_" for char in skill_name.strip()]
    normalized = "".join(normalized_chars).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    if not normalized:
        normalized = "native_skill"
    if normalized[0].isdigit():
        normalized = f"skill_{normalized}"
    return f"skill_{normalized}"


def load_asset_bundles(business_unit_path: Path, business_unit_id: str) -> List[AssetBundleBackendConfig]:
    """Load asset bundle configuration for a business unit."""
    bundles: List[AssetBundleBackendConfig] = []
    bundles_dir = business_unit_path / ASSET_BUNDLES_DIR
    if not bundles_dir.exists():
        return bundles

    for bundle_dir in sorted(bundles_dir.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
            continue
        bundle = load_single_bundle_config(bundle_dir, business_unit_id)
        if bundle is not None:
            bundles.append(bundle)
    return bundles


def load_single_bundle_config(bundle_path: Path, business_unit_id: str) -> Optional[AssetBundleBackendConfig]:
    """Load configuration for a single asset bundle."""
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

    if not isinstance(bundle_config, dict):
        logger.warning("Skipping asset bundle with non-object payload: %s", bundle_yaml)
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

    for volume_file in sorted(volumes_dir.glob("*.yaml")):
        if volume_file.name.startswith("."):
            continue
        try:
            with open(volume_file, "r", encoding="utf-8") as file:
                volume_config = yaml.safe_load(file) or {}
        except Exception as exc:
            logger.error("Failed to read volume config %s: %s", volume_file, exc)
            continue

        if not isinstance(volume_config, dict):
            logger.warning("Skipping volume config with non-object payload: %s", volume_file)
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


__all__ = [
    "AgentBuildContext",
    "AssetBundleBackendConfig",
    "SkillConfig",
    "compute_agent_context_fingerprint",
    "ensure_output_dir",
    "load_active_model",
    "load_agent_context",
    "load_agent_spec",
    "load_asset_bundles",
    "load_memories",
    "load_model_configs",
    "load_single_bundle_config",
    "load_skills",
    "load_volumes_config",
    "resolve_agent_path",
]
