"""
Agent 服务 - 管理 Agent、Prompt、Skill
"""

import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.constants import AGENT_CONFIG_FILE
from app.models.catalog import (
    Agent, AgentCreate, AgentUpdate, EntityType,
    AgentLLMConfig, AgentInstruction, AgentRouting,
    AgentCapabilities, AgentGovernance,
    AgentNativeSkill, AgentPromptTemplate, AgentMCPTool, AgentHumanInTheLoop,
    Prompt, PromptCreate, PromptUpdate,
)
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.catalog_service_new import CatalogService

logger = logging.getLogger(__name__)


class AgentService(BaseService):
    """Agent 服务类"""
    
    def __init__(self, catalog_service: "CatalogService"):
        super().__init__()
        self.catalog_service = catalog_service
    
    # ==================== 路径方法 ====================
    
    def _get_agent_path(self, catalog_id: str, agent_name: str) -> Path:
        """获取 Agent 路径"""
        catalog_path = self.catalog_service.get_catalog_path(catalog_id)
        return self.catalog_service.get_agents_dir(catalog_path) / agent_name
    
    def _get_config_path(self, agent_path: Path) -> Path:
        """获取 Agent 配置文件路径"""
        return agent_path / AGENT_CONFIG_FILE
    
    # ==================== Agent CRUD ====================
    
    def scan_agents(self, catalog_path: Path, catalog_id: str) -> List[Agent]:
        """扫描 Agent"""
        agents_dir = self.catalog_service.get_agents_dir(catalog_path)
        return self._scan_subdirs(agents_dir, lambda p: self._load_agent(catalog_id, p))
    
    def _load_agent(self, catalog_id: str, agent_path: Path) -> Optional[Agent]:
        """加载 Agent"""
        config = self._load_yaml(self._get_config_path(agent_path)) or {}
        baseinfo = self._extract_baseinfo(config, agent_path.name)
        
        # 兼容 metadata 节
        if config.get("metadata"):
            meta = config["metadata"]
            if not baseinfo.get("display_name") or baseinfo["display_name"] == agent_path.name:
                baseinfo["display_name"] = meta.get("name") or meta.get("display_name") or agent_path.name
            if not baseinfo.get("description"):
                baseinfo["description"] = meta.get("description")
        
        # 扫描子目录
        skills = [f.name for f in (agent_path / "skills").iterdir() if f.is_dir() and not f.name.startswith(".")] if (agent_path / "skills").exists() else []
        prompts = [f.name for f in (agent_path / "prompts").iterdir() if f.is_file() and f.suffix.lower() in [".md", ".markdown"] and not f.name.startswith(".")] if (agent_path / "prompts").exists() else []
        
        return Agent(
            id=f"{catalog_id}_agent_{agent_path.name}",
            name=agent_path.name,
            display_name=baseinfo.get("display_name") or agent_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            catalog_id=catalog_id,
            entity_type=EntityType.AGENT,
            path=str(agent_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            llm_config=self._parse_llm_config(config.get("llm_config")),
            instruction=self._parse_instruction(config.get("instruction")),
            routing=self._parse_routing(config.get("routing")),
            capabilities=self._parse_capabilities(config.get("capabilities")),
            governance=self._parse_governance(config.get("governance")),
            skills=skills,
            prompts=prompts,
        )
    
    def _parse_llm_config(self, data: Dict) -> Optional[AgentLLMConfig]:
        if not data:
            return None
        return AgentLLMConfig(
            llm_model=data.get("llm_model"),
            temperature=data.get("temperature", 0.2),
            max_tokens=data.get("max_tokens", 2000),
            response_format=data.get("response_format", "text"),
        )
    
    def _parse_instruction(self, data: Dict) -> Optional[AgentInstruction]:
        if not data:
            return None
        templates = [AgentPromptTemplate(name=p.get("name") if isinstance(p, dict) else p) for p in data.get("user_prompt_templates", [])]
        return AgentInstruction(
            system_prompt=data.get("system_prompt"),
            user_prompt_template=data.get("user_prompt_template"),
            user_prompt_templates=templates,
        )
    
    def _parse_routing(self, data: Dict) -> Optional[AgentRouting]:
        if not data:
            return None
        return AgentRouting(
            trigger_keywords=data.get("trigger_keywords", []),
            required_context_keys=data.get("required_context_keys", []),
            next_possible_agents=data.get("next_possible_agents", []),
        )
    
    def _parse_capabilities(self, data: Dict) -> Optional[AgentCapabilities]:
        if not data:
            return None
        skills = [AgentNativeSkill(name=s.get("name") if isinstance(s, dict) else s) for s in data.get("native_skills", [])]
        tools = [AgentMCPTool(server_id=t.get("server_id", ""), tools=t.get("tools", [])) for t in data.get("mcp_tools", [])]
        return AgentCapabilities(native_skills=skills, mcp_tools=tools)
    
    def _parse_governance(self, data: Dict) -> Optional[AgentGovernance]:
        if not data:
            return None
        hitl = AgentHumanInTheLoop(trigger=data["human_in_the_loop"].get("trigger")) if data.get("human_in_the_loop") else None
        return AgentGovernance(human_in_the_loop=hitl, termination_criteria=data.get("termination_criteria"))
    
    def list_agents(self, catalog_id: str) -> List[Agent]:
        """获取 Agent 列表"""
        catalog_path = self.catalog_service.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return []
        return self.scan_agents(catalog_path, catalog_id)
    
    def get_agent(self, catalog_id: str, agent_name: str) -> Optional[Agent]:
        """获取 Agent"""
        agent_path = self._get_agent_path(catalog_id, agent_name)
        if not agent_path.exists():
            return None
        return self._load_agent(catalog_id, agent_path)
    
    def get_agent_config_content(self, catalog_id: str, agent_name: str) -> Optional[str]:
        """获取 Agent 配置内容"""
        agent_path = self._get_agent_path(catalog_id, agent_name)
        return self._read_file(self._get_config_path(agent_path))
    
    def create_agent(self, catalog_id: str, data: AgentCreate) -> Agent:
        """创建 Agent"""
        catalog_path = self.catalog_service.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        agents_dir = self.catalog_service.get_agents_dir(catalog_path)
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_path = agents_dir / data.name
        if agent_path.exists():
            raise ValueError(f"Agent '{data.name}' 已存在")
        
        # 创建目录结构
        agent_path.mkdir(parents=True, exist_ok=True)
        (agent_path / "skills").mkdir(exist_ok=True)
        (agent_path / "prompts").mkdir(exist_ok=True)
        
        # 创建配置
        config = {
            "baseinfo": self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin"),
            "llm_config": {"llm_model": "", "temperature": 0.2, "max_tokens": 2000, "response_format": "text"},
            "instruction": {"system_prompt": "", "user_prompt_template": "", "user_prompt_templates": []},
            "routing": {"trigger_keywords": [], "required_context_keys": [], "next_possible_agents": []},
            "capabilities": {"native_skills": [], "mcp_tools": []},
            "governance": {"human_in_the_loop": {"trigger": "on_error"}, "termination_criteria": ""},
        }
        
        self._save_yaml(self._get_config_path(agent_path), config)
        return self._load_agent(catalog_id, agent_path)
    
    def update_agent(self, catalog_id: str, agent_name: str, update: AgentUpdate) -> Optional[Agent]:
        """更新 Agent"""
        agent_path = self._get_agent_path(catalog_id, agent_name)
        if not agent_path.exists():
            return None
        
        config_path = self._get_config_path(agent_path)
        config = self._load_yaml(config_path) or {}
        
        # 更新 baseinfo
        baseinfo = self._extract_baseinfo(config, agent_path.name)
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        
        # 更新各配置块
        if update.llm_config:
            lc = config.setdefault("llm_config", {})
            for k in ["llm_model", "temperature", "max_tokens", "response_format"]:
                v = getattr(update.llm_config, k, None)
                if v is not None:
                    lc[k] = v
        
        if update.instruction:
            inst = config.setdefault("instruction", {})
            for k in ["system_prompt", "user_prompt_template"]:
                v = getattr(update.instruction, k, None)
                if v is not None:
                    inst[k] = v
            if update.instruction.user_prompt_templates is not None:
                inst["user_prompt_templates"] = [{"name": p.name} for p in update.instruction.user_prompt_templates]
        
        if update.routing:
            r = config.setdefault("routing", {})
            for k in ["trigger_keywords", "required_context_keys", "next_possible_agents"]:
                v = getattr(update.routing, k, None)
                if v is not None:
                    r[k] = v
        
        if update.capabilities:
            c = config.setdefault("capabilities", {})
            if update.capabilities.native_skills is not None:
                c["native_skills"] = [{"name": s.name} for s in update.capabilities.native_skills]
            if update.capabilities.mcp_tools is not None:
                c["mcp_tools"] = [{"server_id": t.server_id, "tools": t.tools} for t in update.capabilities.mcp_tools]
        
        if update.governance:
            g = config.setdefault("governance", {})
            if update.governance.human_in_the_loop is not None:
                g["human_in_the_loop"] = {"trigger": update.governance.human_in_the_loop.trigger}
            if update.governance.termination_criteria is not None:
                g["termination_criteria"] = update.governance.termination_criteria
        
        self._save_yaml(config_path, config)
        return self._load_agent(catalog_id, agent_path)
    
    def delete_agent(self, catalog_id: str, agent_name: str) -> bool:
        """删除 Agent"""
        return self._remove_dir(self._get_agent_path(catalog_id, agent_name))
    
    # ==================== Prompt 操作 ====================
    
    def _get_enabled_prompts(self, catalog_id: str, agent_name: str) -> List[str]:
        """获取启用的 prompts"""
        config = self._load_yaml(self._get_config_path(self._get_agent_path(catalog_id, agent_name))) or {}
        templates = config.get("instruction", {}).get("user_prompt_templates", [])
        return [p.get("name") if isinstance(p, dict) else p for p in templates]
    
    def _find_prompt_file(self, prompts_dir: Path, prompt_name: str) -> Optional[Path]:
        """查找 prompt 文件"""
        for name in [prompt_name, f"{prompt_name}.md"]:
            path = prompts_dir / name
            if path.exists():
                return path
        return None
    
    def list_prompts(self, catalog_id: str, agent_name: str) -> Optional[List[Prompt]]:
        """获取 Prompt 列表"""
        prompts_dir = self._get_agent_path(catalog_id, agent_name) / "prompts"
        if not prompts_dir.exists():
            return None
        
        enabled = self._get_enabled_prompts(catalog_id, agent_name)
        prompts = []
        
        for item in prompts_dir.iterdir():
            if not item.is_file() or item.suffix.lower() not in [".md", ".markdown"] or item.name.startswith("."):
                continue
            
            content = self._read_file(item) or ""
            meta = self._load_yaml(prompts_dir / f".{item.stem}.meta.yaml") or {}
            
            prompts.append(Prompt(
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
            ))
        
        return prompts
    
    def get_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> Optional[Prompt]:
        """获取 Prompt 详情"""
        prompts_dir = self._get_agent_path(catalog_id, agent_name) / "prompts"
        prompt_path = self._find_prompt_file(prompts_dir, prompt_name)
        if not prompt_path:
            return None
        
        content = self._read_file(prompt_path) or ""
        meta = self._load_yaml(prompts_dir / f".{prompt_path.stem}.meta.yaml") or {}
        enabled = self._get_enabled_prompts(catalog_id, agent_name)
        
        return Prompt(
            name=prompt_path.name,
            display_name=meta.get("display_name") or prompt_path.stem,
            description=meta.get("description"),
            tags=meta.get("tags", []),
            entity_type=EntityType.PROMPT,
            content=content,
            enabled=prompt_path.name in enabled,
            path=str(prompt_path),
            created_at=self._parse_datetime(meta.get("created_at")),
            updated_at=self._parse_datetime(meta.get("updated_at")),
        )
    
    def create_prompt(self, catalog_id: str, agent_name: str, data: PromptCreate) -> bool:
        """创建 Prompt"""
        prompts_dir = self._get_agent_path(catalog_id, agent_name) / "prompts"
        if not prompts_dir.exists():
            return False
        
        name = data.name if data.name.endswith(".md") else f"{data.name}.md"
        prompt_path = prompts_dir / name
        
        if prompt_path.exists():
            raise ValueError(f"Prompt '{data.name}' 已存在")
        
        self._write_file(prompt_path, data.content)
        self._save_yaml(prompts_dir / f".{prompt_path.stem}.meta.yaml", {"created_at": self._now_iso(), "updated_at": self._now_iso()})
        return True
    
    def update_prompt(self, catalog_id: str, agent_name: str, prompt_name: str, update: PromptUpdate) -> bool:
        """更新 Prompt"""
        prompts_dir = self._get_agent_path(catalog_id, agent_name) / "prompts"
        prompt_path = self._find_prompt_file(prompts_dir, prompt_name)
        if not prompt_path:
            return False
        
        if update.content is not None:
            self._write_file(prompt_path, update.content)
        
        meta_path = prompts_dir / f".{prompt_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}
        meta["updated_at"] = self._now_iso()
        self._save_yaml(meta_path, meta)
        return True
    
    def delete_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> bool:
        """删除 Prompt"""
        prompts_dir = self._get_agent_path(catalog_id, agent_name) / "prompts"
        prompt_path = self._find_prompt_file(prompts_dir, prompt_name)
        if not prompt_path:
            return False
        
        prompt_path.unlink()
        meta_path = prompts_dir / f".{prompt_path.stem}.meta.yaml"
        if meta_path.exists():
            meta_path.unlink()
        return True
    
    def toggle_prompt_enabled(self, catalog_id: str, agent_name: str, prompt_name: str, enabled: bool) -> bool:
        """切换 Prompt 启用状态"""
        agent_path = self._get_agent_path(catalog_id, agent_name)
        config_path = self._get_config_path(agent_path)
        prompts_dir = agent_path / "prompts"
        
        if not config_path.exists():
            return False
        
        actual_name = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            if (prompts_dir / name).exists():
                actual_name = name
                break
        if not actual_name:
            return False
        
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
    
    # ==================== Skill 操作 ====================
    
    def get_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取 Skill 内容和路径"""
        skill_path = self._get_agent_path(catalog_id, agent_name) / "skills" / skill_name
        if not skill_path.exists() or not skill_path.is_dir():
            return None
        
        content = self._read_file(skill_path / "SKILL.md") or ""
        return {"content": content, "path": str(skill_path)}
    
    def delete_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> bool:
        """删除 Skill"""
        skill_path = self._get_agent_path(catalog_id, agent_name) / "skills" / skill_name
        if not skill_path.exists():
            return False
        
        if skill_path.is_dir():
            shutil.rmtree(skill_path)
        else:
            skill_path.unlink()
        return True
    
    def toggle_skill_enabled(self, catalog_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        """切换 Skill 启用状态"""
        agent_path = self._get_agent_path(catalog_id, agent_name)
        config_path = self._get_config_path(agent_path)
        skills_dir = agent_path / "skills"
        
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
    
    def import_skill_from_zip(self, catalog_id: str, agent_name: str, zip_file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        """从 zip 文件导入 Skill"""
        zip_file_path = Path(zip_file_path)
        agent_path = self._get_agent_path(catalog_id, agent_name)
        skills_dir = agent_path / "skills"
        
        if not agent_path.exists():
            return {"success": False, "message": f"Agent '{agent_name}' 不存在"}
        
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if not zip_file_path.exists():
                return {"success": False, "message": f"zip 文件不存在: {zip_file_path}"}
            
            if not zipfile.is_zipfile(str(zip_file_path)):
                return {"success": False, "message": "无效的 zip 文件"}
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                with zipfile.ZipFile(str(zip_file_path), 'r') as zip_ref:
                    if not zip_ref.namelist():
                        return {"success": False, "message": "zip 文件为空"}
                    zip_ref.extractall(temp_path)
                
                # 查找内容目录
                top_level = [item for item in temp_path.iterdir() if not item.name.startswith('__MACOSX') and not item.name.startswith('._')]
                content_dir = top_level[0] if len(top_level) == 1 and top_level[0].is_dir() else temp_path
                
                # 查找 SKILL.md
                skill_md_path = content_dir / "SKILL.md"
                if not skill_md_path.exists():
                    candidates = [f for f in content_dir.iterdir() if f.name.upper() == "SKILL.MD"]
                    if candidates:
                        skill_md_path = candidates[0]
                    else:
                        return {"success": False, "message": "无效的 Skill 包：缺少 SKILL.md 文件"}
                
                # 解析 frontmatter
                frontmatter = self._parse_skill_frontmatter(skill_md_path)
                if not frontmatter.get('name'):
                    return {"success": False, "message": "无效的 SKILL.md：缺少 name 字段"}
                
                skill_name = frontmatter['name']
                skill_description = frontmatter.get('description', "从 zip 包导入的 Skill")
                
                skill_path = skills_dir / skill_name
                if skill_path.exists():
                    return {"success": False, "message": f"Skill '{skill_name}' 已存在", "skill_name": skill_name}
                
                skill_path.mkdir(parents=True, exist_ok=True)
                
                # 移动文件
                for item in content_dir.iterdir():
                    if not item.name.startswith('__MACOSX') and not item.name.startswith('._'):
                        shutil.move(str(item), str(skill_path / item.name))
                
                # 创建配置
                self._save_yaml(skill_path / f"{skill_name}.yaml", {
                    "baseinfo": self._create_baseinfo(skill_name, skill_name, skill_description),
                    "source": "local_import",
                    "import_file": original_filename or zip_file_path.name,
                })
                
                return {
                    "success": True,
                    "skill_name": skill_name,
                    "description": skill_description,
                    "message": f"Skill '{skill_name}' 导入成功",
                    "path": str(skill_path)
                }
                
        except zipfile.BadZipFile:
            return {"success": False, "message": "损坏的 zip 文件"}
        except Exception as e:
            logger.error(f"导入 Skill 失败: {e}", exc_info=True)
            return {"success": False, "message": f"导入失败: {str(e)}"}
    
    def _parse_skill_frontmatter(self, skill_md_path: Path) -> Dict[str, str]:
        """解析 SKILL.md 的 YAML frontmatter"""
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
            logger.error(f"解析 SKILL.md 失败: {e}")
            return {}
