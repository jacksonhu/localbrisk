/**
 * BusinessUnit Store - 状态管理
 * 管理 BusinessUnit、AssetBundle、Asset、Agent、Model、MCP 的状态和操作
 */

import { ref, computed, reactive } from "vue";
import { businessUnitApi, assetBundleApi, assetApi, agentApi, modelApi, mcpApi } from "@/services/api";
import type {
  BusinessUnit,
  BusinessUnitCreate,
  BusinessUnitUpdate,
  BusinessUnitTreeNode,
  BusinessUnitItem,
  AssetBundle,
  AssetBundleCreate,
  AssetBundleUpdate,
  Asset,
  AssetCreate,
  Agent,
  AgentCreate,
  Model,
  ModelCreate,
  MCP,
  MCPCreate,
  OutputFileContent,
} from "@/types/catalog";

// ============ 状态 ============

/** 所有 BusinessUnit 列表 */
const businessUnits = ref<BusinessUnit[]>([]);

/** 导航树 */
const businessUnitTree = ref<BusinessUnitTreeNode[]>([]);

/** 转换后的树形数据（保持展开状态） */
const businessUnitItems = ref<BusinessUnitItem[]>([]);

/** 节点展开状态存储 */
const expandedNodes = ref<Set<string>>(new Set());

/** 当前选中的 BusinessUnit */
const selectedBusinessUnit = ref<BusinessUnit | null>(null);

/** 当前选中的 AssetBundle */
const selectedAssetBundle = ref<AssetBundle | null>(null);

/** 当前选中的 Asset */
const selectedAsset = ref<Asset | null>(null);

/** 当前选中的 Agent */
const selectedAgent = ref<Agent | null>(null);

/** 当前选中的 Model */
const selectedModel = ref<Model | null>(null);

/** 当前选中的 Memory 名称（用于显示 Memory 详情页） */
const selectedMemoryName = ref<string>('');

/** 当前选中的 Skill 名称（用于显示 Skill 详情页） */
const selectedSkillName = ref<string>('');

/** 当前 AssetBundle 下的 Asset 列表 */
const currentAssets = ref<Asset[]>([]);

/** 加载状态 */
const loading = reactive({
  businessUnits: false,
  tree: false,
  bundles: false,
  assets: false,
  creating: false,
  deleting: false,
});

/** 错误状态 */
const error = ref<string | null>(null);

/** 当前选中的 BusinessUnit 的 AssetBundle 列表 */
const currentAssetBundles = computed<AssetBundle[]>(() => {
  return selectedBusinessUnit.value?.asset_bundles || [];
});

/** 当前选中的 MCP */
const selectedMCP = ref<MCP | null>(null);

/** 当前选中的 MCP 名称（用于显示 MCP 详情页） */
const selectedMCPName = ref<string>('');

/** 当前选中的 output 文件 */
const selectedOutputFile = ref<OutputFileContent | null>(null);

/**
 * 计算当前选中节点在树中的 ID
 * 
 * 节点 ID 格式（与后端保持一致）：
 * - BusinessUnit: businessUnitId (如 "market_analysis")
 * - AssetBundle: bundleId (如 "market_analysis_default")
 * - Agent: agentId (如 "market_analysis_agent_dd")
 * - Memory: {agentId}_prompt_{memoryName} (如 "market_analysis_agent_dd_prompt_ddd.md")
 * - Skill: {agentId}_skill_{skillName} (如 "market_analysis_agent_dd_skill_xxx")
 * - Model: modelId (如 "market_analysis_agent_dd_model_xxx")
 * - MCP: {agentId}_mcp_{mcpName}
 * - Asset: assetId
 * 
 * 优先级（从高到低）：Memory/Skill/MCP > Model > Asset > AssetBundle > Agent > BusinessUnit
 */
const selectedNodeId = computed<string | undefined>(() => {
  // 1. Memory 选中时（必须同时有 Agent 和 PromptName）
  if (selectedMemoryName.value && selectedAgent.value) {
    // Memory 节点 ID 格式: {agent.id}_prompt_{memoryName}
    // 注意：memoryName 包含文件扩展名（如 ddd.md）
    return `${selectedAgent.value.id}_prompt_${selectedMemoryName.value}`;
  }
  
  // 1.5 Skill 选中时（必须同时有 Agent 和 SkillName）
  if (selectedSkillName.value && selectedAgent.value) {
    // Skill 节点 ID 格式: {agent.id}_skill_{skillName}
    return `${selectedAgent.value.id}_skill_${selectedSkillName.value}`;
  }
  
  // 1.6 MCP 选中时（必须同时有 Agent 和 MCPName）
  if (selectedMCPName.value && selectedAgent.value) {
    // MCP 节点 ID 格式: {agent.id}_mcp_{mcpName}
    return `${selectedAgent.value.id}_mcp_${selectedMCPName.value}`;
  }
  
  // 2. Output 文件选中时
  if (selectedOutputFile.value && selectedAgent.value) {
    return `${selectedAgent.value.id}_output/${selectedOutputFile.value.relative_path}`;
  }

  // 3. Model 选中时
  if (selectedModel.value) {
    return selectedModel.value.id;
  }
  
  // 3. Asset 选中时
  if (selectedAsset.value) {
    return selectedAsset.value.id;
  }
  
  // 4. AssetBundle 选中时（但没有选中其子节点）
  if (selectedAssetBundle.value) {
    return selectedAssetBundle.value.id;
  }
  
  // 5. Agent 选中时（但没有选中其子节点）
  if (selectedAgent.value) {
    return selectedAgent.value.id;
  }
  
  // 6. BusinessUnit 选中时
  if (selectedBusinessUnit.value) {
    return selectedBusinessUnit.value.id;
  }
  
  return undefined;
});

// ============ 辅助函数 ============

/** 资产类型显示配置 */
const ASSET_TYPE_CONFIG: Record<string, { label: string; icon: string }> = {
  table: { label: 'Tables', icon: 'table' },
  volume: { label: 'Volumes', icon: 'folder-open' },
  function: { label: 'Functions', icon: 'code' },
  model: { label: 'Models', icon: 'cpu' },
  agent: { label: 'Agents', icon: 'bot' },
  note: { label: 'Notes', icon: 'file-text' },
};

/**
 * 归一化 Agent 子节点：兼容 prompts/memories 命名，并确保始终展示 Memories 目录
 */
function normalizeAgentChildren(agentNode: BusinessUnitTreeNode): BusinessUnitTreeNode[] {
  const originalChildren = agentNode.children || [];
  const agentMemoryNames = selectedAgent.value?.name === agentNode.name
    ? (selectedAgent.value.memories || [])
    : [];

  const buildMemoryChildren = (names: string[]): BusinessUnitTreeNode[] => {
    const metadata = {
      business_unit_id: agentNode.metadata?.business_unit_id,
      agent_name: agentNode.name,
    };
    return names.map((memoryName) => ({
      id: `${agentNode.id}_prompt_${memoryName}`,
      name: memoryName,
      display_name: memoryName,
      node_type: 'prompt',
      children: [],
      metadata,
    }));
  };

  const normalizedChildren = originalChildren.map((child) => {
    if (child.node_type !== 'folder') {
      return child;
    }

    const folderName = (child.name || '').toLowerCase();

    if (folderName === 'prompts' || folderName === 'memories') {
      const folderChildren = (child.children || []).map((memoryChild) => ({
        ...memoryChild,
        id: `${agentNode.id}_prompt_${(memoryChild.name || memoryChild.display_name || '').trim()}`,
        metadata: {
          business_unit_id: agentNode.metadata?.business_unit_id,
          agent_name: agentNode.name,
          ...(memoryChild.metadata || {}),
        },
      }));

      const fallbackChildren = folderChildren.length > 0 ? folderChildren : buildMemoryChildren(agentMemoryNames);

      return {
        ...child,
        id: `${agentNode.id}_memories`,
        name: 'memories',
        display_name: 'Memories',
        children: fallbackChildren,
        metadata: {
          business_unit_id: agentNode.metadata?.business_unit_id,
          agent_name: agentNode.name,
          ...(child.metadata || {}),
        },
      };
    }

    if (folderName === 'skills' || folderName === 'models' || folderName === 'mcps') {
      const displayMap: Record<string, string> = {
        skills: 'Skills',
        models: 'Models',
        mcps: 'MCPs',
      };
      return {
        ...child,
        id: `${agentNode.id}_${folderName}`,
        name: folderName,
        display_name: displayMap[folderName],
        children: child.children || [],
        metadata: {
          business_unit_id: agentNode.metadata?.business_unit_id,
          agent_name: agentNode.name,
          ...(child.metadata || {}),
        },
      };
    }

    return child;
  });

  const ensureFolderSpecs: Array<{ key: 'skills' | 'memories' | 'models' | 'mcps'; displayName: string }> = [
    { key: 'skills', displayName: 'Skills' },
    { key: 'memories', displayName: 'Memories' },
    { key: 'models', displayName: 'Models' },
    { key: 'mcps', displayName: 'MCPs' },
  ];

  for (const folderSpec of ensureFolderSpecs) {
    const exists = normalizedChildren.some((child) => {
      if (child.node_type !== 'folder') return false;
      const name = (child.name || '').toLowerCase();
      if (folderSpec.key === 'memories') {
        return name === 'memories' || name === 'prompts';
      }
      return name === folderSpec.key;
    });

    if (exists) continue;

    normalizedChildren.push({
      id: `${agentNode.id}_${folderSpec.key}`,
      name: folderSpec.key,
      display_name: folderSpec.displayName,
      node_type: 'folder',
      children: folderSpec.key === 'memories' ? buildMemoryChildren(agentMemoryNames) : [],
      metadata: {
        business_unit_id: agentNode.metadata?.business_unit_id,
        agent_name: agentNode.name,
      },
    });
  }

  const orderMap: Record<string, number> = {
    skills: 1,
    memories: 2,
    models: 3,
    mcps: 4,
    output: 5,
  };

  return normalizedChildren.sort((a, b) => {
    const getOrder = (node: BusinessUnitTreeNode): number => {
      if (node.node_type === 'output') return orderMap.output;
      if (node.node_type === 'folder') {
        const name = (node.name || '').toLowerCase();
        const normalizedName = name === 'prompts' ? 'memories' : name;
        return orderMap[normalizedName] || 999;
      }
      return 999;
    };
    return getOrder(a) - getOrder(b);
  });
}

/**
 * 将 BusinessUnitTreeNode 转换为 BusinessUnitItem
 * 对于 AssetBundle 节点，将其子节点按资产类型分组
 * @param nodes 原始树节点
 * @param _parentType 父节点类型（用于判断是否需要分组，预留参数）
 */
function convertTreeToItems(nodes: BusinessUnitTreeNode[], _parentType?: string): BusinessUnitItem[] {
  if (!nodes || !Array.isArray(nodes)) {
    return [];
  }
  return nodes.map((node) => {
    let children: BusinessUnitItem[] | undefined;
    const normalizedNodeChildren = node.node_type === 'agent' ? normalizeAgentChildren(node) : node.children;

    // 如果是 AssetBundle 节点且有子节点，按资产类型分组
    if (node.node_type === 'asset_bundle' && normalizedNodeChildren && normalizedNodeChildren.length > 0) {
      children = groupAssetsByType(normalizedNodeChildren, node.id || '');
    } else if (normalizedNodeChildren && normalizedNodeChildren.length > 0) {
      // 递归转换子节点
      children = convertTreeToItems(normalizedNodeChildren, node.node_type);
    } else if (node.node_type === 'folder' && node.children) {
      // folder 类型即使没有子节点也保持 children 为空数组（用于正确显示展开状态）
      children = [];
    }

    const item: BusinessUnitItem = {
      id: node.id || '',
      name: node.display_name || node.name || '',
      type: node.node_type || 'business_unit',
      icon: node.icon || getIconForType(node.node_type || 'business_unit'),
      expanded: expandedNodes.value.has(node.id || ''),
      bundle_type: node.bundle_type,
      metadata: node.metadata || {},
      children: children,
    };
    return item;
  });
}

/**
 * 将资产按类型分组
 * @param assets 资产节点列表
 * @param bundleId AssetBundle ID（用于生成分组节点 ID）
 */
function groupAssetsByType(assets: BusinessUnitTreeNode[], bundleId: string): BusinessUnitItem[] {
  // 按类型分组
  const grouped: Record<string, BusinessUnitTreeNode[]> = {};
  
  for (const asset of assets) {
    const assetType = asset.node_type || 'note';
    if (!grouped[assetType]) {
      grouped[assetType] = [];
    }
    grouped[assetType].push(asset);
  }
  
  // 转换为分组节点，按预定义顺序排序
  const typeOrder = ['table', 'volume', 'function', 'model', 'agent', 'note'];
  const result: BusinessUnitItem[] = [];
  
  for (const assetType of typeOrder) {
    if (grouped[assetType] && grouped[assetType].length > 0) {
      const config = ASSET_TYPE_CONFIG[assetType] || { label: assetType, icon: 'file' };
      const groupId = `${bundleId}_type_${assetType}`;
      
      const groupItem: BusinessUnitItem = {
        id: groupId,
        name: `${config.label} (${grouped[assetType].length})`,
        type: 'asset_type',
        icon: config.icon,
        expanded: expandedNodes.value.has(groupId),
        metadata: { assetType },
        children: grouped[assetType].map((asset) => ({
          id: asset.id || '',
          name: asset.display_name || asset.name || '',
          type: asset.node_type || 'note',
          icon: asset.icon || getIconForType(asset.node_type || 'note'),
          expanded: false,
          metadata: asset.metadata || {},
        })),
      };
      
      result.push(groupItem);
    }
  }
  
  // 处理未知类型
  for (const assetType of Object.keys(grouped)) {
    if (!typeOrder.includes(assetType)) {
      const groupId = `${bundleId}_type_${assetType}`;
      const groupItem: BusinessUnitItem = {
        id: groupId,
        name: `${assetType} (${grouped[assetType].length})`,
        type: 'asset_type',
        icon: 'file',
        expanded: expandedNodes.value.has(groupId),
        metadata: { assetType },
        children: grouped[assetType].map((asset) => ({
          id: asset.id || '',
          name: asset.display_name || asset.name || '',
          type: asset.node_type || 'note',
          icon: asset.icon || getIconForType(asset.node_type || 'note'),
          expanded: false,
          metadata: asset.metadata || {},
        })),
      };
      result.push(groupItem);
    }
  }
  
  return result;
}

/**
 * 更新树形数据
 */
function updateBusinessUnitItems(): void {
  // 重新转换树形数据，使用新数组触发响应式更新
  const newItems = convertTreeToItems(businessUnitTree.value);
  businessUnitItems.value = newItems;
}

/**
 * 切换节点展开状态
 */
function toggleNodeExpanded(nodeId: string, expanded?: boolean): void {
  if (expanded === undefined) {
    // 切换状态
    if (expandedNodes.value.has(nodeId)) {
      expandedNodes.value.delete(nodeId);
    } else {
      expandedNodes.value.add(nodeId);
    }
  } else if (expanded) {
    expandedNodes.value.add(nodeId);
  } else {
    expandedNodes.value.delete(nodeId);
  }
  // 更新树形数据 - 使用 nextTick 确保 Vue 响应式系统能检测到变化
  updateBusinessUnitItems();
}

/**
 * 根据节点类型获取默认图标
 */
function getIconForType(type: string): string {
  const iconMap: Record<string, string> = {
    business_unit: "folder",
    asset_bundle: "database",
    table: "table",
    volume: "folder-open",
    agent: "bot",
    note: "file-text",
  };
  return iconMap[type] || "file";
}

// ============ 统一的选择状态管理 ============

/**
 * 选择类型枚举
 * 定义了所有可选择的节点类型，用于统一的状态清除逻辑
 */
type SelectionType = 'business_unit' | 'asset_bundle' | 'asset' | 'model' | 'agent' | 'prompt' | 'skill' | 'mcp' | 'output_file';

/**
 * 准备选择某个类型的节点
 * 清除与该类型不兼容的选择状态
 * 
 * 树形结构说明：
 * BusinessUnit (根)
 * ├── AssetBundle 分支
 * │   ├── AssetBundle
 * │   └── Asset (table/volume)
 * └── Agent 分支
 *     ├── Agent
 *     ├── Memory/Skill
 *     ├── Model
 *     └── MCP
 * 
 * 规则：
 * - AssetBundle 分支和 Agent 分支互斥，选择一个分支时清除另一个分支
 * - 选择父级节点时，清除子级节点的选择
 */
function prepareForSelection(targetType: SelectionType): void {
  // AssetBundle 分支类型
  const assetBundleBranch: SelectionType[] = ['asset_bundle', 'asset'];
  // Agent 分支类型
  const agentBranch: SelectionType[] = ['agent', 'prompt', 'skill', 'model', 'mcp', 'output_file'];
  
  if (assetBundleBranch.includes(targetType)) {
    // 选择 AssetBundle 分支，清除 Agent 分支
    selectedAgent.value = null;
    selectedMemoryName.value = '';
    selectedSkillName.value = '';
    selectedModel.value = null;
    selectedMCP.value = null;
    selectedMCPName.value = '';
    selectedOutputFile.value = null;
    
    // 如果选择 AssetBundle，清除 Asset（选择父级清除子级）
    if (targetType === 'asset_bundle') {
      selectedAsset.value = null;
      currentAssets.value = [];
    }
  } else if (agentBranch.includes(targetType)) {
    // 选择 Agent 分支，清除 AssetBundle 分支
    selectedAssetBundle.value = null;
    selectedAsset.value = null;
    currentAssets.value = [];
    
    // 如果选择 Agent，清除所有子级（Memory、Skill、Model、MCP）
    if (targetType === 'agent') {
      selectedMemoryName.value = '';
      selectedSkillName.value = '';
      selectedModel.value = null;
      selectedMCP.value = null;
      selectedMCPName.value = '';
      selectedOutputFile.value = null;
    }
    // 如果选择 Memory，清除其他同级
    if (targetType === 'prompt') {
      selectedSkillName.value = '';
      selectedModel.value = null;
      selectedMCP.value = null;
      selectedMCPName.value = '';
      selectedOutputFile.value = null;
    }
    // 如果选择 Skill，清除其他同级
    if (targetType === 'skill') {
      selectedMemoryName.value = '';
      selectedModel.value = null;
      selectedMCP.value = null;
      selectedMCPName.value = '';
      selectedOutputFile.value = null;
    }
    // 如果选择 Model，清除其他同级
    if (targetType === 'model') {
      selectedMemoryName.value = '';
      selectedSkillName.value = '';
      selectedMCP.value = null;
      selectedMCPName.value = '';
      selectedOutputFile.value = null;
    }
    // 如果选择 MCP，清除其他同级
    if (targetType === 'mcp') {
      selectedMemoryName.value = '';
      selectedSkillName.value = '';
      selectedModel.value = null;
      selectedOutputFile.value = null;
    }
    // 如果选择 output 文件，清除其他同级
    if (targetType === 'output_file') {
      selectedMemoryName.value = '';
      selectedSkillName.value = '';
      selectedModel.value = null;
      selectedMCP.value = null;
      selectedMCPName.value = '';
    }
  }
}

// ============ Actions ============

/**
 * 获取所有 BusinessUnit
 */
async function fetchBusinessUnits(): Promise<void> {
  loading.businessUnits = true;
  error.value = null;
  
  try {
    businessUnits.value = await businessUnitApi.list();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 BusinessUnit 列表失败";
    console.error("fetchBusinessUnits error:", e);
  } finally {
    loading.businessUnits = false;
  }
}

/**
 * 获取导航树
 */
async function fetchTree(): Promise<void> {
  loading.tree = true;
  error.value = null;
  
  try {
    const tree = await businessUnitApi.getTree();
    businessUnitTree.value = tree;
    // 更新树形数据
    updateBusinessUnitItems();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取导航树失败";
    console.error("fetchTree error:", e);
  } finally {
    loading.tree = false;
  }
}

/**
 * 获取单个 BusinessUnit 详情
 */
async function fetchBusinessUnit(businessUnitId: string): Promise<BusinessUnit | null> {
  loading.businessUnits = true;
  error.value = null;
  
  try {
    const businessUnit = await businessUnitApi.get(businessUnitId);
    selectedBusinessUnit.value = businessUnit;
    return businessUnit;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 BusinessUnit 详情失败";
    console.error("fetchBusinessUnit error:", e);
    return null;
  } finally {
    loading.businessUnits = false;
  }
}

/**
 * 创建 BusinessUnit
 */
async function createBusinessUnit(data: BusinessUnitCreate): Promise<BusinessUnit | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newBusinessUnit = await businessUnitApi.create(data);
    // 刷新列表和树
    await Promise.all([fetchBusinessUnits(), fetchTree()]);
    return newBusinessUnit;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 BusinessUnit 失败";
    console.error("createBusinessUnit error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 BusinessUnit
 */
async function deleteBusinessUnit(businessUnitId: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await businessUnitApi.delete(businessUnitId);
    // 清除选中状态
    if (selectedBusinessUnit.value?.id === businessUnitId) {
      selectedBusinessUnit.value = null;
      selectedAssetBundle.value = null;
      currentAssets.value = [];
    }
    // 刷新列表和树
    await Promise.all([fetchBusinessUnits(), fetchTree()]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 BusinessUnit 失败";
    console.error("deleteBusinessUnit error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 更新 BusinessUnit
 */
async function updateBusinessUnit(businessUnitId: string, data: BusinessUnitUpdate): Promise<BusinessUnit | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const updatedBusinessUnit = await businessUnitApi.update(businessUnitId, data);
    // 更新选中的 BusinessUnit
    if (selectedBusinessUnit.value?.id === businessUnitId) {
      selectedBusinessUnit.value = updatedBusinessUnit;
    }
    // 刷新列表和树
    await Promise.all([fetchBusinessUnits(), fetchTree()]);
    return updatedBusinessUnit;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "更新 BusinessUnit 失败";
    console.error("updateBusinessUnit error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 选择 BusinessUnit
 * 只展开节点并获取详情，不清除其他状态（由调用方决定是否清除）
 */
async function selectBusinessUnit(businessUnitId: string): Promise<void> {
  // 先展开该节点
  toggleNodeExpanded(businessUnitId, true);
  // 获取详情
  await fetchBusinessUnit(businessUnitId);
}

/**
 * 确保 BusinessUnit 已加载
 * 如果当前选中的 BusinessUnit 不是目标，则加载目标 BusinessUnit
 * @returns 是否发生了 BusinessUnit 切换
 */
async function ensureBusinessUnitLoaded(businessUnitId: string): Promise<boolean> {
  if (!selectedBusinessUnit.value || selectedBusinessUnit.value.id !== businessUnitId) {
    await selectBusinessUnit(businessUnitId);
    return true;
  }
  return false;
}

/**
 * 获取 AssetBundle 列表
 */
async function fetchAssetBundles(businessUnitId: string): Promise<AssetBundle[]> {
  loading.bundles = true;
  error.value = null;
  
  try {
    return await assetBundleApi.list(businessUnitId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 AssetBundle 列表失败";
    console.error("fetchAssetBundles error:", e);
    return [];
  } finally {
    loading.bundles = false;
  }
}

/**
 * 创建 AssetBundle
 */
async function createAssetBundle(businessUnitId: string, data: AssetBundleCreate): Promise<AssetBundle | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newAssetBundle = await assetBundleApi.create(businessUnitId, data);
    // 刷新当前 BusinessUnit 和树
    await Promise.all([
      fetchBusinessUnit(businessUnitId),
      fetchTree(),
    ]);
    return newAssetBundle;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 AssetBundle 失败";
    console.error("createAssetBundle error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 AssetBundle
 */
async function deleteAssetBundle(businessUnitId: string, bundleName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await assetBundleApi.delete(businessUnitId, bundleName);
    // 清除选中状态
    if (selectedAssetBundle.value?.name === bundleName) {
      selectedAssetBundle.value = null;
      currentAssets.value = [];
    }
    // 刷新当前 BusinessUnit 和树
    await Promise.all([
      fetchBusinessUnit(businessUnitId),
      fetchTree(),
    ]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 AssetBundle 失败";
    console.error("deleteAssetBundle error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 更新 AssetBundle
 */
async function updateAssetBundle(businessUnitId: string, bundleName: string, data: AssetBundleUpdate): Promise<AssetBundle | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const updatedAssetBundle = await assetBundleApi.update(businessUnitId, bundleName, data);
    // 更新选中的 AssetBundle
    if (selectedAssetBundle.value?.name === bundleName) {
      selectedAssetBundle.value = updatedAssetBundle;
    }
    // 刷新当前 BusinessUnit
    await fetchBusinessUnit(businessUnitId);
    return updatedAssetBundle;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "更新 AssetBundle 失败";
    console.error("updateAssetBundle error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 选择 AssetBundle（从树形导航点击）
 * @param businessUnitId BusinessUnit ID
 * @param bundleName AssetBundle 名称
 */
async function selectAssetBundleByName(businessUnitId: string, bundleName: string): Promise<void> {
  // 准备选择 AssetBundle（清除不兼容的选择状态）
  prepareForSelection('asset_bundle');
  
  // 确保 BusinessUnit 已加载
  await ensureBusinessUnitLoaded(businessUnitId);
  
  // 从已加载的 BusinessUnit 中查找 AssetBundle
  const bundle = selectedBusinessUnit.value?.asset_bundles.find(s => s.name === bundleName);
  if (bundle) {
    selectedAssetBundle.value = bundle;
    // 注意：不在这里控制展开状态，由 BusinessUnitTree 的 toggle-expand 事件管理
    // 加载 Asset 列表
    await fetchAssets(businessUnitId, bundleName);
  }
}

/**
 * 选择 AssetBundle
 */
async function selectAssetBundle(businessUnitId: string, bundle: AssetBundle): Promise<void> {
  // 准备选择 AssetBundle
  prepareForSelection('asset_bundle');
  
  selectedAssetBundle.value = bundle;
  await fetchAssets(businessUnitId, bundle.name);
}

/**
 * 获取 Asset 列表
 */
async function fetchAssets(businessUnitId: string, bundleName: string): Promise<Asset[]> {
  loading.assets = true;
  error.value = null;
  
  try {
    const assets = await assetApi.list(businessUnitId, bundleName);
    currentAssets.value = assets;
    return assets;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 Asset 列表失败";
    console.error("fetchAssets error:", e);
    return [];
  } finally {
    loading.assets = false;
  }
}

/**
 * 创建 Asset
 */
async function createAsset(businessUnitId: string, bundleName: string, data: AssetCreate): Promise<Asset | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newAsset = await assetApi.create(businessUnitId, bundleName, data);
    // 刷新树和资产列表
    await Promise.all([
      fetchTree(),
      fetchAssets(businessUnitId, bundleName),
    ]);
    return newAsset;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 Asset 失败";
    console.error("createAsset error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 Asset
 */
async function deleteAsset(businessUnitId: string, bundleName: string, assetName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await assetApi.delete(businessUnitId, bundleName, assetName);
    // 刷新树和资产列表
    await Promise.all([
      fetchTree(),
      fetchAssets(businessUnitId, bundleName),
    ]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 Asset 失败";
    console.error("deleteAsset error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 清除 AssetBundle 选中状态
 */
function clearSelectedAssetBundle(): void {
  selectedAssetBundle.value = null;
  selectedAsset.value = null;
  currentAssets.value = [];
}

/**
 * 选择 Asset
 */
function selectAsset(asset: Asset): void {
  // 准备选择 Asset
  prepareForSelection('asset');
  
  selectedAsset.value = asset;
}

/**
 * 通过名称选择 Asset（从树形导航点击）
 */
async function selectAssetByName(businessUnitId: string, bundleName: string, assetName: string): Promise<void> {
  // 准备选择 Asset
  prepareForSelection('asset');
  
  // 确保 BusinessUnit 已加载
  await ensureBusinessUnitLoaded(businessUnitId);
  
  // 确保 AssetBundle 已选中
  const bundle = selectedBusinessUnit.value?.asset_bundles.find(s => s.name === bundleName);
  if (bundle) {
    selectedAssetBundle.value = bundle;
    // 总是重新加载 Asset 列表，确保数据是最新的
    await fetchAssets(businessUnitId, bundleName);
  }
  
  // 从 Asset 列表中查找
  const asset = currentAssets.value.find(a => a.name === assetName);
  if (asset) {
    selectedAsset.value = asset;
  }
}

/**
 * 清除 Asset 选中状态
 */
function clearSelectedAsset(): void {
  selectedAsset.value = null;
}

// ============ Agent Actions ============

/**
 * 创建 Agent
 */
async function createAgent(businessUnitId: string, data: AgentCreate): Promise<Agent | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newAgent = await agentApi.create(businessUnitId, data);
    // 刷新树
    await fetchTree();
    return newAgent;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 Agent 失败";
    console.error("createAgent error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 Agent
 */
async function deleteAgent(businessUnitId: string, agentName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await agentApi.delete(businessUnitId, agentName);
    // 清除选中状态
    if (selectedAgent.value?.name === agentName) {
      selectedAgent.value = null;
    }
    // 刷新树
    await fetchTree();
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 Agent 失败";
    console.error("deleteAgent error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 选择 Agent
 */
async function selectAgent(businessUnitId: string, agentName: string): Promise<void> {
  // 准备选择 Agent（清除 AssetBundle 分支的选择状态）
  prepareForSelection('agent');
  
  try {
    // 确保 BusinessUnit 已加载
    await ensureBusinessUnitLoaded(businessUnitId);
    
    const agent = await agentApi.get(businessUnitId, agentName);
    selectedAgent.value = agent;
    
    // 展开 Agent 节点（需要根据 agent.id 来展开）
    if (agent.id) {
      toggleNodeExpanded(agent.id, true);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 Agent 详情失败";
    console.error("selectAgent error:", e);
  }
}

/**
 * 清除 Agent 选中状态
 */
function clearSelectedAgent(): void {
  selectedAgent.value = null;
  selectedMemoryName.value = '';
  selectedSkillName.value = '';
  selectedMCPName.value = '';
  selectedMCP.value = null;
  selectedModel.value = null;
  selectedOutputFile.value = null;
}

/**
 * 刷新当前选中的 Agent 数据
 * 不改变选中状态，只更新 Agent 数据（如 capabilities 配置）
 */
async function refreshSelectedAgent(): Promise<void> {
  if (!selectedAgent.value || !selectedBusinessUnit.value) return;
  
  try {
    const agent = await agentApi.get(selectedBusinessUnit.value.id, selectedAgent.value.name);
    selectedAgent.value = agent;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "刷新 Agent 数据失败";
    console.error("refreshSelectedAgent error:", e);
  }
}

// ============ Memory 操作 ============

/**
 * 选择 Memory
 * @param businessUnitId BusinessUnit ID
 * @param agentName Agent 名称
 * @param memoryName Memory 名称
 */
async function selectMemory(businessUnitId: string, agentName: string, memoryName: string): Promise<void> {
  // 准备选择 Memory
  prepareForSelection('prompt');
  
  // 确保 Agent 已选中（selectAgent 会处理 BusinessUnit 加载和状态清除）
  const needLoadAgent = !selectedAgent.value || 
                        selectedAgent.value.name !== agentName || 
                        selectedBusinessUnit.value?.id !== businessUnitId;
  
  if (needLoadAgent) {
    await selectAgent(businessUnitId, agentName);
  }
  
  // 设置选中的 Memory 名称
  selectedMemoryName.value = memoryName;
}

/**
 * 清除 Memory 选中状态
 */
function clearSelectedMemory(): void {
  selectedMemoryName.value = '';
}

// ============ Skill 操作 ============

/**
 * 选择 Skill
 * @param businessUnitId BusinessUnit ID
 * @param agentName Agent 名称
 * @param skillName Skill 名称
 */
async function selectSkill(businessUnitId: string, agentName: string, skillName: string): Promise<void> {
  // 准备选择 Skill
  prepareForSelection('skill');
  
  // 确保 Agent 已选中（selectAgent 会处理 BusinessUnit 加载和状态清除）
  const needLoadAgent = !selectedAgent.value || 
                        selectedAgent.value.name !== agentName || 
                        selectedBusinessUnit.value?.id !== businessUnitId;
  
  if (needLoadAgent) {
    await selectAgent(businessUnitId, agentName);
  }
  
  // 设置选中的 Skill 名称
  selectedSkillName.value = skillName;
}

/**
 * 清除 Skill 选中状态
 */
function clearSelectedSkill(): void {
  selectedSkillName.value = '';
}

// ============ Model 操作（Agent 级别） ============

/**
 * 创建 Model（在 Agent 下）
 */
async function createModel(businessUnitId: string, agentName: string, data: ModelCreate): Promise<Model | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newModel = await modelApi.create(businessUnitId, agentName, data);
    // 刷新树和 Agent
    await Promise.all([fetchTree(), refreshSelectedAgent()]);
    return newModel;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建模型失败";
    console.error("createModel error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 Model
 */
async function deleteModel(businessUnitId: string, agentName: string, modelName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await modelApi.delete(businessUnitId, agentName, modelName);
    // 清除选中状态
    if (selectedModel.value?.name === modelName) {
      selectedModel.value = null;
    }
    // 刷新树和 Agent
    await Promise.all([fetchTree(), refreshSelectedAgent()]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除模型失败";
    console.error("deleteModel error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 选择 Model（Agent 下的 Model）
 */
async function selectModel(businessUnitId: string, agentName: string, modelName: string): Promise<void> {
  // 准备选择 Model
  prepareForSelection('model');
  
  try {
    // 确保 Agent 已选中
    const needLoadAgent = !selectedAgent.value || 
                          selectedAgent.value.name !== agentName || 
                          selectedBusinessUnit.value?.id !== businessUnitId;
    
    if (needLoadAgent) {
      await selectAgent(businessUnitId, agentName);
    }
    
    const model = await modelApi.get(businessUnitId, agentName, modelName);
    selectedModel.value = model;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取模型详情失败";
    console.error("selectModel error:", e);
  }
}

/**
 * 启用 Model（禁用其他 Model）
 */
async function enableModel(businessUnitId: string, agentName: string, modelName: string): Promise<boolean> {
  try {
    await modelApi.enable(businessUnitId, agentName, modelName);
    // 刷新树和 Agent
    await Promise.all([fetchTree(), refreshSelectedAgent()]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "启用模型失败";
    console.error("enableModel error:", e);
    return false;
  }
}

/**
 * 清除 Model 选中状态
 */
function clearSelectedModel(): void {
  selectedModel.value = null;
}

// ============ MCP 操作（Agent 级别） ============

/**
 * 创建 MCP（在 Agent 下）
 */
async function createMCP(businessUnitId: string, agentName: string, data: MCPCreate): Promise<MCP | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newMCP = await mcpApi.create(businessUnitId, agentName, data);
    // 刷新树和 Agent
    await Promise.all([fetchTree(), refreshSelectedAgent()]);
    return newMCP;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 MCP 失败";
    console.error("createMCP error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 MCP
 */
async function deleteMCP(businessUnitId: string, agentName: string, mcpName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await mcpApi.delete(businessUnitId, agentName, mcpName);
    // 清除选中状态
    if (selectedMCP.value?.name === mcpName) {
      selectedMCP.value = null;
      selectedMCPName.value = '';
    }
    // 刷新树和 Agent
    await Promise.all([fetchTree(), refreshSelectedAgent()]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 MCP 失败";
    console.error("deleteMCP error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 选择 MCP
 */
async function selectMCP(businessUnitId: string, agentName: string, mcpName: string): Promise<void> {
  // 准备选择 MCP（与 Model 类似，属于 Agent 分支）
  prepareForSelection('mcp');
  
  try {
    // 确保 Agent 已选中
    const needLoadAgent = !selectedAgent.value || 
                          selectedAgent.value.name !== agentName || 
                          selectedBusinessUnit.value?.id !== businessUnitId;
    
    if (needLoadAgent) {
      await selectAgent(businessUnitId, agentName);
    }
    
    const mcp = await mcpApi.get(businessUnitId, agentName, mcpName);
    selectedMCP.value = mcp;
    selectedMCPName.value = mcpName;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 MCP 详情失败";
    console.error("selectMCP error:", e);
  }
}

/**
 * 清除 MCP 选中状态
 */
function clearSelectedMCP(): void {
  selectedMCP.value = null;
  selectedMCPName.value = '';
}

/**
 * 选择 output 文件
 */
async function selectOutputFile(businessUnitId: string, agentName: string, relativePath: string): Promise<void> {
  prepareForSelection('output_file');

  const needLoadAgent = !selectedAgent.value || 
                        selectedAgent.value.name !== agentName || 
                        selectedBusinessUnit.value?.id !== businessUnitId;

  if (needLoadAgent) {
    await selectAgent(businessUnitId, agentName);
  }

  try {
    selectedOutputFile.value = await businessUnitApi.getOutputFileContent(businessUnitId, agentName, relativePath);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "读取 output 文件失败";
    console.error("selectOutputFile error:", e);
  }
}

/**
 * 清除 output 文件选中状态
 */
function clearSelectedOutputFile(): void {
  selectedOutputFile.value = null;
}

/**
 * 清除错误
 */
function clearError(): void {
  error.value = null;
}

/**
 * 重置状态
 */
function reset(): void {
  businessUnits.value = [];
  businessUnitTree.value = [];
  businessUnitItems.value = [];
  expandedNodes.value.clear();
  selectedBusinessUnit.value = null;
  selectedAssetBundle.value = null;
  selectedAgent.value = null;
  selectedModel.value = null;
  selectedMCP.value = null;
  selectedMCPName.value = '';
  selectedOutputFile.value = null;
  currentAssets.value = [];
  error.value = null;
}

// ============ 导出 ============

export function useBusinessUnitStore() {
  return {
    // 状态
    businessUnits,
    businessUnitTree,
    businessUnitItems,
    expandedNodes,
    selectedBusinessUnit,
    selectedAssetBundle,
    selectedAsset,
    selectedAgent,
    selectedModel,
    selectedMCP,
    selectedMCPName,
    selectedOutputFile,
    selectedMemoryName,
    selectedSkillName,
    selectedNodeId,  // 统一的选中节点 ID 计算
    currentAssetBundles,
    currentAssets,
    loading,
    error,
    
    // Actions
    fetchBusinessUnits,
    fetchTree,
    fetchBusinessUnit,
    createBusinessUnit,
    updateBusinessUnit,
    deleteBusinessUnit,
    selectBusinessUnit,
    toggleNodeExpanded,
    fetchAssetBundles,
    createAssetBundle,
    updateAssetBundle,
    deleteAssetBundle,
    selectAssetBundle,
    selectAssetBundleByName,
    clearSelectedAssetBundle,
    fetchAssets,
    createAsset,
    deleteAsset,
    selectAsset,
    selectAssetByName,
    clearSelectedAsset,
    createAgent,
    deleteAgent,
    selectAgent,
    refreshSelectedAgent,  // 刷新 Agent 数据但不改变选中状态
    clearSelectedAgent,
    selectMemory,
    clearSelectedMemory,
    selectSkill,
    clearSelectedSkill,
    createModel,
    deleteModel,
    selectModel,
    enableModel,
    clearSelectedModel,
    createMCP,
    deleteMCP,
    selectMCP,
    clearSelectedMCP,
    selectOutputFile,
    clearSelectedOutputFile,
    clearError,
    reset,
  };
}

export default useBusinessUnitStore;
