"""
Agent Engine Implementation Based on DeepAgents SDK

Builds intelligent agents using LangChain DeepAgents SDK, supports:
- Loading config from agent_spec.yaml
- Loading skills, memories, models directory configs
- Multiple system prompt concatenation
- FilesystemBackend filesystem backend

Dependencies:
- pyyaml (required)
- langchain-core (required for building Agent)
- langchain-openai (required for OpenAI-compatible API)
- deepagents (required for building Agent)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass
import yaml
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.cache.memory import InMemoryCache
from app.core.constants import ASSET_BUNDLES_DIR, ASSET_BUNDLE_CONFIG_FILE, VOLUMES_DIR, AGENT_SKILLS_DIR, AGENT_MEMORIES_DIR, \
    AGENT_OUTPUT_DIR, TABLES_DIR

from .subagents import create_builtin_subagents

# Type-checking only imports
if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# ============================================================
# Dependency Imports
# ============================================================
# Record import status and errors for diagnostics for diagnostics
_LANGCHAIN_AVAILABLE = False
_DEEPAGENTS_AVAILABLE = False
_LANGCHAIN_IMPORT_ERROR: Optional[str] = None
_DEEPAGENTS_IMPORT_ERROR: Optional[str] = None

# Import langchain-core
try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    _LANGCHAIN_AVAILABLE = True
except ImportError as e:
    BaseChatModel = None
    BaseTool = None
    _LANGCHAIN_IMPORT_ERROR = str(e)

# Import deepagents and langgraph
try:
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend, LocalShellBackend, CompositeBackend
    from langgraph.graph.state import CompiledStateGraph
    _DEEPAGENTS_AVAILABLE = True
except ImportError as e:
    create_deep_agent = None
    FilesystemBackend = None
    LocalShellBackend = None
    CompositeBackend = None
    CompiledStateGraph = None
    _DEEPAGENTS_IMPORT_ERROR = str(e)


def get_python_info() -> Dict[str, Any]:
    """Get current Python environment info for diagnostics"""
    return {
        "executable": sys.executable,
        "version": sys.version,
        "prefix": sys.prefix,
        "path": sys.path[:5],  # only first 5 paths
    }


def check_dependencies(raise_error: bool = True) -> bool:
    """Check dependencies are available
    
    Args:
        raise_error: whether to raise an exception if dependencies are unavailable
        
    Returns:
        bool: whether all dependencies are available
    """
    missing = []
    errors = []
    
    if not _LANGCHAIN_AVAILABLE:
        missing.append("langchain-core")
        if _LANGCHAIN_IMPORT_ERROR:
            errors.append(f"langchain-core: {_LANGCHAIN_IMPORT_ERROR}")
            
    if not _DEEPAGENTS_AVAILABLE:
        missing.append("deepagents")
        if _DEEPAGENTS_IMPORT_ERROR:
            errors.append(f"deepagents: {_DEEPAGENTS_IMPORT_ERROR}")
    
    if missing and raise_error:
        python_info = get_python_info()
        error_msg = (
            f"Missing required dependencies: {', '.join(missing)}.\n"
            f"Import errors: {'; '.join(errors)}\n"
            f"Current Python: {python_info['executable']}\n"
            f"Please ensure you are using the correct virtual environment, or run: pip install {' '.join(missing)}"
        )
        raise ImportError(error_msg)
    
    return len(missing) == 0


def log_dependency_status():
    """Log dependency status (called at startup)"""
    python_info = get_python_info()
    logger.info(f"Python environment: {python_info['executable']}")
    logger.info(f"Python version: {python_info['version'].split()[0]}")
    logger.info(f"langchain-core available: {_LANGCHAIN_AVAILABLE}")
    logger.info(f"deepagents available: {_DEEPAGENTS_AVAILABLE}")
    
    if _LANGCHAIN_IMPORT_ERROR:
        logger.warning(f"langchain-core import error: {_LANGCHAIN_IMPORT_ERROR}")
    if _DEEPAGENTS_IMPORT_ERROR:
        logger.warning(f"deepagents import error: {_DEEPAGENTS_IMPORT_ERROR}")


# Log dependency status at module load time
log_dependency_status()


@dataclass
class SkillConfig:
    """Skill config
    
    Describes config for a single skill
    """
    name: str                                # Skill name
    absolute_path: str                       # Absolute path to skill directory
    mount_path: str                          # Mount path (POSIX format for backend routing)


@dataclass
class AssetBundleBackendConfig:
    """Asset Bundle backend config
    
    Describes backend config for a single asset bundle
    """
    bundle_name: str                         # Bundle name
    bundle_type: str                         # Bundle type: local or external
    bundle_path: str                         # Bundle directory path
    mount_path: str                          # Mount path (used for routing)
    volumes: List[Dict[str, Any]]            # Volume config list


@dataclass
class AgentBuildContext:
    """Agent build context
    
    Contains all config needed to build an Agent
    """
    business_unit_path: str                  # Business Unit directory path
    agent_path: str                          # Agent directory path
    agent_name: str                          # Agent name
    business_unit_id: str                    # Business Unit ID
    agent_spec: Dict[str, Any]               # agent_spec.yaml content
    model_config: Optional[Dict[str, Any]]   # Active model config
    memories: List[Dict[str, Any]]           # All enabled memory configs
    skills: List[SkillConfig]                # Skill config list
    output_path: str                       # Working directory path
    asset_bundles: List[AssetBundleBackendConfig] = None  # Asset Bundle backend config list
    
    def __post_init__(self):
        if self.asset_bundles is None:
            self.asset_bundles = []


class DeepAgentsEngine:
    """Agent engine based on DeepAgents SDK
    
    Loads config from Agent dir and creates DeepAgent instances
    """
    
    def __init__(self):
        logger.info("Initializing DeepAgentsEngine")
        self._llm_factory = None
        self._model_resolver: Optional[callable] = None
        self._checkpointer_contexts: Dict[int, Any] = {}
    
    def _ensure_llm_factory(self):
        """Ensure LLM factory is initialized"""
        if self._llm_factory is None:
            if not _LANGCHAIN_AVAILABLE:
                raise ImportError("langchain-core required: pip install langchain-core")
            from ..llm.client_factory import get_llm_client_factory
            self._llm_factory = get_llm_client_factory()
        return self._llm_factory
    
    def set_model_resolver(self, resolver: callable):
        """Set model resolver
        
        Args:
            resolver: async function, accepts (business_unit_id, agent_name, model_name) returns model config
        """
        self._model_resolver = resolver
        if self._llm_factory:
            self._llm_factory.set_model_resolver(resolver)
        logger.debug("Model resolver set")
    
    async def build_agent(
        self,
        agent_path: str,
        business_unit_id: str,
        tools: Optional[List] = None,
        debug: bool = False,
    ):
        """Build  DeepAgent instance
        
        Args:
            agent_path: Agent directory path (e.g., ~/.localbrisk/App_Data/Catalogs/myunit/agents/Data_analyst)
            business_unit_id: Business Unit ID
            tools: Additional custom tools (List[BaseTool])
            debug: Whether to enable debug mode
            
        Returns:
            CompiledStateGraph: Compiled DeepAgent instance
            
        Raises:
            ImportError: If required dependencies are missing
        """
        # Check dependencies
        check_dependencies(raise_error=True)
        
        logger.info(f"Building Agent: path={agent_path}, business_unit={business_unit_id}")
        
        # 1. Load Agent config context
        context = await self._load_agent_context(agent_path, business_unit_id)
        
        # 2. Create LLM client
        llm_client = await self._create_llm_client(context)
        
        # 3. Build system prompt (concatenate all enabled prompts)
        system_prompt = self._load_base_system_prompt()
        system_prompt=system_prompt.replace("{{cwd}}", context.agent_path)
        
        # 4. Create CompositeBackend filesystem backend (contains skills 和 asset bundles Mount)
        backend = self._create_backend(context)
        # 5. Collect skill mount paths (POSIX 格式, 相对于 backend)
        # skills 参数需要的是相对于 backend 的路径, 如 ["/skills/python_expert/", "/skills/data_analyst/"]
        skills_mount_paths = None
        if context.skills:
            skills_mount_paths = [skill.mount_path for skill in context.skills]
            logger.debug(f"skills:: {skills_mount_paths}")
        
        # 6. Merge tools (built-in + external custom tools)
        from agent_engine.tools import get_builtin_tools
        task_root = str(Path(context.output_path) / ".task")
        Path(task_root).mkdir(parents=True, exist_ok=True)
        builtin_tools = get_builtin_tools(backend=backend, task_root=task_root)
        all_tools = builtin_tools + (tools if tools else [])

        # 7. Initialize Checkpointer (unified async)

        checkpoint_root = str(Path(context.output_path) / ".checkpoints")
        Path(checkpoint_root).mkdir(parents=True, exist_ok=True)
        checkpoint_db = str(Path(checkpoint_root) / "checkpoints.sqlite")
        checkpointer_cm = AsyncSqliteSaver.from_conn_string(checkpoint_db)
        checkpointer = await self._enter_checkpointer_context(checkpointer_cm)
        checkpointer = InMemorySaver()
        try:
            # 8. Create built-in sub-Agents (reuse parent sandbox backend / tools / model)
            subagents = create_builtin_subagents(
                parent_model=llm_client,
                parent_tools=all_tools,
                parent_backend=backend,
            )

            # 9. Create DeepAgent (Markdown direct output)
            logger.info(
                f"Create DeepAgent: model={type(llm_client).__name__}, skills={len(context.skills) if context.skills else 0}, "
                f"memories={len(context.memories)}, subagents={len(subagents)}"
            )

            create_kwargs = {
                "model": llm_client,
                "tools": all_tools if all_tools else None,
                "system_prompt": system_prompt if system_prompt else None,
                "skills": ["./skills/"],
                "backend": backend,
                "memory": context.memories,
                "debug": debug,
                "checkpointer": checkpointer,
                "name": context.agent_name,
                "cache": InMemoryCache(),
                "subagents": subagents,
            }

            try:
                agent = create_deep_agent(**create_kwargs)
            except TypeError as e:
                if "subagents" not in str(e):
                    raise
                logger.warning("Current deepagents version doesn't support subagents parameter, falling back to no-subagent mode: %s", e)
                create_kwargs.pop("subagents", None)
                agent = create_deep_agent(**create_kwargs)
        except Exception:
            await self._exit_checkpointer_context(checkpointer_cm)
            raise

        self._checkpointer_contexts[id(agent)] = checkpointer_cm
        logger.info(f"Agent built successfully: {context.agent_name}")
        return agent

    async def _enter_checkpointer_context(self, cm: Any) -> Any:
        """Compatible with sync/async checkpointer context manager."""
        aenter = getattr(cm, "__aenter__", None)
        if callable(aenter):
            return await aenter()
        enter = getattr(cm, "__enter__", None)
        if callable(enter):
            return enter()
        return cm

    async def _exit_checkpointer_context(self, cm: Any) -> None:
        """Compatible with sync/async checkpointer context manager."""
        aexit = getattr(cm, "__aexit__", None)
        if callable(aexit):
            await aexit(None, None, None)
            return
        exit_ = getattr(cm, "__exit__", None)
        if callable(exit_):
            exit_(None, None, None)

    async def close_agent_resources(self, agent: Any) -> None:
        """Close resources created during Agent build phase (e.g., checkpointer context)"""
        cm = self._checkpointer_contexts.pop(id(agent), None)
        if cm is None:
            return
        try:
            await self._exit_checkpointer_context(cm)
        except Exception as e:
            logger.warning(f"Failed to close checkpointer: {e}")
    
    async def _load_agent_context(
        self,
        agent_path: str,
        business_unit_id: str
    ) -> AgentBuildContext:
        """Load Agent config context
        
        Load all config from Agent directory
        
        Args:
            agent_path: Agent directory path
            business_unit_id: Business Unit ID
            
        Returns:
            AgentBuildContext: config context
        """
        agent_path = os.path.expanduser(agent_path)
        path = Path(agent_path)
        
        if not path.exists():
            raise ValueError(f"Agent directory does not exist: {agent_path}")
        
        # 1. Load agent_spec.yaml
        spec_path = path / "agent_spec.yaml"
        if not spec_path.exists():
            raise ValueError(f"agent_spec.yaml does not exist: {spec_path}")
        
        with open(spec_path, 'r', encoding='utf-8') as f:
            agent_spec = yaml.safe_load(f)
        
        agent_name = agent_spec.get("baseinfo", {}).get("name", path.name)
        logger.info(f"Loading Agent 配置: name={agent_name}")
        
        # 2. Load激活的model config
        model_config = await self._load_active_model(path, agent_spec, business_unit_id, agent_name)
        
        # 3. Load all enabled memories
        memories = self._load_memories(path)
        
        # 4. Load all skill paths
        skills = self._load_skills(path)
        
        # 5. Determine output path
        output_path = str(path / "output")
        os.makedirs(output_path, exist_ok=True)
        
        # 6. Load asset bundles backend config
        asset_bundles = self._load_asset_bundles(path.parent.parent, business_unit_id)
        
        return AgentBuildContext(
            business_unit_path=str(path.parent.parent),
            agent_path=agent_path,
            agent_name=agent_name,
            business_unit_id=business_unit_id,
            agent_spec=agent_spec,
            model_config=model_config,
            memories=memories,
            skills=skills,
            output_path=output_path,
            asset_bundles=asset_bundles
        )
    
    async def _load_active_model(
        self,
        agent_path: Path,
        agent_spec: Dict[str, Any],
        business_unit_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load active model config
        
        Args:
            agent_path: Agent directory path
            agent_spec: agent_spec.yaml content
            business_unit_id: Business Unit ID
            agent_name: Agent name
            
        Returns:
            model config dict
        """
        # Get active model name
        active_model = agent_spec.get("active_model")
        if not active_model:
            # Try to get from llm_config
            llm_config = agent_spec.get("llm_config", {})
            active_model = llm_config.get("llm_model")
        
        if not active_model:
            logger.warning(f"Agent {agent_name} has no active model configured")
            return None
        
        logger.info(f"Loading active model: {active_model}")
        
        # First try loading from local models directory
        models_dir = agent_path / "models"
        if models_dir.exists():
            model_file = models_dir / f"{active_model}.yaml"
            if model_file.exists():
                logger.debug(f"Loading model config from local: {model_file}")
                with open(model_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        
        # If not found locally, use model_resolver
        if self._model_resolver:
            try:
                return await self._model_resolver(business_unit_id, agent_name, active_model)
            except Exception as e:
                logger.error(f"Failed to resolve model config: {e}")
        
        return None
    
    def _load_memories(self, agent_path: Path) -> List[Dict[str, Any]]:
        """Load all enabled memories

        Load all .md files and metadata from memories directory

        Args:
            agent_path: Agent directory path

        Returns:
            enabled memory config list
        """
        memories = []
        memories_dir = agent_path / AGENT_MEMORIES_DIR

        if not memories_dir.exists():
            logger.debug(f"memories directory does not exist: {memories_dir}")
            return memories

        # Iterate all .md files (excluding files starting with .)
        for md_file in sorted(memories_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue

            memory_name = md_file.stem
            logger.debug(f"Loading  memory: {memory_name}")

            # Try reading metadata file
            meta_file = memories_dir / f".{memory_name}.meta.yaml"
            meta = {}
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f) or {}

            # Check if enabled (enabled by default)
            if not meta.get("enabled", True):
                logger.debug(f"memory {memory_name} disabled, skipping")
                continue

            memories.append(f"/memories/{memory_name}.md")
        logger.info(f"Loaded {len(memories)}  memories")
        return memories
    
    def _load_skills(self, agent_path: Path) -> List[SkillConfig]:
        """Load all skill configs
        
        Scan skills directory, return skill config list containing SKILL.md
        
        Args:
            agent_path: Agent directory path
            
        Returns:
            skill config list (SkillConfig)
        """
        skills = []
        skills_dir = agent_path / "skills"
        
        if not skills_dir.exists():
            logger.debug(f"skills directory does not exist: {skills_dir}")
            return skills
        
        # Iterate subdirectories under skills directory
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            # Check if SKILL.md exists
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                skill_name = skill_dir.name
                # Mount path uses POSIX format: /skills/{skill_name}/
                mount_path = f"/{AGENT_SKILLS_DIR}/{skill_name}/"
                
                skill_config = SkillConfig(
                    name=skill_name,
                    absolute_path=str(skill_dir),
                    mount_path=mount_path
                )
                skills.append(skill_config)
                logger.debug(f"Found skill: {skill_name} -> {mount_path}")
            else:
                logger.debug(f"directory {skill_dir.name} missing SKILL.md, skipping")
        
        logger.info(f"Loaded {len(skills)}  skills")
        return skills
    
    async def _create_llm_client(self, context: AgentBuildContext):
        """Create LLM client
        
        Args:
            context: Agent build context
            
        Returns:
            LangChain BaseChatModel instance
        """
        if not context.model_config:
            logger.warning(f"Agent {context.agent_name} has no model configured, will use default")
            return None
        
        # Lazy import
        from ..core.config import AgentRuntimeConfig, LLMRuntimeConfig
        
        # Extract LLM runtime config from agent_spec
        llm_runtime_config = LLMRuntimeConfig.from_agent_llm_config(
            context.agent_spec.get("llm_config", {})
        )
        
        # Read temperature from model_config (if available)
        model_temperature = context.model_config.get("temperature") or context.model_config.get("tempreture")
        if model_temperature is not None:
            llm_runtime_config.temperature = float(model_temperature)
        
        # Create AgentRuntimeConfig
        runtime_config = AgentRuntimeConfig(
            agent_name=context.agent_name,
            business_unit_id=context.business_unit_id,
            agent_path=context.agent_path,
            llm_config=llm_runtime_config
        )
        
        # Ensure LLM factory is initialized
        llm_factory = self._ensure_llm_factory()
        if self._model_resolver:
            llm_factory.set_model_resolver(self._model_resolver)
        
        # Use factory to create client
        return await llm_factory.create_client(runtime_config, context.model_config)
    
    
    def _load_base_system_prompt(self) -> str:
        """Load base system prompt template
        
        从 AGENTS.md 文件读取base system prompt template, 该模板contains {user_custom_prompt} 占位符
        
        Returns:
            base system prompt template string
        """
        # AGENTS.md 位于当前文件所在directory
        engine_dir = Path(__file__).parent
        agents_md_path = engine_dir / "AGENTS.md"
        try:
            content = agents_md_path.read_text(encoding="utf-8")
            logger.debug(f"Loading base system prompt template: {agents_md_path}, length {len(content)}  characters")
            return content
        except Exception as e:
            logger.error(f"Failed to read  AGENTS.md failed: {e}")
            raise Exception(f"Failed to read AGENTS.md: {e}")

    def _create_backend(self, context: AgentBuildContext):
        """Create CompositeBackend filesystem backend
        
        Creates a composite backend containing:
        1. LocalShellBackend - default backend, allows reading/writing files and executing commands under output
        2. FilesystemBackend - Mount skills directory (只读)
        3. 多个 FilesystemBackend(virtual_mode=True) - Mount各个 asset bundle 的文档directory (只读)
        
        Args:
            context: Agent build context
            
        Returns:
            CompositeBackend or FilesystemBackend instance
        """
        output = context.output_path
        has_memories = context.memories and len(context.memories) > 0
        # If no skills or asset bundles, or CompositeBackend unavailable, fall back to simple FilesystemBackend
        has_skills = context.skills and len(context.skills) > 0
        has_bundles = context.asset_bundles and len(context.asset_bundles) > 0

        if (not has_skills and not has_bundles and not has_memories) or CompositeBackend is None or LocalShellBackend is None:
            logger.info(f"Creating  FilesystemBackend: root_dir={output}")
            return FilesystemBackend(root_dir=output)
        
        logger.info(f"Creating  CompositeBackend: output={output}, skills={len(context.skills) if has_skills else 0}, asset_bundles={len(context.asset_bundles) if has_bundles else 0}")

        
        # 2. Build route configuration
        routes = {}
        routes["/large_tool_results/"] = FilesystemBackend(root_dir=f"{output}/.large_tool_results", virtual_mode=True)
        routes["/conversation_history/"] = FilesystemBackend(root_dir=f"{output}/.conversation_history", virtual_mode=True)
        if has_memories:
            memories_dir = f"{context.agent_path}/{AGENT_MEMORIES_DIR}"
            if os.path.exists(memories_dir):
                routes[f"/memories/"] = FilesystemBackend(
                    root_dir=memories_dir,
                    virtual_mode=True
                )
            else:
                logger.warning(f"Memories directory does not exist: {memories_dir}")
        # 2.2 Mount asset bundles
        if has_bundles:
            for bundle_config in context.asset_bundles:
                bundle_name = bundle_config.bundle_name
                bundle_type = bundle_config.bundle_type
                if bundle_type == "external":
                    # External 类型:直接使用 bundle directory作为 asset_dir (virtual mode, read-only)
                    mount_path = f"{bundle_config.mount_path}/"
                    realpath = f"{context.business_unit_path}/{ASSET_BUNDLES_DIR}/{bundle_name}/{TABLES_DIR}"
                    routes[mount_path] = FilesystemBackend(
                        root_dir=realpath,
                        virtual_mode=True
                    )
                    logger.debug(f"Mounting external bundle: {mount_path} -> {realpath}")
                
                elif bundle_type == "local":
                    # Local type: iterate volumes, mount each volume's storage_location
                    for volume in bundle_config.volumes:
                        volume_name = volume.get("name", "")
                        volume_type = volume.get("volume_type", "local")
                        storage_location = volume.get("storage_location", "")
                        
                        if volume_type == "local" and storage_location:
                            # Expand ~ in path
                            storage_path = os.path.expanduser(storage_location)
                            
                            if os.path.exists(storage_path):
                                mount_path = f"{bundle_config.mount_path}_{volume_name}/"
                                routes[mount_path] = FilesystemBackend(
                                    root_dir=storage_path,
                                    virtual_mode=True
                                )
                                logger.debug(f"Mounting local volume: {mount_path} -> {storage_path}")
                            else:
                                logger.warning(f"Volume path does not exist: {storage_path}")
                        
                        elif volume_type != "local":
                            # Other types (e.g., s3) not yet supported
                            logger.debug(f"Skipping non-local volume type: {volume_name} (type={volume_type})")
        
        # 3. Create CompositeBackend
        venv_path = f"{context.agent_path}/venv"
        env = {
            "PATH": f"{venv_path}/bin:{os.environ.get('PATH', '')}",
            "VIRTUAL_ENV": venv_path,
        }
        if routes:
            composite_backend = CompositeBackend(
                default=LocalShellBackend(root_dir=context.agent_path,virtual_mode=False,inherit_env=True,env=env),
                routes=routes
            )
            logger.info(f"python location:{composite_backend.execute("which python").output}")
            logger.info(f"CompositeBackend created successfully: routes={len(routes)}  mount points")

            return composite_backend
        else:
            raise ValueError(f"No valid mount points")
    def _load_asset_bundles(self, bu_path: Path, business_unit_id: str) -> List[AssetBundleBackendConfig]:
        """Load all Asset Bundle backend configs under Business Unit
        
        Iterate asset_bundles directory, read each bundle config and build backend config list
        
        Args:
            bu_path: Business Unit directory path
            business_unit_id: Business Unit ID
            
        Returns:
            List of AssetBundleBackendConfig
        """
        asset_bundles = []
        bundles_dir = bu_path / ASSET_BUNDLES_DIR
        
        if not bundles_dir.exists():
            logger.debug(f"asset_bundles directory does not exist: {bundles_dir}")
            return asset_bundles
        
        logger.info(f"Scanning asset_bundles: {bundles_dir}")
        
        for bundle_dir in bundles_dir.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
                continue
            
            bundle_config = self._load_single_bundle_config(bundle_dir, business_unit_id)
            if bundle_config:
                asset_bundles.append(bundle_config)
        
        logger.info(f"Loaded {len(asset_bundles)}  asset bundle configs")
        return asset_bundles
    
    def _load_single_bundle_config(self, bundle_path: Path, business_unit_id: str) -> Optional[AssetBundleBackendConfig]:
        """Load 单 Asset(s) Bundle 的后端配置
        
        Steps:
        1. Read bundle.yaml to get bundle_type
        2. 如果是 external 类型, asset_dir 就是当前 bundle directory
        3. 如果是 local 类型, 读取 volumes directory下的 volume 配置
        
        Args:
            bundle_path: Bundle directory path
            business_unit_id: Business Unit ID
            
        Returns:
            AssetBundleBackendConfig or None
        """
        bundle_name = bundle_path.name
        bundle_yaml = bundle_path / ASSET_BUNDLE_CONFIG_FILE
        
        if not bundle_yaml.exists():
            logger.debug(f"bundle.yaml does not exist: {bundle_yaml}")
            return None
        
        try:
            with open(bundle_yaml, 'r', encoding='utf-8') as f:
                bundle_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to read  bundle.yaml failed: {bundle_yaml}, error={e}")
            return None
        
        bundle_type = bundle_config.get("bundle_type", "local")
        logger.debug(f"Loading bundle: {bundle_name}, type={bundle_type}")
        
        volumes = []
        
        if bundle_type == "local":
            # Local type: read all volume configs under volumes directory
            volumes_dir = bundle_path / VOLUMES_DIR
            if volumes_dir.exists():
                volumes = self._load_volumes_config(volumes_dir)
            return AssetBundleBackendConfig(
                bundle_name=bundle_name,
                bundle_type=bundle_type,
                bundle_path=str(bundle_path),
                mount_path=f"/{bundle_name}",
                volumes=volumes
            )
        else:
            # External type: directly load tables
            return AssetBundleBackendConfig(
                bundle_name=bundle_name,
                bundle_type=bundle_type,
                bundle_path=str(bundle_path),
                mount_path=f"/{bundle_name}",
                volumes=volumes
            )
    
    def _load_volumes_config(self, volumes_dir: Path) -> List[Dict[str, Any]]:
        """Load  volumes directory下的所有 volume 配置
        
        Args:
            volumes_dir: volumes directory path
            
        Returns:
            List of volume configs
        """
        volumes = []
        
        for volume_file in volumes_dir.glob("*.yaml"):
            if volume_file.name.startswith("."):
                continue
            
            try:
                with open(volume_file, 'r', encoding='utf-8') as f:
                    volume_config = yaml.safe_load(f) or {}
                
                volume_name = volume_file.stem
                volume_type = volume_config.get("volume_type", "local")
                
                volume_info = {
                    "name": volume_name,
                    "volume_type": volume_type,
                    "file_path": str(volume_file)
                }
                
                # Add different config based on volume_type
                if volume_type == "local":
                    volume_info["storage_location"] = volume_config.get("storage_location", "")
                elif volume_type == "s3":
                    volume_info.update({
                        "s3_endpoint": volume_config.get("s3_endpoint"),
                        "s3_bucket": volume_config.get("s3_bucket"),
                        "s3_access_key": volume_config.get("s3_access_key"),
                        "s3_secret_key": volume_config.get("s3_secret_key"),
                    })
                
                volumes.append(volume_info)
                logger.debug(f"Loading volume: {volume_name}, type={volume_type}")
                
            except Exception as e:
                logger.error(f"Failed to read  volume 配置failed: {volume_file}, error={e}")
        
        return volumes


# Global engine instance
_engine_instance: Optional[DeepAgentsEngine] = None


def get_deepagents_engine() -> DeepAgentsEngine:
    """Get global DeepAgents engine instance"""
    global _engine_instance
    if _engine_instance is None:
        logger.debug("Creating global DeepAgentsEngine instance")
        _engine_instance = DeepAgentsEngine()
    return _engine_instance




# Export dependency checking functions
__all__ = [
    "DeepAgentsEngine",
    "AgentBuildContext",
    "AssetBundleBackendConfig",
    "SkillConfig",
    "get_deepagents_engine",
    "check_dependencies",
    "get_python_info",
    "log_dependency_status",
]
