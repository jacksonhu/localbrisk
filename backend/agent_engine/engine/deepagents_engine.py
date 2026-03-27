"""
基于 DeepAgents SDK 的 Agent 引擎实现

使用 LangChain DeepAgents SDK 构建智能代理，支持：
- 从 agent_spec.yaml 加载配置
- 加载 skills、memories、models 目录配置
- 支持多个 system prompt 拼接
- FilesystemBackend 文件系统后端

依赖:
- pyyaml (必需)
- langchain-core (构建 Agent 时需要)
- langchain-openai (使用 OpenAI 兼容 API 时需要)
- deepagents (构建 Agent 时需要)
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

# 仅用于类型检查的导入
if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# ============================================================
# 依赖导入
# ============================================================
# 记录导入状态和错误信息，便于诊断问题
_LANGCHAIN_AVAILABLE = False
_DEEPAGENTS_AVAILABLE = False
_LANGCHAIN_IMPORT_ERROR: Optional[str] = None
_DEEPAGENTS_IMPORT_ERROR: Optional[str] = None

# 导入 langchain-core
try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    _LANGCHAIN_AVAILABLE = True
except ImportError as e:
    BaseChatModel = None
    BaseTool = None
    _LANGCHAIN_IMPORT_ERROR = str(e)

# 导入 deepagents 和 langgraph
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
    """获取当前 Python 环境信息，用于诊断问题"""
    return {
        "executable": sys.executable,
        "version": sys.version,
        "prefix": sys.prefix,
        "path": sys.path[:5],  # 只取前5个路径
    }


def check_dependencies(raise_error: bool = True) -> bool:
    """检查依赖是否可用
    
    Args:
        raise_error: 如果依赖不可用是否抛出异常
        
    Returns:
        bool: 依赖是否全部可用
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
            f"缺少必要依赖: {', '.join(missing)}。\n"
            f"导入错误: {'; '.join(errors)}\n"
            f"当前 Python: {python_info['executable']}\n"
            f"请确保使用正确的虚拟环境运行，或执行: pip install {' '.join(missing)}"
        )
        raise ImportError(error_msg)
    
    return len(missing) == 0


def log_dependency_status():
    """记录依赖状态到日志（启动时调用）"""
    python_info = get_python_info()
    logger.info(f"Python 环境: {python_info['executable']}")
    logger.info(f"Python 版本: {python_info['version'].split()[0]}")
    logger.info(f"langchain-core 可用: {_LANGCHAIN_AVAILABLE}")
    logger.info(f"deepagents 可用: {_DEEPAGENTS_AVAILABLE}")
    
    if _LANGCHAIN_IMPORT_ERROR:
        logger.warning(f"langchain-core 导入错误: {_LANGCHAIN_IMPORT_ERROR}")
    if _DEEPAGENTS_IMPORT_ERROR:
        logger.warning(f"deepagents 导入错误: {_DEEPAGENTS_IMPORT_ERROR}")


# 模块加载时记录依赖状态
log_dependency_status()


@dataclass
class SkillConfig:
    """技能配置
    
    用于描述单个技能的配置信息
    """
    name: str                                # 技能名称
    absolute_path: str                       # 技能目录的绝对路径
    mount_path: str                          # 挂载路径（POSIX 格式，用于 backend 路由）


@dataclass
class AssetBundleBackendConfig:
    """Asset Bundle 后端配置
    
    用于描述单个 asset bundle 的后端配置信息
    """
    bundle_name: str                         # Bundle 名称
    bundle_type: str                         # Bundle 类型: local 或 external
    bundle_path: str                         # Bundle 目录路径
    mount_path: str                          # 挂载路径（用于路由）
    volumes: List[Dict[str, Any]]            # Volume 配置列表


@dataclass
class AgentBuildContext:
    """Agent 构建上下文
    
    包含构建 Agent 所需的所有配置信息
    """
    business_unit_path: str                  # Business Unit 目录路径
    agent_path: str                          # Agent 目录路径
    agent_name: str                          # Agent 名称
    business_unit_id: str                    # Business Unit ID
    agent_spec: Dict[str, Any]               # agent_spec.yaml 内容
    model_config: Optional[Dict[str, Any]]   # 激活的模型配置
    memories: List[Dict[str, Any]]           # 所有启用的 memory 配置
    skills: List[SkillConfig]                # 技能配置列表
    output_path: str                       # 工作目录路径
    asset_bundles: List[AssetBundleBackendConfig] = None  # Asset Bundle 后端配置列表
    
    def __post_init__(self):
        if self.asset_bundles is None:
            self.asset_bundles = []


class DeepAgentsEngine:
    """基于 DeepAgents SDK 的 Agent 引擎
    
    负责从 Agent 配置目录加载配置并创建 DeepAgent 实例
    """
    
    def __init__(self):
        logger.info("初始化 DeepAgentsEngine")
        self._llm_factory = None
        self._model_resolver: Optional[callable] = None
        self._checkpointer_contexts: Dict[int, Any] = {}
    
    def _ensure_llm_factory(self):
        """确保 LLM 工厂已初始化"""
        if self._llm_factory is None:
            if not _LANGCHAIN_AVAILABLE:
                raise ImportError("需要安装 langchain-core: pip install langchain-core")
            from ..llm.client_factory import get_llm_client_factory
            self._llm_factory = get_llm_client_factory()
        return self._llm_factory
    
    def set_model_resolver(self, resolver: callable):
        """设置模型解析器
        
        Args:
            resolver: 异步函数，接收 (business_unit_id, agent_name, model_name) 返回模型配置
        """
        self._model_resolver = resolver
        if self._llm_factory:
            self._llm_factory.set_model_resolver(resolver)
        logger.debug("模型解析器已设置")
    
    async def build_agent(
        self,
        agent_path: str,
        business_unit_id: str,
        tools: Optional[List] = None,
        debug: bool = False,
    ):
        """构建 DeepAgent 实例
        
        Args:
            agent_path: Agent 目录路径 (如 ~/.localbrisk/App_Data/Catalogs/myunit/agents/Data_analyst)
            business_unit_id: Business Unit ID
            tools: 额外的自定义工具 (List[BaseTool])
            debug: 是否启用调试模式
            
        Returns:
            CompiledStateGraph: 编译后的 DeepAgent 实例
            
        Raises:
            ImportError: 如果缺少必要依赖
        """
        # 检查依赖
        check_dependencies(raise_error=True)
        
        logger.info(f"开始构建 Agent: path={agent_path}, business_unit={business_unit_id}")
        
        # 1. 加载 Agent 配置上下文
        context = await self._load_agent_context(agent_path, business_unit_id)
        
        # 2. 创建 LLM 客户端
        llm_client = await self._create_llm_client(context)
        
        # 3. 构建系统提示（拼接所有启用的 prompt）
        system_prompt = self._load_base_system_prompt()
        system_prompt=system_prompt.replace("{{cwd}}", context.agent_path)
        
        # 4. 创建 CompositeBackend 文件系统后端（包含 skills 和 asset bundles 挂载）
        backend = self._create_backend(context)
        # 5. 收集技能的挂载路径（POSIX 格式，相对于 backend）
        # skills 参数需要的是相对于 backend 的路径，如 ["/skills/python_expert/", "/skills/data_analyst/"]
        skills_mount_paths = None
        if context.skills:
            skills_mount_paths = [skill.mount_path for skill in context.skills]
            logger.debug(f"skills:: {skills_mount_paths}")
        
        # 6. 合并工具（内置工具 + 外部自定义工具）
        from agent_engine.tools import get_builtin_tools
        task_root = str(Path(context.output_path) / ".task")
        Path(task_root).mkdir(parents=True, exist_ok=True)
        builtin_tools = get_builtin_tools(backend=backend, task_root=task_root)
        all_tools = builtin_tools + (tools if tools else [])

        # 7. 初始化 Checkpointer（统一异步）

        checkpoint_root = str(Path(context.output_path) / ".checkpoints")
        Path(checkpoint_root).mkdir(parents=True, exist_ok=True)
        checkpoint_db = str(Path(checkpoint_root) / "checkpoints.sqlite")
        checkpointer_cm = AsyncSqliteSaver.from_conn_string(checkpoint_db)
        checkpointer = await self._enter_checkpointer_context(checkpointer_cm)
        checkpointer = InMemorySaver()
        try:
            # 8. 创建内置子 Agent（复用父级沙箱 backend / tools / model）
            subagents = create_builtin_subagents(
                parent_model=llm_client,
                parent_tools=all_tools,
                parent_backend=backend,
            )

            # 9. 创建 DeepAgent（Markdown 直出）
            logger.info(
                f"创建 DeepAgent: model={type(llm_client).__name__}, skills={len(context.skills) if context.skills else 0}, "
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
                logger.warning("当前 deepagents 版本不支持 subagents 参数，回退为无子 Agent 模式: %s", e)
                create_kwargs.pop("subagents", None)
                agent = create_deep_agent(**create_kwargs)
        except Exception:
            await self._exit_checkpointer_context(checkpointer_cm)
            raise

        self._checkpointer_contexts[id(agent)] = checkpointer_cm
        logger.info(f"Agent 构建成功: {context.agent_name}")
        return agent

    async def _enter_checkpointer_context(self, cm: Any) -> Any:
        """兼容同步/异步 checkpointer context manager。"""
        aenter = getattr(cm, "__aenter__", None)
        if callable(aenter):
            return await aenter()
        enter = getattr(cm, "__enter__", None)
        if callable(enter):
            return enter()
        return cm

    async def _exit_checkpointer_context(self, cm: Any) -> None:
        """兼容同步/异步 checkpointer context manager。"""
        aexit = getattr(cm, "__aexit__", None)
        if callable(aexit):
            await aexit(None, None, None)
            return
        exit_ = getattr(cm, "__exit__", None)
        if callable(exit_):
            exit_(None, None, None)

    async def close_agent_resources(self, agent: Any) -> None:
        """关闭 Agent 构建阶段创建的资源（如 checkpointer context）"""
        cm = self._checkpointer_contexts.pop(id(agent), None)
        if cm is None:
            return
        try:
            await self._exit_checkpointer_context(cm)
        except Exception as e:
            logger.warning(f"关闭 checkpointer 失败: {e}")
    
    async def _load_agent_context(
        self,
        agent_path: str,
        business_unit_id: str
    ) -> AgentBuildContext:
        """加载 Agent 配置上下文
        
        从 Agent 目录加载所有配置信息
        
        Args:
            agent_path: Agent 目录路径
            business_unit_id: Business Unit ID
            
        Returns:
            AgentBuildContext: 配置上下文
        """
        agent_path = os.path.expanduser(agent_path)
        path = Path(agent_path)
        
        if not path.exists():
            raise ValueError(f"Agent 目录不存在: {agent_path}")
        
        # 1. 加载 agent_spec.yaml
        spec_path = path / "agent_spec.yaml"
        if not spec_path.exists():
            raise ValueError(f"agent_spec.yaml 不存在: {spec_path}")
        
        with open(spec_path, 'r', encoding='utf-8') as f:
            agent_spec = yaml.safe_load(f)
        
        agent_name = agent_spec.get("baseinfo", {}).get("name", path.name)
        logger.info(f"加载 Agent 配置: name={agent_name}")
        
        # 2. 加载激活的模型配置
        model_config = await self._load_active_model(path, agent_spec, business_unit_id, agent_name)
        
        # 3. 加载所有启用的 memories
        memories = self._load_memories(path)
        
        # 4. 加载所有技能路径
        skills = self._load_skills(path)
        
        # 5. 确定 output 路径
        output_path = str(path / "output")
        os.makedirs(output_path, exist_ok=True)
        
        # 6. 加载 asset bundles 后端配置
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
        """加载激活的模型配置
        
        Args:
            agent_path: Agent 目录路径
            agent_spec: agent_spec.yaml 内容
            business_unit_id: Business Unit ID
            agent_name: Agent 名称
            
        Returns:
            模型配置字典
        """
        # 获取激活的模型名称
        active_model = agent_spec.get("active_model")
        if not active_model:
            # 尝试从 llm_config 获取
            llm_config = agent_spec.get("llm_config", {})
            active_model = llm_config.get("llm_model")
        
        if not active_model:
            logger.warning(f"Agent {agent_name} 未配置激活的模型")
            return None
        
        logger.info(f"加载激活的模型: {active_model}")
        
        # 先尝试从本地 models 目录加载
        models_dir = agent_path / "models"
        if models_dir.exists():
            model_file = models_dir / f"{active_model}.yaml"
            if model_file.exists():
                logger.debug(f"从本地加载模型配置: {model_file}")
                with open(model_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        
        # 如果本地没有，使用 model_resolver
        if self._model_resolver:
            try:
                return await self._model_resolver(business_unit_id, agent_name, active_model)
            except Exception as e:
                logger.error(f"解析模型配置失败: {e}")
        
        return None
    
    def _load_memories(self, agent_path: Path) -> List[Dict[str, Any]]:
        """加载所有启用的 memories

        从 memories 目录加载所有 .md 文件及其元数据

        Args:
            agent_path: Agent 目录路径

        Returns:
            启用的 memory 配置列表
        """
        memories = []
        memories_dir = agent_path / AGENT_MEMORIES_DIR

        if not memories_dir.exists():
            logger.debug(f"memories 目录不存在: {memories_dir}")
            return memories

        # 遍历所有 .md 文件（排除 . 开头的文件）
        for md_file in sorted(memories_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue

            memory_name = md_file.stem
            logger.debug(f"加载 memory: {memory_name}")

            # 尝试读取元数据文件
            meta_file = memories_dir / f".{memory_name}.meta.yaml"
            meta = {}
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f) or {}

            # 检查是否启用（默认启用）
            if not meta.get("enabled", True):
                logger.debug(f"memory {memory_name} 已禁用，跳过")
                continue

            memories.append(f"/memories/{memory_name}.md")
        logger.info(f"加载了 {len(memories)} 个 memories")
        return memories
    
    def _load_skills(self, agent_path: Path) -> List[SkillConfig]:
        """加载所有技能配置
        
        扫描 skills 目录，返回包含 SKILL.md 的技能配置列表
        
        Args:
            agent_path: Agent 目录路径
            
        Returns:
            技能配置列表 (SkillConfig)
        """
        skills = []
        skills_dir = agent_path / "skills"
        
        if not skills_dir.exists():
            logger.debug(f"skills 目录不存在: {skills_dir}")
            return skills
        
        # 遍历 skills 目录下的子目录
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            # 检查是否包含 SKILL.md
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                skill_name = skill_dir.name
                # 挂载路径使用 POSIX 格式: /skills/{skill_name}/
                mount_path = f"/{AGENT_SKILLS_DIR}/{skill_name}/"
                
                skill_config = SkillConfig(
                    name=skill_name,
                    absolute_path=str(skill_dir),
                    mount_path=mount_path
                )
                skills.append(skill_config)
                logger.debug(f"发现技能: {skill_name} -> {mount_path}")
            else:
                logger.debug(f"目录 {skill_dir.name} 缺少 SKILL.md，跳过")
        
        logger.info(f"加载了 {len(skills)} 个技能")
        return skills
    
    async def _create_llm_client(self, context: AgentBuildContext):
        """创建 LLM 客户端
        
        Args:
            context: Agent 构建上下文
            
        Returns:
            LangChain BaseChatModel 实例
        """
        if not context.model_config:
            logger.warning(f"Agent {context.agent_name} 没有配置模型，将使用默认模型")
            return None
        
        # 延迟导入
        from ..core.config import AgentRuntimeConfig, LLMRuntimeConfig
        
        # 从 agent_spec 提取 LLM 运行时配置
        llm_runtime_config = LLMRuntimeConfig.from_agent_llm_config(
            context.agent_spec.get("llm_config", {})
        )
        
        # 从 model_config 读取 temperature（如果有）
        model_temperature = context.model_config.get("temperature") or context.model_config.get("tempreture")
        if model_temperature is not None:
            llm_runtime_config.temperature = float(model_temperature)
        
        # 创建 AgentRuntimeConfig
        runtime_config = AgentRuntimeConfig(
            agent_name=context.agent_name,
            business_unit_id=context.business_unit_id,
            agent_path=context.agent_path,
            llm_config=llm_runtime_config
        )
        
        # 确保 LLM 工厂已初始化
        llm_factory = self._ensure_llm_factory()
        if self._model_resolver:
            llm_factory.set_model_resolver(self._model_resolver)
        
        # 使用工厂创建客户端
        return await llm_factory.create_client(runtime_config, context.model_config)
    
    
    def _load_base_system_prompt(self) -> str:
        """加载基础系统提示模板
        
        从 AGENTS.md 文件读取基础系统提示模板，该模板包含 {user_custom_prompt} 占位符
        
        Returns:
            基础系统提示模板字符串
        """
        # AGENTS.md 位于当前文件所在目录
        engine_dir = Path(__file__).parent
        agents_md_path = engine_dir / "AGENTS.md"
        try:
            content = agents_md_path.read_text(encoding="utf-8")
            logger.debug(f"加载基础系统提示模板: {agents_md_path}, 长度 {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"读取 AGENTS.md 失败: {e}")
            raise Exception(f"读取 AGENTS.md 失败: {e}")

    def _create_backend(self, context: AgentBuildContext):
        """创建 CompositeBackend 文件系统后端
        
        创建一个组合后端，包含：
        1. LocalShellBackend - 默认后端，允许在 output 下读写文件和执行命令
        2. FilesystemBackend - 挂载 skills 目录（只读）
        3. 多个 FilesystemBackend(virtual_mode=True) - 挂载各个 asset bundle 的文档目录（只读）
        
        Args:
            context: Agent 构建上下文
            
        Returns:
            CompositeBackend 或 FilesystemBackend 实例
        """
        output = context.output_path
        has_memories = context.memories and len(context.memories) > 0
        # 如果没有 skills 和 asset bundles，或 CompositeBackend 不可用，回退到简单的 FilesystemBackend
        has_skills = context.skills and len(context.skills) > 0
        has_bundles = context.asset_bundles and len(context.asset_bundles) > 0

        if (not has_skills and not has_bundles and not has_memories) or CompositeBackend is None or LocalShellBackend is None:
            logger.info(f"创建 FilesystemBackend: root_dir={output}")
            return FilesystemBackend(root_dir=output)
        
        logger.info(f"创建 CompositeBackend: output={output}, skills={len(context.skills) if has_skills else 0}, asset_bundles={len(context.asset_bundles) if has_bundles else 0}")

        
        # 2. 构建路由配置
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
                logger.warning(f"Memories 目录不存在: {memories_dir}")
        # 2.2 挂载 asset bundles
        if has_bundles:
            for bundle_config in context.asset_bundles:
                bundle_name = bundle_config.bundle_name
                bundle_type = bundle_config.bundle_type
                if bundle_type == "external":
                    # External 类型：直接使用 bundle 目录作为 asset_dir（虚拟模式，只读）
                    mount_path = f"{bundle_config.mount_path}/"
                    realpath = f"{context.business_unit_path}/{ASSET_BUNDLES_DIR}/{bundle_name}/{TABLES_DIR}"
                    routes[mount_path] = FilesystemBackend(
                        root_dir=realpath,
                        virtual_mode=True
                    )
                    logger.debug(f"挂载 external bundle: {mount_path} -> {realpath}")
                
                elif bundle_type == "local":
                    # Local 类型：遍历 volumes，挂载每个 volume 的 storage_location
                    for volume in bundle_config.volumes:
                        volume_name = volume.get("name", "")
                        volume_type = volume.get("volume_type", "local")
                        storage_location = volume.get("storage_location", "")
                        
                        if volume_type == "local" and storage_location:
                            # 展开路径中的 ~ 符号
                            storage_path = os.path.expanduser(storage_location)
                            
                            if os.path.exists(storage_path):
                                mount_path = f"{bundle_config.mount_path}_{volume_name}/"
                                routes[mount_path] = FilesystemBackend(
                                    root_dir=storage_path,
                                    virtual_mode=True
                                )
                                logger.debug(f"挂载 local volume: {mount_path} -> {storage_path}")
                            else:
                                logger.warning(f"Volume 路径不存在: {storage_path}")
                        
                        elif volume_type != "local":
                            # 其他类型（如 s3）暂时不支持
                            logger.debug(f"跳过非 local 类型的 volume: {volume_name} (type={volume_type})")
        
        # 3. 创建 CompositeBackend
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
            logger.info(f"CompositeBackend 创建成功: routes={len(routes)} 个挂载点")

            return composite_backend
        else:
            raise ValueError(f"没有有效的挂载点")
    def _load_asset_bundles(self, bu_path: Path, business_unit_id: str) -> List[AssetBundleBackendConfig]:
        """加载 Business Unit 下所有 Asset Bundle 的后端配置
        
        遍历 asset_bundles 目录，读取每个 bundle 的配置并构建后端配置列表
        
        Args:
            bu_path: Business Unit 目录路径
            business_unit_id: Business Unit ID
            
        Returns:
            AssetBundleBackendConfig 列表
        """
        asset_bundles = []
        bundles_dir = bu_path / ASSET_BUNDLES_DIR
        
        if not bundles_dir.exists():
            logger.debug(f"asset_bundles 目录不存在: {bundles_dir}")
            return asset_bundles
        
        logger.info(f"扫描 asset_bundles: {bundles_dir}")
        
        for bundle_dir in bundles_dir.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
                continue
            
            bundle_config = self._load_single_bundle_config(bundle_dir, business_unit_id)
            if bundle_config:
                asset_bundles.append(bundle_config)
        
        logger.info(f"加载了 {len(asset_bundles)} 个 asset bundle 配置")
        return asset_bundles
    
    def _load_single_bundle_config(self, bundle_path: Path, business_unit_id: str) -> Optional[AssetBundleBackendConfig]:
        """加载单个 Asset Bundle 的后端配置
        
        步骤：
        1. 读取 bundle.yaml 获取 bundle_type
        2. 如果是 external 类型，asset_dir 就是当前 bundle 目录
        3. 如果是 local 类型，读取 volumes 目录下的 volume 配置
        
        Args:
            bundle_path: Bundle 目录路径
            business_unit_id: Business Unit ID
            
        Returns:
            AssetBundleBackendConfig 或 None
        """
        bundle_name = bundle_path.name
        bundle_yaml = bundle_path / ASSET_BUNDLE_CONFIG_FILE
        
        if not bundle_yaml.exists():
            logger.debug(f"bundle.yaml 不存在: {bundle_yaml}")
            return None
        
        try:
            with open(bundle_yaml, 'r', encoding='utf-8') as f:
                bundle_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"读取 bundle.yaml 失败: {bundle_yaml}, error={e}")
            return None
        
        bundle_type = bundle_config.get("bundle_type", "local")
        logger.debug(f"加载 bundle: {bundle_name}, type={bundle_type}")
        
        volumes = []
        
        if bundle_type == "local":
            # Local 类型：读取 volumes 目录下的所有 volume 配置
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
            # External 类型：直接加载tables
            return AssetBundleBackendConfig(
                bundle_name=bundle_name,
                bundle_type=bundle_type,
                bundle_path=str(bundle_path),
                mount_path=f"/{bundle_name}",
                volumes=volumes
            )
    
    def _load_volumes_config(self, volumes_dir: Path) -> List[Dict[str, Any]]:
        """加载 volumes 目录下的所有 volume 配置
        
        Args:
            volumes_dir: volumes 目录路径
            
        Returns:
            Volume 配置列表
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
                
                # 根据 volume_type 添加不同的配置
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
                logger.debug(f"加载 volume: {volume_name}, type={volume_type}")
                
            except Exception as e:
                logger.error(f"读取 volume 配置失败: {volume_file}, error={e}")
        
        return volumes


# 全局引擎实例
_engine_instance: Optional[DeepAgentsEngine] = None


def get_deepagents_engine() -> DeepAgentsEngine:
    """获取全局 DeepAgents 引擎实例"""
    global _engine_instance
    if _engine_instance is None:
        logger.debug("创建全局 DeepAgentsEngine 实例")
        _engine_instance = DeepAgentsEngine()
    return _engine_instance




# 导出依赖检查函数
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
