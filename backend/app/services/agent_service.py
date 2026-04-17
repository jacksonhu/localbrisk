"""
Agent Service - manages Agent, Memory, Skill, Model, MCP
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
AGENT_BASE_SUBDIRS = (
    AGENT_SKILLS_DIR,
    AGENT_MEMORIES_DIR,
    AGENT_MODELS_DIR,
    AGENT_MCPS_DIR,
    AGENT_OUTPUT_DIR,
)
AGENT_OUTPUT_SYSTEM_SUBDIRS = (
    ".task",
    ".checkpoints",
    ".large_tool_results",
    ".conversation_history",
)


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

    def _get_memory_dir_candidates(self, agent_path: Path) -> List[Path]:
        """Get Memory directory candidates (memories only)"""
        memories_dir = agent_path / AGENT_MEMORIES_DIR
        return [memories_dir] if memories_dir.exists() else []

    def _get_primary_memory_dir(self, agent_path: Path, create: bool = False) -> Path:
        """Get primary Memory directory (unified memories)"""
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
        """Load Agent"""
        config_path = self._get_config_path(agent_path)
        if not config_path.exists():
            logger.debug(f"Agent config file does not exist, skipping: {agent_path.name}")
            return None
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, agent_path.name)
        
        # Scan subdirectories
        skills = self._scan_dir_names(agent_path / AGENT_SKILLS_DIR, is_dir=True)
        memories: List[str] = []
        for memory_dir in self._get_memory_dir_candidates(agent_path):
            memories.extend(self._scan_dir_names(memory_dir, suffixes=[".md", ".markdown"]))
        memories = sorted(set(memories))
        models = self._scan_dir_names(agent_path / AGENT_MODELS_DIR, suffixes=[".yaml", ".yml"])
        mcps = self._scan_dir_names(agent_path / AGENT_MCPS_DIR, suffixes=[".yaml", ".yml"])
        
        # Get active model
        active_model = config.get("active_model")
        if not active_model and models:
            # Check if any model has enabled=True
            for model_name in models:
                model_config = self._load_yaml(agent_path / AGENT_MODELS_DIR / f"{model_name}.yaml")
                if model_config and model_config.get("enabled"):
                    active_model = model_name
                    break
        
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
            llm_config=self._parse_llm_config(config.get("llm_config")),
            skills=skills,
            memories=memories,
            models=models,
            mcps=mcps,
            active_model=active_model,
        )
    
    def _scan_dir_names(self, dir_path: Path, is_dir: bool = False, suffixes: List[str] = None) -> List[str]:
        """Scan directory, return name list"""
        if not dir_path.exists():
            return []
        
        result = []
        for item in dir_path.iterdir():
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
    
    def _parse_llm_config(self, data: Dict) -> Optional[AgentLLMConfig]:
        if not data:
            return None
        return AgentLLMConfig(
            llm_model=data.get("llm_model"),
        )
    
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
        """Initialize Agent directory structure."""
        agent_path.mkdir(parents=True, exist_ok=True)
        for directory in AGENT_BASE_SUBDIRS:
            (agent_path / directory).mkdir(exist_ok=True)

        for system_dir in AGENT_OUTPUT_SYSTEM_SUBDIRS:
            (agent_path / system_dir).mkdir(exist_ok=True)
        agents_md_path = agent_path / AGENT_MEMORIES_DIR / "AGENTS.md"
        if not agents_md_path.exists():
            agents_md_path.write_text(build_default_agents_memory(agent_path), encoding="utf-8")

    def create_agent(self, business_unit_id: str, data: AgentCreate) -> Agent:
        """Create Agent"""
        bu_path = self.business_unit_service.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            raise ValueError(f"BusinessUnit '{business_unit_id}' does not exist")
        
        agents_dir = self.business_unit_service.get_agents_dir(bu_path)
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_path = agents_dir / data.name
        if agent_path.exists():
            raise ValueError(f"Agent '{data.name}' already exists")
        
        # Create directory structure
        self._initialize_agent_directories(agent_path)
        self._create_agent_venv(agent_path)
        
        # Create config (simplified: only baseinfo and llm_config)
        config = {
            "baseinfo": self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin"),
            "llm_config": {"llm_model": ""},
        }
        
        self._save_yaml(self._get_config_path(agent_path), config)
        return self._load_agent(business_unit_id, agent_path)
    
    def update_agent(self, business_unit_id: str, agent_name: str, update: AgentUpdate) -> Optional[Agent]:
        """Update Agent"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        if not agent_path.exists():
            return None
        
        config_path = self._get_config_path(agent_path)
        config = self._load_yaml(config_path) or {}
        
        # Update baseinfo
        baseinfo = self._extract_baseinfo(config, agent_path.name)
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        
        # Update llm_config
        if update.llm_config:
            lc = config.setdefault("llm_config", {})
            if update.llm_config.llm_model is not None:
                lc["llm_model"] = update.llm_config.llm_model
        
        self._save_yaml(config_path, config)
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
        
        # If this model is enabled, disable others and update active_model
        if data.enabled:
            self._set_active_model(business_unit_id, agent_name, data.name)
        
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
                # Enable: set as active model
                self._set_active_model(business_unit_id, agent_name, model_name)
            else:
                # Disable: clear active_model and llm_config.llm_model if it's the current active model
                self._clear_active_model_if_matches(business_unit_id, agent_name, model_name)
        
        self._save_yaml(model_path, config)
        return self._load_model(business_unit_id, agent_name, model_path)
    
    def _clear_active_model_if_matches(self, business_unit_id: str, agent_name: str, model_name: str):
        """Clear active_model and llm_config.llm_model if the specified model is the current active model"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        agent_config_path = self._get_config_path(agent_path)
        agent_config = self._load_yaml(agent_config_path) or {}
        
        current_active = agent_config.get("active_model")
        llm_model = agent_config.get("llm_config", {}).get("llm_model", "")
        
        # Check if active_model or llm_config.llm_model matches
        if current_active == model_name or model_name in llm_model:
            agent_config["active_model"] = None
            if "llm_config" in agent_config:
                agent_config["llm_config"]["llm_model"] = ""
            self._save_yaml(agent_config_path, agent_config)
    
    def delete_model(self, business_unit_id: str, agent_name: str, model_name: str) -> bool:
        """Delete Model"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        
        # If it's the current active model, clear active_model
        agent_config_path = self._get_config_path(agent_path)
        agent_config = self._load_yaml(agent_config_path) or {}
        if agent_config.get("active_model") == model_name:
            agent_config["active_model"] = None
            self._save_yaml(agent_config_path, agent_config)
        
        return self._delete_file(model_path)
    
    def _set_active_model(self, business_unit_id: str, agent_name: str, model_name: str):
        """Set active Model (disable others and update llm_config.llm_model)"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        models_dir = self._get_models_dir(agent_path)
        
        # Disable other models
        if models_dir.exists():
            for model_file in models_dir.glob("*.yaml"):
                if model_file.stem != model_name:
                    config = self._load_yaml(model_file) or {}
                    config["enabled"] = False
                    self._save_yaml(model_file, config)
        
        # Update active_model and llm_config.llm_model in Agent config
        agent_config_path = self._get_config_path(agent_path)
        agent_config = self._load_yaml(agent_config_path) or {}
        agent_config["active_model"] = model_name
        
        # Also update llm_config.llm_model
        llm_config = agent_config.setdefault("llm_config", {})
        llm_config["llm_model"] = model_name
        
        self._save_yaml(agent_config_path, agent_config)
    
    def enable_model(self, business_unit_id: str, agent_name: str, model_name: str) -> bool:
        """Enable specified Model (disable others)"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        model_path = self._get_models_dir(agent_path) / f"{model_name}.yaml"
        if not model_path.exists():
            return False
        
        config = self._load_yaml(model_path) or {}
        config["enabled"] = True
        self._save_yaml(model_path, config)
        
        self._set_active_model(business_unit_id, agent_name, model_name)
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
    
    def _get_enabled_memories(self, business_unit_id: str, agent_name: str) -> List[str]:
        """Get enabled Memory names"""
        config = self._load_yaml(self._get_config_path(self._get_agent_path(business_unit_id, agent_name))) or {}
        templates = config.get("instruction", {}).get("user_prompt_templates", [])
        return [p.get("name") if isinstance(p, dict) else p for p in templates]

    def _find_memory_file(self, memory_dirs: List[Path], memory_name: str) -> Optional[Path]:
        """Find file across multiple Memory directories"""
        for memory_dir in memory_dirs:
            for name in [memory_name, f"{memory_name}.md"]:
                path = memory_dir / name
                if path.exists():
                    return path
        return None

    def list_memories(self, business_unit_id: str, agent_name: str) -> Optional[List[Memory]]:
        """Get Memory list"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dirs = self._get_memory_dir_candidates(agent_path)
        if not memory_dirs:
            return []

        enabled = self._get_enabled_memories(business_unit_id, agent_name)
        memories_map: Dict[str, Memory] = {}

        for memory_dir in memory_dirs:
            for item in memory_dir.iterdir():
                if not item.is_file() or item.suffix.lower() not in [".md", ".markdown"] or item.name.startswith("."):
                    continue
                if item.name in memories_map:
                    continue

                content = self._read_file(item) or ""
                meta = self._load_yaml(memory_dir / f".{item.stem}.meta.yaml") or {}

                memories_map[item.name] = Memory(
                    name=item.name,
                    display_name=meta.get("display_name") or item.stem,
                    description=meta.get("description"),
                    tags=meta.get("tags", []),
                    entity_type=EntityType.PROMPT,
                    content=content,
                    enabled=item.name in enabled,
                    path=str(item),
                    created_at=self._parse_datetime(meta.get("created_at")),
                    updated_at=self._parse_datetime(meta.get("updated_at")),
                )

        return [memories_map[name] for name in sorted(memories_map.keys())]

    def get_memory(self, business_unit_id: str, agent_name: str, memory_name: str) -> Optional[Memory]:
        """Get Memory details"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dirs = self._get_memory_dir_candidates(agent_path)
        memory_path = self._find_memory_file(memory_dirs, memory_name)
        if not memory_path:
            return None

        content = self._read_file(memory_path) or ""
        meta = self._load_yaml(memory_path.parent / f".{memory_path.stem}.meta.yaml") or {}
        enabled = self._get_enabled_memories(business_unit_id, agent_name)

        return Memory(
            name=memory_path.name,
            display_name=meta.get("display_name") or memory_path.stem,
            description=meta.get("description"),
            tags=meta.get("tags", []),
            entity_type=EntityType.PROMPT,
            content=content,
            enabled=memory_path.name in enabled,
            path=str(memory_path),
            created_at=self._parse_datetime(meta.get("created_at")),
            updated_at=self._parse_datetime(meta.get("updated_at")),
        )

    def create_memory(self, business_unit_id: str, agent_name: str, data: MemoryCreate) -> bool:
        """Create Memory"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dir = self._get_primary_memory_dir(agent_path, create=True)

        name = data.name if data.name.endswith(".md") else f"{data.name}.md"
        memory_path = memory_dir / name

        if memory_path.exists():
            raise ValueError(f"Memory '{data.name}' already exists")

        self._write_file(memory_path, data.content)
        self._save_yaml(memory_dir / f".{memory_path.stem}.meta.yaml", {"created_at": self._now_iso(), "updated_at": self._now_iso()})
        return True

    def update_memory(self, business_unit_id: str, agent_name: str, memory_name: str, update: MemoryUpdate) -> bool:
        """Update Memory"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dirs = self._get_memory_dir_candidates(agent_path)
        memory_path = self._find_memory_file(memory_dirs, memory_name)
        if not memory_path:
            return False

        if update.content is not None:
            self._write_file(memory_path, update.content)

        meta_path = memory_path.parent / f".{memory_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}
        meta["updated_at"] = self._now_iso()
        self._save_yaml(meta_path, meta)
        return True

    def delete_memory(self, business_unit_id: str, agent_name: str, memory_name: str) -> bool:
        """Delete Memory"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        memory_dirs = self._get_memory_dir_candidates(agent_path)
        memory_path = self._find_memory_file(memory_dirs, memory_name)
        if not memory_path:
            return False

        memory_path.unlink()
        meta_path = memory_path.parent / f".{memory_path.stem}.meta.yaml"
        if meta_path.exists():
            meta_path.unlink()
        return True

    def toggle_memory_enabled(self, business_unit_id: str, agent_name: str, memory_name: str, enabled: bool) -> bool:
        """Toggle Memory enabled status"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        config_path = self._get_config_path(agent_path)

        if not config_path.exists():
            return False

        memory_path = self._find_memory_file(self._get_memory_dir_candidates(agent_path), memory_name)
        if not memory_path:
            return False
        actual_name = memory_path.name

        config = self._load_yaml(config_path) or {}
        inst = config.setdefault("instruction", {})
        templates = inst.get("user_prompt_templates", [])
        names = [p.get("name") if isinstance(p, dict) else p for p in templates]

        if enabled and actual_name not in names:
            templates.append({"name": actual_name})
        elif not enabled:
            templates = [p for p in templates if (p.get("name") if isinstance(p, dict) else p) != actual_name]

        inst["user_prompt_templates"] = templates
        config["baseinfo"] = self._update_baseinfo(self._extract_baseinfo(config, agent_path.name))

        self._save_yaml(config_path, config)
        return True
    
    # ==================== Skill Operations ====================
    
    def get_skill(self, business_unit_id: str, agent_name: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get Skill content and path"""
        skill_path = self._get_agent_path(business_unit_id, agent_name) / AGENT_SKILLS_DIR / skill_name
        if not skill_path.exists() or not skill_path.is_dir():
            return None
        
        content = self._read_file(skill_path / "SKILL.md") or ""
        return {"content": content, "path": str(skill_path)}
    
    def delete_skill(self, business_unit_id: str, agent_name: str, skill_name: str) -> bool:
        """Delete Skill"""
        skill_path = self._get_agent_path(business_unit_id, agent_name) / AGENT_SKILLS_DIR / skill_name
        if not skill_path.exists():
            return False
        
        if skill_path.is_dir():
            shutil.rmtree(skill_path)
        else:
            skill_path.unlink()
        return True
    
    def toggle_skill_enabled(self, business_unit_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        """Toggle Skill enabled status"""
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        config_path = self._get_config_path(agent_path)
        skills_dir = agent_path / AGENT_SKILLS_DIR
        
        if not config_path.exists() or not (skills_dir / skill_name).exists():
            return False
        
        config = self._load_yaml(config_path) or {}
        caps = config.setdefault("capabilities", {})
        skills = caps.get("native_skills", [])
        names = [s.get("name") if isinstance(s, dict) else s for s in skills]
        
        if enabled and skill_name not in names:
            skills.append({"name": skill_name})
        elif not enabled:
            skills = [s for s in skills if (s.get("name") if isinstance(s, dict) else s) != skill_name]
        
        caps["native_skills"] = skills
        config["baseinfo"] = self._update_baseinfo(self._extract_baseinfo(config, agent_path.name))
        
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
