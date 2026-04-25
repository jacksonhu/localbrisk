"""
Agent Service - manages Agent, Memory, Skill, Model, MCP.

On-disk ``agent_spec.yaml`` schema (simplified):

    baseinfo:
      name: ...
      display_name: ...
      description: ...
    instruction: |
      Free-form system prompt template string. Supports runtime-rendered
      placeholders: {{agent_name}}, {{agent_path}}, {{now}}.
    llm_config:
      llm_model: <model-name>
    skills:
      - <enabled-native-skill-name>

Notes:
- Memories are auto-loaded from ``{agent_path}/memories/*.md`` by the runtime;
  there is no per-memory enabled flag in yaml.
- ``skills`` at the top level is the enabled list. The available pool comes
  from scanning the ``skills/`` directory.
- Active model selection is controlled only by ``llm_config.llm_model``.
"""

import logging
import re
import shutil
import tempfile
import venv
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.constants import (
    AGENT_CONFIG_FILE,
    AGENT_MODELS_DIR,
    AGENT_MCPS_DIR,
    AGENT_OUTPUT_DIR,
    AGENT_MEMORIES_DIR,
    AGENT_SKILLS_DIR,
)
from app.models.business_unit import (
    Agent, AgentCreate, AgentUpdate, EntityType,
    AgentLLMConfig,
    Memory, MemoryCreate, MemoryUpdate,
    Model, ModelCreate, ModelUpdate, ModelType,
    MCP, MCPCreate, MCPUpdate, MCPType,
)
from app.services.base_service import BaseService


if TYPE_CHECKING:
    from app.services.business_unit_service import BusinessUnitService

logger = logging.getLogger(__name__)

# Directories initialized under every new agent.
AGENT_BASE_SUBDIRS = (
    AGENT_SKILLS_DIR,
    AGENT_MEMORIES_DIR,
    AGENT_MODELS_DIR,
    AGENT_MCPS_DIR,
    AGENT_OUTPUT_DIR,
)

# Hidden runtime bookkeeping directories under ``output/``.
AGENT_OUTPUT_SYSTEM_SUBDIRS = (
    ".task",
    ".checkpoints",
    ".large_tool_results",
    ".conversation_history",
)

# Default instruction template persisted into new agents. Placeholders are
# rendered by the runtime engine, not here, so the template stays stable.
DEFAULT_INSTRUCTION_TEMPLATE = (
    "You are agent {{agent_name}}\n"
    "Working directory: {{agent_path}}\n"
    "Current date: {{now}}"
)

# Seed content written into ``memories/AGENTS.md`` on agent creation.
DEFAULT_AGENTS_MEMORY = (
    "# Agent Memory\n\n"
    "Capture reusable context, domain facts, and long-term preferences for this agent here.\n"
    "All markdown files under this directory are auto-loaded as memory at runtime.\n"
)


def _normalize_skill_list(value: Any) -> List[str]:
    """Normalize a yaml-loaded ``skills`` value into a deduplicated ordered list.

    Accepts either ``["skill_a", "skill_b"]`` or the legacy object-style
    ``[{"name": "skill_a"}, ...]`` and always returns plain strings.
    """
    if not isinstance(value, list):
        return []
    names: List[str] = []
    seen: set[str] = set()
    for entry in value:
        name: Optional[str]
        if isinstance(entry, dict):
            name = entry.get("name")
        elif isinstance(entry, str):
            name = entry
        else:
            name = None
        if not isinstance(name, str):
            continue
        normalized = name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(normalized)
    return names


class AgentService(BaseService):
    """Agent service class"""
    
    def __init__(self, business_unit_service: "BusinessUnitService"):
        super().__init__()
        self.business_unit_service = business_unit_service
    
    # ==================== Path Methods ====================
    
    def _get_agent_path(self, business_unit_id: str, agent_name: str) -> Path:
        """Get Agent path"""
        bu_path = self.business_unit_service.get_business_unit_path(business_unit_id)
        return self.business_unit_service.get_agents_dir(bu_path) / agent_name
    
    def _get_config_path(self, agent_path: Path) -> Path:
        """Get Agent config file path"""
        return agent_path / AGENT_CONFIG_FILE
    
    def _get_models_dir(self, agent_path: Path) -> Path:
        """Get Models directory under Agent"""
        return agent_path / AGENT_MODELS_DIR
    
    def _get_mcps_dir(self, agent_path: Path) -> Path:
        """Get MCPs directory under Agent"""
        return agent_path / AGENT_MCPS_DIR
    
    def _get_output_dir(self, agent_path: Path) -> Path:
        """Get Output directory under Agent"""
        return agent_path / AGENT_OUTPUT_DIR

    def _get_memory_dir(self, agent_path: Path, create: bool = False) -> Path:
        """Get the memories directory for an agent."""
        memories_dir = agent_path / AGENT_MEMORIES_DIR
        if create:
            memories_dir.mkdir(parents=True, exist_ok=True)
        return memories_dir
    
    # ==================== Agent CRUD ====================
    
    def scan_agents(self, bu_path: Path, business_unit_id: str) -> List[Agent]:
        """Scan Agents"""
        agents_dir = self.business_unit_service.get_agents_dir(bu_path)
        return self._scan_subdirs(agents_dir, lambda p: self._load_agent(business_unit_id, p))
    
    def _load_agent(self, business_unit_id: str, agent_path: Path) -> Optional[Agent]:
        """Load an agent from disk into its DTO representation."""
        config_path = self._get_config_path(agent_path)
        if not config_path.exists():
            logger.debug("Agent config file does not exist, skipping: %s", agent_path.name)
            return None
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, agent_path.name)

        # Scan on-disk resource pool.
        available_skills = self._scan_dir_names(agent_path / AGENT_SKILLS_DIR, is_dir=True)
        memories = self._scan_dir_names(
            agent_path / AGENT_MEMORIES_DIR, suffixes=[".md", ".markdown"]
        )
        models = self._scan_dir_names(agent_path / AGENT_MODELS_DIR, suffixes=[".yaml", ".yml"])
        mcps = self._scan_dir_names(agent_path / AGENT_MCPS_DIR, suffixes=[".yaml", ".yml"])

        # Enabled skills = intersection of declared list and on-disk skills.
        declared_skills = _normalize_skill_list(config.get("skills"))
        enabled_skills = [name for name in declared_skills if name in available_skills]

        # Instruction is a plain string; fall back to the default template when missing.
        instruction = config.get("instruction")
        if not isinstance(instruction, str):
            instruction = DEFAULT_INSTRUCTION_TEMPLATE

        return Agent(
            id=f"{business_unit_id}_agent_{agent_path.name}",
            name=agent_path.name,
            display_name=baseinfo.get("display_name") or agent_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            business_unit_id=business_unit_id,
            entity_type=EntityType.AGENT,
            path=str(agent_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            instruction=instruction,
            llm_config=self._parse_llm_config(config.get("llm_config")),
            skills=enabled_skills,
            available_skills=available_skills,
            memories=memories,
            models=models,
            mcps=mcps,
        )

    def _scan_dir_names(
        self,
        dir_path: Path,
        is_dir: bool = False,
        suffixes: Optional[List[str]] = None,
    ) -> List[str]:
        """Scan a directory and return item names in a stable order."""
        if not dir_path.exists():
            return []

        result: List[str] = []
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith("."):
                continue
            if is_dir and item.is_dir():
                result.append(item.name)
            elif not is_dir and item.is_file():
                if suffixes:
                    if item.suffix.lower() in suffixes:
                        result.append(item.stem)
                else:
                    result.append(item.name)
        return result

    def _parse_llm_config(self, data: Optional[Dict[str, Any]]) -> Optional[AgentLLMConfig]:
        """Parse the ``llm_config`` section from yaml into a typed model."""
        if not data:
            return None
        return AgentLLMConfig(llm_model=data.get("llm_model"))
    
    def list_agents(self, business_unit_id: str) -> List[Agent]:
        """Get Agent list"""
        bu_path = self.business_unit_service.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            return []
        return self.scan_agents(bu_path, business_unit_id)
    
    def get_agent(self, business_unit_id: str, agent_name: str) -> Optional[Agent]:
        """Get Agent"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        if not agent_path.exists():
            return None
        return self._load_agent(business_unit_id, agent_path)
    
    def get_agent_config_content(self, business_unit_id: str, agent_name: str) -> Optional[str]:
        """Get Agent config content"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        return self._read_file(self._get_config_path(agent_path))
    
    def _create_agent_venv(self, agent_path: Path) -> None:
        """Create Python virtual environment (venv) under Agent root directory"""
        venv_path = agent_path / "venv"
        if venv_path.exists():
            return
        try:
            venv.EnvBuilder(with_pip=False).create(str(venv_path))
        except Exception as e:
            raise RuntimeError(f"Failed to create Agent virtual environment: {e}") from e

    def _initialize_agent_directories(self, agent_path: Path) -> None:
        """Initialize the fixed directory layout for a new agent."""
        agent_path.mkdir(parents=True, exist_ok=True)
        for directory in AGENT_BASE_SUBDIRS:
            (agent_path / directory).mkdir(exist_ok=True)

        # Bookkeeping directories live under output/.
        output_dir = agent_path / AGENT_OUTPUT_DIR
        for system_dir in AGENT_OUTPUT_SYSTEM_SUBDIRS:
            (output_dir / system_dir).mkdir(parents=True, exist_ok=True)

        # Seed default memory so the runtime always has something to load.
        agents_md_path = agent_path / AGENT_MEMORIES_DIR / "AGENTS.md"
        if not agents_md_path.exists():
            agents_md_path.write_text(DEFAULT_AGENTS_MEMORY, encoding="utf-8")

    def create_agent(self, business_unit_id: str, data: AgentCreate) -> Agent:
        """Create a new agent with the simplified default config."""
        bu_path = self.business_unit_service.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            raise ValueError(f"BusinessUnit '{business_unit_id}' does not exist")

        agents_dir = self.business_unit_service.get_agents_dir(bu_path)
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_path = agents_dir / data.name
        if agent_path.exists():
            raise ValueError(f"Agent '{data.name}' already exists")

        self._initialize_agent_directories(agent_path)
        self._create_agent_venv(agent_path)

        # Minimal default config: baseinfo + default instruction + empty llm/skills.
        config = {
            "baseinfo": self._create_baseinfo(
                data.name,
                data.display_name,
                data.description,
                data.tags,
                data.owner or "admin",
            ),
            "instruction": DEFAULT_INSTRUCTION_TEMPLATE,
            "llm_config": {"llm_model": ""},
            "skills": [],
        }

        self._save_yaml(self._get_config_path(agent_path), config)
        logger.info("Created agent: %s/%s", business_unit_id, data.name)
        return self._load_agent(business_unit_id, agent_path)

    def update_agent(
        self,
        business_unit_id: str,
        agent_name: str,
        update: AgentUpdate,
    ) -> Optional[Agent]:
        """Partially update an agent's ``agent_spec.yaml``."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        if not agent_path.exists():
            return None

        config_path = self._get_config_path(agent_path)
        config = self._load_yaml(config_path) or {}

        # Update baseinfo (display_name/description/tags + updated_at).
        baseinfo = self._extract_baseinfo(config, agent_path.name)
        baseinfo = self._update_baseinfo(
            baseinfo, update.display_name, update.description, update.tags
        )
        config["baseinfo"] = baseinfo

        # Update instruction string. None means unchanged; empty string clears it.
        if update.instruction is not None:
            config["instruction"] = update.instruction

        # Update llm_config.llm_model.
        if update.llm_config is not None:
            lc = config.setdefault("llm_config", {})
            if update.llm_config.llm_model is not None:
                lc["llm_model"] = update.llm_config.llm_model

        # Update enabled skills list (validated against on-disk skills/).
        if update.skills is not None:
            available = set(self._scan_dir_names(agent_path / AGENT_SKILLS_DIR, is_dir=True))
            seen: set[str] = set()
            filtered: List[str] = []
            for name in update.skills:
                if name in available and name not in seen:
                    filtered.append(name)
                    seen.add(name)
            config["skills"] = filtered

        self._save_yaml(config_path, config)
        logger.info("Updated agent: %s/%s", business_unit_id, agent_name)
        return self._load_agent(business_unit_id, agent_path)
    
    def delete_agent(self, business_unit_id: str, agent_name: str) -> bool:
        """Delete Agent"""
        return self._remove_dir(self._get_agent_path(business_unit_id, agent_name))
    
    # ==================== Model Operations ====================
    
    def list_models(self, business_unit_id: str, agent_name: str) -> List[Model]:
        """Get Model list under Agent"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        models_dir = self._get_models_dir(agent_path)
        if not models_dir.exists():
            return []
        return self._scan_yaml_files(models_dir, lambda p: self._load_model(business_unit_id, agent_name, p))
    
    def _load_model(self, business_unit_id: str, agent_name: str, model_path: Path) -> Optional[Model]:
        """Load Model"""
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path.stem)
        
        return Model(
            id=f"{business_unit_id}_{agent_name}_model_{model_path.stem}",
            name=model_path.stem,
            display_name=baseinfo.get("display_name") or model_path.stem,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            agent_id=f"{business_unit_id}_agent_{agent_name}",
            entity_type=EntityType.MODEL,
            path=str(model_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            model_type=config.get("model_type", "endpoint"),
            enabled=config.get("enabled", False),
            local_provider=config.get("local_provider"),
            local_source=config.get("local_source"),
            volume_reference=config.get("volume_reference"),
            huggingface_repo=config.get("huggingface_repo"),
            huggingface_filename=config.get("huggingface_filename"),
            endpoint_provider=config.get("endpoint_provider"),
            api_base_url=config.get("api_base_url"),
            api_key=config.get("api_key"),
            model_id=config.get("model_id"),
            temperature=config.get("temperature", 0.0),
        )
    
    def get_model(self, business_unit_id: str, agent_name: str, model_name: str) -> Optional[Model]:
        """Get Model"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        return self._load_model(business_unit_id, agent_name, model_path)
    
    def get_model_config_content(self, business_unit_id: str, agent_name: str, model_name: str) -> Optional[str]:
        """Get Model config content"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        return self._read_file(self._get_models_dir(agent_path) / f"{model_name}.yaml")
    
    def create_model(self, business_unit_id: str, agent_name: str, data: ModelCreate) -> Model:
        """Create Model"""
        logger.info(f"Creating Model: {business_unit_id}/{agent_name}/{data.name}, type={data.model_type}")
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        if not agent_path.exists():
            raise ValueError(f"Agent '{agent_name}' does not exist")
        
        models_dir = self._get_models_dir(agent_path)
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / f"{data.name}.yaml"
        if model_path.exists():
            raise ValueError(f"Model '{data.name}' already exists")
        
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        
        config = {
            "baseinfo": baseinfo,
            "model_type": data.model_type.value if hasattr(data.model_type, 'value') else data.model_type,
            "enabled": data.enabled if data.enabled else False,
        }
        
        # Add optional fields
        optional_fields = [
            ("local_provider", data.local_provider),
            ("local_source", data.local_source),
            ("volume_reference", data.volume_reference),
            ("huggingface_repo", data.huggingface_repo),
            ("huggingface_filename", data.huggingface_filename),
            ("endpoint_provider", data.endpoint_provider),
            ("api_base_url", data.api_base_url),
            ("api_key", data.api_key),
            ("model_id", data.model_id),
            ("temperature", data.temperature),
        ]
        
        for key, value in optional_fields:
            if value:
                config[key] = value.value if hasattr(value, 'value') else value
        
        self._save_yaml(model_path, config)
        
        # If this model is enabled, disable others and update llm_model
        if data.enabled:
            self._set_llm_model(business_unit_id, agent_name, data.name)
        
        logger.info(f"Model created successfully: {data.name}")
        return self._load_model(business_unit_id, agent_name, model_path)
    
    def update_model(self, business_unit_id: str, agent_name: str, model_name: str, update: ModelUpdate) -> Optional[Model]:
        """Update Model"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path.stem)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        
        # Update optional fields
        if update.api_key is not None:
            config["api_key"] = update.api_key
        if update.api_base_url is not None:
            config["api_base_url"] = update.api_base_url
        if update.model_id is not None:
            config["model_id"] = update.model_id
        if update.temperature is not None:
            config["temperature"] = update.temperature
        if update.enabled is not None:
            config["enabled"] = update.enabled
            if update.enabled:
                # Enable: set as llm_model
                self._set_llm_model(business_unit_id, agent_name, model_name)
            else:
                # Disable: clear llm_config.llm_model if it's the current model
                self._clear_llm_model_if_matches(business_unit_id, agent_name, model_name)
        
        self._save_yaml(model_path, config)
        return self._load_model(business_unit_id, agent_name, model_path)
    
    def _clear_llm_model_if_matches(
        self, business_unit_id: str, agent_name: str, model_name: str
    ) -> None:
        """If the given model is the current one, clear ``llm_config.llm_model``."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        agent_config_path = self._get_config_path(agent_path)
        agent_config = self._load_yaml(agent_config_path) or {}
        llm_config = agent_config.get("llm_config") or {}
        if llm_config.get("llm_model") == model_name:
            llm_config["llm_model"] = ""
            agent_config["llm_config"] = llm_config
            self._save_yaml(agent_config_path, agent_config)
            logger.info(
                "Cleared llm_model for %s/%s (was %s)",
                business_unit_id,
                agent_name,
                model_name,
            )

    def delete_model(
        self, business_unit_id: str, agent_name: str, model_name: str
    ) -> bool:
        """Delete a model yaml; clear llm_model selection if it matched."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        self._clear_llm_model_if_matches(business_unit_id, agent_name, model_name)
        return self._delete_file(model_path)

    def _set_llm_model(
        self, business_unit_id: str, agent_name: str, model_name: str
    ) -> None:
        """Mark one model as the selected llm_model and disable siblings for UI consistency."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        models_dir = self._get_models_dir(agent_path)

        # Disable sibling models so ``enabled`` stays a single-writer flag.
        if models_dir.exists():
            for model_file in models_dir.glob("*.yaml"):
                if model_file.stem == model_name:
                    continue
                sibling_config = self._load_yaml(model_file) or {}
                if sibling_config.get("enabled"):
                    sibling_config["enabled"] = False
                    self._save_yaml(model_file, sibling_config)

        # Persist the model name into llm_config.llm_model.
        agent_config_path = self._get_config_path(agent_path)
        agent_config = self._load_yaml(agent_config_path) or {}
        llm_config = agent_config.setdefault("llm_config", {})
        llm_config["llm_model"] = model_name
        self._save_yaml(agent_config_path, agent_config)
        logger.info(
            "Set llm_model for %s/%s -> %s", business_unit_id, agent_name, model_name
        )
    
    def enable_model(self, business_unit_id: str, agent_name: str, model_name: str) -> bool:
        """Enable specified Model (disable others)"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        if not model_path.exists():
            return False
        
        config = self._load_yaml(model_path) or {}
        config["enabled"] = True
        self._save_yaml(model_path, config)
        
        self._set_llm_model(business_unit_id, agent_name, model_name)
        return True
    
    # ==================== MCP Operations ====================
    
    def list_mcps(self, business_unit_id: str, agent_name: str) -> List[MCP]:
        """Get Agent 下的 MCP 列表"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        mcps_dir = self._get_mcps_dir(agent_path)
        if not mcps_dir.exists():
            return []
        return self._scan_yaml_files(mcps_dir, lambda p: self._load_mcp(business_unit_id, agent_name, p))
    
    def _load_mcp(self, business_unit_id: str, agent_name: str, mcp_path: Path) -> Optional[MCP]:
        """Load MCP"""
        config = self._load_yaml(mcp_path) or {}
        baseinfo = self._extract_baseinfo(config, mcp_path.stem)
        
        return MCP(
            id=f"{business_unit_id}_{agent_name}_mcp_{mcp_path.stem}",
            name=mcp_path.stem,
            display_name=baseinfo.get("display_name") or mcp_path.stem,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            agent_id=f"{business_unit_id}_agent_{agent_name}",
            entity_type=EntityType.MCP,
            mcp_type=config.get("mcp_type", MCPType.PYTHON_FUNCTION),
            enabled=config.get("enabled", True),
            path=str(mcp_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            python_config=config.get("python_config"),
            server_config=config.get("server_config"),
            api_config=config.get("api_config"),
        )
    
    def get_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str) -> Optional[MCP]:
        """Get MCP"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        mcp_path = self._get_mcps_dir(agent_path) / f"{mcp_name}.yaml"
        if not mcp_path.exists():
            return None
        return self._load_mcp(business_unit_id, agent_name, mcp_path)
    
    def create_mcp(self, business_unit_id: str, agent_name: str, data: MCPCreate) -> MCP:
        """Create MCP"""
        logger.info(f"Creating MCP: {business_unit_id}/{agent_name}/{data.name}, type={data.mcp_type}")
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        if not agent_path.exists():
            raise ValueError(f"Agent '{agent_name}' does not exist")
        
        mcps_dir = self._get_mcps_dir(agent_path)
        mcps_dir.mkdir(parents=True, exist_ok=True)
        
        mcp_path = mcps_dir / f"{data.name}.yaml"
        if mcp_path.exists():
            raise ValueError(f"MCP '{data.name}' already exists")
        
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        
        config = {
            "baseinfo": baseinfo,
            "mcp_type": data.mcp_type.value if hasattr(data.mcp_type, 'value') else data.mcp_type,
            "enabled": data.enabled if data.enabled is not None else True,
        }
        
        # Add config based on type
        if data.python_config:
            config["python_config"] = data.python_config.model_dump() if hasattr(data.python_config, 'model_dump') else data.python_config
        if data.server_config:
            config["server_config"] = data.server_config.model_dump() if hasattr(data.server_config, 'model_dump') else data.server_config
        if data.api_config:
            config["api_config"] = data.api_config.model_dump() if hasattr(data.api_config, 'model_dump') else data.api_config
        
        self._save_yaml(mcp_path, config)
        logger.info(f"MCP created successfully: {data.name}")
        return self._load_mcp(business_unit_id, agent_name, mcp_path)
    
    def update_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str, update: MCPUpdate) -> Optional[MCP]:
        """Update MCP"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        mcp_path = self._get_mcps_dir(agent_path) / f"{mcp_name}.yaml"
        if not mcp_path.exists():
            return None
        
        config = self._load_yaml(mcp_path) or {}
        baseinfo = self._extract_baseinfo(config, mcp_path.stem)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        
        if update.enabled is not None:
            config["enabled"] = update.enabled
        if update.python_config:
            config["python_config"] = update.python_config.model_dump() if hasattr(update.python_config, 'model_dump') else update.python_config
        if update.server_config:
            config["server_config"] = update.server_config.model_dump() if hasattr(update.server_config, 'model_dump') else update.server_config
        if update.api_config:
            config["api_config"] = update.api_config.model_dump() if hasattr(update.api_config, 'model_dump') else update.api_config
        
        self._save_yaml(mcp_path, config)
        return self._load_mcp(business_unit_id, agent_name, mcp_path)
    
    def delete_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str) -> bool:
        """Delete MCP"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        return self._delete_file(self._get_mcps_dir(agent_path) / f"{mcp_name}.yaml")
    
    # ==================== Memory Operations ====================
    #
    # Memories are plain markdown files under ``{agent_path}/memories/``.
    # They are always auto-loaded at runtime; there is no per-memory toggle.

    def _find_memory_file(self, memory_dir: Path, memory_name: str) -> Optional[Path]:
        """Resolve a memory name (with or without ``.md``) to its on-disk file."""
        if not memory_dir.exists():
            return None
        for candidate in (memory_name, f"{memory_name}.md"):
            path = memory_dir / candidate
            if path.exists() and path.is_file():
                return path
        return None

    def _build_memory(self, memory_path: Path) -> Memory:
        """Build a Memory DTO from one markdown file plus its optional metadata."""
        content = self._read_file(memory_path) or ""
        meta_path = memory_path.parent / f".{memory_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}

        return Memory(
            name=memory_path.name,
            display_name=meta.get("display_name") or memory_path.stem,
            description=meta.get("description"),
            tags=meta.get("tags", []),
            entity_type=EntityType.PROMPT,
            content=content,
            # Any markdown under memories/ is auto-loaded at runtime.
            enabled=True,
            path=str(memory_path),
            created_at=self._parse_datetime(meta.get("created_at")),
            updated_at=self._parse_datetime(meta.get("updated_at")),
        )

    def list_memories(
        self, business_unit_id: str, agent_name: str
    ) -> Optional[List[Memory]]:
        """Return all markdown memories under an agent."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dir = self._get_memory_dir(agent_path)
        if not memory_dir.exists():
            return []

        memories: List[Memory] = []
        for item in sorted(memory_dir.iterdir()):
            if not item.is_file() or item.name.startswith("."):
                continue
            if item.suffix.lower() not in {".md", ".markdown"}:
                continue
            memories.append(self._build_memory(item))
        return memories

    def get_memory(
        self, business_unit_id: str, agent_name: str, memory_name: str
    ) -> Optional[Memory]:
        """Return a single memory file."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_path = self._find_memory_file(self._get_memory_dir(agent_path), memory_name)
        if not memory_path:
            return None
        return self._build_memory(memory_path)

    def create_memory(
        self, business_unit_id: str, agent_name: str, data: MemoryCreate
    ) -> bool:
        """Create a new markdown memory under an agent."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dir = self._get_memory_dir(agent_path, create=True)

        file_name = data.name if data.name.endswith(".md") else f"{data.name}.md"
        memory_path = memory_dir / file_name
        if memory_path.exists():
            raise ValueError(f"Memory '{data.name}' already exists")

        self._write_file(memory_path, data.content)
        now = self._now_iso()
        self._save_yaml(
            memory_dir / f".{memory_path.stem}.meta.yaml",
            {"created_at": now, "updated_at": now},
        )
        logger.info(
            "Created memory: %s/%s/%s", business_unit_id, agent_name, memory_path.name
        )
        return True

    def update_memory(
        self,
        business_unit_id: str,
        agent_name: str,
        memory_name: str,
        update: MemoryUpdate,
    ) -> bool:
        """Update a memory file's content and bump its metadata."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_path = self._find_memory_file(self._get_memory_dir(agent_path), memory_name)
        if not memory_path:
            return False

        if update.content is not None:
            self._write_file(memory_path, update.content)

        meta_path = memory_path.parent / f".{memory_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}
        meta["updated_at"] = self._now_iso()
        self._save_yaml(meta_path, meta)
        return True

    def delete_memory(
        self, business_unit_id: str, agent_name: str, memory_name: str
    ) -> bool:
        """Delete a memory file plus its sidecar metadata."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_path = self._find_memory_file(self._get_memory_dir(agent_path), memory_name)
        if not memory_path:
            return False

        memory_path.unlink()
        meta_path = memory_path.parent / f".{memory_path.stem}.meta.yaml"
        if meta_path.exists():
            meta_path.unlink()
        return True

    # ==================== Skill Operations ====================
    #
    # Skills live as subdirectories under ``{agent_path}/skills/``. The top-level
    # ``skills:`` list in ``agent_spec.yaml`` stores which ones are enabled.

    def get_skill(
        self, business_unit_id: str, agent_name: str, skill_name: str
    ) -> Optional[Dict[str, Any]]:
        """Return skill SKILL.md content plus its on-disk path."""
        skill_path = (
            self._get_agent_path(business_unit_id, agent_name)
            / AGENT_SKILLS_DIR
            / skill_name
        )
        if not skill_path.exists() or not skill_path.is_dir():
            return None

        content = self._read_file(skill_path / "SKILL.md") or ""
        return {"content": content, "path": str(skill_path)}

    def delete_skill(
        self, business_unit_id: str, agent_name: str, skill_name: str
    ) -> bool:
        """Delete a skill directory and drop it from the enabled list."""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        skill_path = agent_path / AGENT_SKILLS_DIR / skill_name
        if not skill_path.exists():
            return False

        if skill_path.is_dir():
            shutil.rmtree(skill_path)
        else:
            skill_path.unlink()

        # Remove the skill from the enabled list in agent_spec.yaml if present.
        config_path = self._get_config_path(agent_path)
        if config_path.exists():
            config = self._load_yaml(config_path) or {}
            declared = _normalize_skill_list(config.get("skills"))
            if skill_name in declared:
                config["skills"] = [name for name in declared if name != skill_name]
                self._save_yaml(config_path, config)
        return True
    
    def import_skill_from_zip(self, business_unit_id: str, agent_name: str, zip_file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        """Import Skill from zip file"""
        zip_file_path = Path(zip_file_path)
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        skills_dir = agent_path / AGENT_SKILLS_DIR
        
        if not agent_path.exists():
            return {"success": False, "message": f"Agent '{agent_name}' does not exist"}
        
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if not zip_file_path.exists():
                return {"success": False, "message": f"zip file does not exist: {zip_file_path}"}
            
            if not zipfile.is_zipfile(str(zip_file_path)):
                return {"success": False, "message": "Invalid zip file"}
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                with zipfile.ZipFile(str(zip_file_path), 'r') as zip_ref:
                    if not zip_ref.namelist():
                        return {"success": False, "message": "zip file is empty"}
                    zip_ref.extractall(temp_path)
                
                # Find content directory
                top_level = [item for item in temp_path.iterdir() if not item.name.startswith('__MACOSX') and not item.name.startswith('._')]
                content_dir = top_level[0] if len(top_level) == 1 and top_level[0].is_dir() else temp_path
                
                # Find SKILL.md
                skill_md_path = content_dir / "SKILL.md"
                if not skill_md_path.exists():
                    candidates = [f for f in content_dir.iterdir() if f.name.upper() == "SKILL.MD"]
                    if candidates:
                        skill_md_path = candidates[0]
                    else:
                        return {"success": False, "message": "Invalid Skill package: missing SKILL.md file"}
                
                # Parse frontmatter
                frontmatter = self._parse_skill_frontmatter(skill_md_path)
                if not frontmatter.get('name'):
                    return {"success": False, "message": "Invalid SKILL.md: missing name field"}
                
                skill_name = frontmatter['name']
                skill_description = frontmatter.get('description', "Skill imported from zip package")
                
                skill_path = skills_dir / skill_name
                if skill_path.exists():
                    return {"success": False, "message": f"Skill '{skill_name}' already exists", "skill_name": skill_name}
                
                skill_path.mkdir(parents=True, exist_ok=True)
                
                # Move files
                for item in content_dir.iterdir():
                    if not item.name.startswith('__MACOSX') and not item.name.startswith('._'):
                        shutil.move(str(item), str(skill_path / item.name))
                
                # Create config
                self._save_yaml(skill_path / f"{skill_name}.yaml", {
                    "baseinfo": self._create_baseinfo(skill_name, skill_name, skill_description),
                    "source": "local_import",
                    "import_file": original_filename or zip_file_path.name,
                })
                
                return {
                    "success": True,
                    "skill_name": skill_name,
                    "description": skill_description,
                    "message": f"Skill '{skill_name}' imported successfully",
                    "path": str(skill_path)
                }
                
        except zipfile.BadZipFile:
            return {"success": False, "message": "Corrupted zip file"}
        except Exception as e:
            logger.error(f"Failed to import Skill: {e}", exc_info=True)
            return {"success": False, "message": f"Import failed: {str(e)}"}
    
    def _parse_skill_frontmatter(self, skill_md_path: Path) -> Dict[str, str]:
        """Parse YAML frontmatter from SKILL.md"""
        try:
            content = skill_md_path.read_text(encoding='utf-8')
            match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not match:
                return {}
            
            result = {}
            for line in match.group(1).split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key, value = key.strip(), value.strip()
                    if key and value:
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Failed to parse SKILL.md: {e}")
            return {}
