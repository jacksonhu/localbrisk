/**
 * Catalog Store - 状态管理
 * 管理 Catalog、Schema、Asset、Agent 的状态和操作
 */

import { ref, computed, reactive } from "vue";
import { catalogApi, schemaApi, assetApi, agentApi, modelApi } from "@/services/api";
import type {
  Catalog,
  CatalogCreate,
  CatalogUpdate,
  CatalogTreeNode,
  CatalogItem,
  Schema,
  SchemaCreate,
  SchemaUpdate,
  Asset,
  AssetCreate,
  Agent,
  AgentCreate,
  Model,
  ModelCreate,
} from "@/types/catalog";

// ============ 状态 ============

/** 所有 Catalog 列表 */
const catalogs = ref<Catalog[]>([]);

/** 导航树 */
const catalogTree = ref<CatalogTreeNode[]>([]);

/** 转换后的树形数据（保持展开状态） */
const catalogItems = ref<CatalogItem[]>([]);

/** 节点展开状态存储 */
const expandedNodes = ref<Set<string>>(new Set());

/** 当前选中的 Catalog */
const selectedCatalog = ref<Catalog | null>(null);

/** 当前选中的 Schema */
const selectedSchema = ref<Schema | null>(null);

/** 当前选中的 Asset */
const selectedAsset = ref<Asset | null>(null);

/** 当前选中的 Agent */
const selectedAgent = ref<Agent | null>(null);

/** 当前选中的 Model */
const selectedModel = ref<Model | null>(null);

/** 当前选中的 Prompt 名称（用于显示 Prompt 详情页） */
const selectedPromptName = ref<string>('');

/** 当前 Schema 下的 Asset 列表 */
const currentAssets = ref<Asset[]>([]);

/** 加载状态 */
const loading = reactive({
  catalogs: false,
  tree: false,
  schemas: false,
  assets: false,
  creating: false,
  deleting: false,
});

/** 错误状态 */
const error = ref<string | null>(null);

/** 当前选中的 Catalog 的 Schema 列表 */
const currentSchemas = computed<Schema[]>(() => {
  return selectedCatalog.value?.schemas || [];
});

/**
 * 计算当前选中节点在树中的 ID
 * 
 * 节点 ID 格式（与后端保持一致）：
 * - Catalog: catalogId (如 "market_analysis")
 * - Schema: schemaId (如 "market_analysis_default")
 * - Agent: agentId (如 "market_analysis_agent_dd")
 * - Prompt: {agentId}_prompt_{promptName} (如 "market_analysis_agent_dd_prompt_ddd.md")
 * - Skill: {agentId}_skill_{skillName} (如 "market_analysis_agent_dd_skill_xxx.py")
 * - Asset: assetId
 * - Model: modelId
 * 
 * 优先级（从高到低）：Prompt/Skill > Model > Asset > Schema > Agent > Catalog
 */
const selectedNodeId = computed<string | undefined>(() => {
  // 1. Prompt/Skill 选中时（必须同时有 Agent 和 PromptName）
  if (selectedPromptName.value && selectedAgent.value) {
    // Prompt 节点 ID 格式: {agent.id}_prompt_{promptName}
    // 注意：promptName 包含文件扩展名（如 ddd.md）
    return `${selectedAgent.value.id}_prompt_${selectedPromptName.value}`;
  }
  
  // 2. Model 选中时
  if (selectedModel.value) {
    return selectedModel.value.id;
  }
  
  // 3. Asset 选中时
  if (selectedAsset.value) {
    return selectedAsset.value.id;
  }
  
  // 4. Schema 选中时（但没有选中其子节点）
  if (selectedSchema.value) {
    return selectedSchema.value.id;
  }
  
  // 5. Agent 选中时（但没有选中其子节点）
  if (selectedAgent.value) {
    return selectedAgent.value.id;
  }
  
  // 6. Catalog 选中时
  if (selectedCatalog.value) {
    return selectedCatalog.value.id;
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
 * 将 CatalogTreeNode 转换为 CatalogItem
 * 对于 Schema 节点，将其子节点按资产类型分组
 * @param nodes 原始树节点
 * @param _parentType 父节点类型（用于判断是否需要分组，预留参数）
 */
function convertTreeToItems(nodes: CatalogTreeNode[], _parentType?: string): CatalogItem[] {
  if (!nodes || !Array.isArray(nodes)) {
    return [];
  }
  return nodes.map((node) => {
    let children: CatalogItem[] | undefined;
    
    // 如果是 Schema 节点且有子节点，按资产类型分组
    if (node.node_type === 'schema' && node.children && node.children.length > 0) {
      children = groupAssetsByType(node.children, node.id || '');
    } else if (node.children && node.children.length > 0) {
      // 递归转换子节点
      children = convertTreeToItems(node.children, node.node_type);
    } else if (node.node_type === 'folder' && node.children) {
      // folder 类型即使没有子节点也保持 children 为空数组（用于正确显示展开状态）
      children = [];
    }
    
    const item: CatalogItem = {
      id: node.id || '',
      name: node.display_name || node.name || '',
      type: node.node_type || 'catalog',
      icon: node.icon || getIconForType(node.node_type || 'catalog'),
      expanded: expandedNodes.value.has(node.id || ''),
      readonly: node.readonly || false,
      source: node.source,
      metadata: node.metadata || {},
      children: children,
    };
    return item;
  });
}

/**
 * 将资产按类型分组
 * @param assets 资产节点列表
 * @param schemaId Schema ID（用于生成分组节点 ID）
 */
function groupAssetsByType(assets: CatalogTreeNode[], schemaId: string): CatalogItem[] {
  // 按类型分组
  const grouped: Record<string, CatalogTreeNode[]> = {};
  
  for (const asset of assets) {
    const assetType = asset.node_type || 'note';
    if (!grouped[assetType]) {
      grouped[assetType] = [];
    }
    grouped[assetType].push(asset);
  }
  
  // 转换为分组节点，按预定义顺序排序
  const typeOrder = ['table', 'volume', 'function', 'model', 'agent', 'note'];
  const result: CatalogItem[] = [];
  
  for (const assetType of typeOrder) {
    if (grouped[assetType] && grouped[assetType].length > 0) {
      const config = ASSET_TYPE_CONFIG[assetType] || { label: assetType, icon: 'file' };
      const groupId = `${schemaId}_type_${assetType}`;
      
      const groupItem: CatalogItem = {
        id: groupId,
        name: `${config.label} (${grouped[assetType].length})`,
        type: 'asset_type',
        icon: config.icon,
        expanded: expandedNodes.value.has(groupId),
        readonly: false,
        metadata: { assetType },
        children: grouped[assetType].map((asset) => ({
          id: asset.id || '',
          name: asset.display_name || asset.name || '',
          type: asset.node_type || 'note',
          icon: asset.icon || getIconForType(asset.node_type || 'note'),
          expanded: false,
          readonly: asset.readonly || false,
          source: asset.source,
          metadata: asset.metadata || {},
        })),
      };
      
      result.push(groupItem);
    }
  }
  
  // 处理未知类型
  for (const assetType of Object.keys(grouped)) {
    if (!typeOrder.includes(assetType)) {
      const groupId = `${schemaId}_type_${assetType}`;
      const groupItem: CatalogItem = {
        id: groupId,
        name: `${assetType} (${grouped[assetType].length})`,
        type: 'asset_type',
        icon: 'file',
        expanded: expandedNodes.value.has(groupId),
        readonly: false,
        metadata: { assetType },
        children: grouped[assetType].map((asset) => ({
          id: asset.id || '',
          name: asset.display_name || asset.name || '',
          type: asset.node_type || 'note',
          icon: asset.icon || getIconForType(asset.node_type || 'note'),
          expanded: false,
          readonly: asset.readonly || false,
          source: asset.source,
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
function updateCatalogItems(): void {
  // 重新转换树形数据，使用新数组触发响应式更新
  const newItems = convertTreeToItems(catalogTree.value);
  catalogItems.value = newItems;
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
  updateCatalogItems();
}

/**
 * 根据节点类型获取默认图标
 */
function getIconForType(type: string): string {
  const iconMap: Record<string, string> = {
    catalog: "folder",
    schema: "database",
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
type SelectionType = 'catalog' | 'schema' | 'asset' | 'model' | 'agent' | 'prompt';

/**
 * 准备选择某个类型的节点
 * 清除与该类型不兼容的选择状态
 * 
 * 树形结构说明：
 * Catalog (根)
 * ├── Schema 分支
 * │   ├── Schema
 * │   ├── Asset (table/volume)
 * │   └── Model
 * └── Agent 分支
 *     ├── Agent
 *     └── Prompt/Skill
 * 
 * 规则：
 * - Schema 分支和 Agent 分支互斥，选择一个分支时清除另一个分支
 * - 同分支内，Asset 和 Model 互斥（都属于 Schema 的子级）
 * - 选择父级节点时，清除子级节点的选择
 */
function prepareForSelection(targetType: SelectionType): void {
  // Schema 分支类型
  const schemaBranch: SelectionType[] = ['schema', 'asset', 'model'];
  // Agent 分支类型
  const agentBranch: SelectionType[] = ['agent', 'prompt'];
  
  if (schemaBranch.includes(targetType)) {
    // 选择 Schema 分支，清除 Agent 分支
    selectedAgent.value = null;
    selectedPromptName.value = '';
    
    // 如果选择 Schema，清除 Asset 和 Model（选择父级清除子级）
    if (targetType === 'schema') {
      selectedAsset.value = null;
      selectedModel.value = null;
      currentAssets.value = [];
    }
    // 如果选择 Asset，清除 Model（同级互斥）
    if (targetType === 'asset') {
      selectedModel.value = null;
    }
    // 如果选择 Model，清除 Asset（同级互斥）
    if (targetType === 'model') {
      selectedAsset.value = null;
    }
  } else if (agentBranch.includes(targetType)) {
    // 选择 Agent 分支，清除 Schema 分支
    selectedSchema.value = null;
    selectedAsset.value = null;
    selectedModel.value = null;
    currentAssets.value = [];
    
    // 如果选择 Agent，清除 Prompt（选择父级清除子级）
    if (targetType === 'agent') {
      selectedPromptName.value = '';
    }
  }
}

// ============ Actions ============

/**
 * 获取所有 Catalog
 */
async function fetchCatalogs(): Promise<void> {
  loading.catalogs = true;
  error.value = null;
  
  try {
    catalogs.value = await catalogApi.list();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 Catalog 列表失败";
    console.error("fetchCatalogs error:", e);
  } finally {
    loading.catalogs = false;
  }
}

/**
 * 获取导航树
 */
async function fetchTree(): Promise<void> {
  loading.tree = true;
  error.value = null;
  
  try {
    const tree = await catalogApi.getTree();
    catalogTree.value = tree;
    // 更新树形数据
    updateCatalogItems();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取导航树失败";
    console.error("fetchTree error:", e);
  } finally {
    loading.tree = false;
  }
}

/**
 * 获取单个 Catalog 详情
 */
async function fetchCatalog(catalogId: string): Promise<Catalog | null> {
  loading.catalogs = true;
  error.value = null;
  
  try {
    const catalog = await catalogApi.get(catalogId);
    selectedCatalog.value = catalog;
    return catalog;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 Catalog 详情失败";
    console.error("fetchCatalog error:", e);
    return null;
  } finally {
    loading.catalogs = false;
  }
}

/**
 * 创建 Catalog
 */
async function createCatalog(data: CatalogCreate): Promise<Catalog | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newCatalog = await catalogApi.create(data);
    // 刷新列表和树
    await Promise.all([fetchCatalogs(), fetchTree()]);
    return newCatalog;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 Catalog 失败";
    console.error("createCatalog error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 Catalog
 */
async function deleteCatalog(catalogId: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await catalogApi.delete(catalogId);
    // 清除选中状态
    if (selectedCatalog.value?.id === catalogId) {
      selectedCatalog.value = null;
      selectedSchema.value = null;
      currentAssets.value = [];
    }
    // 刷新列表和树
    await Promise.all([fetchCatalogs(), fetchTree()]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 Catalog 失败";
    console.error("deleteCatalog error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 更新 Catalog
 */
async function updateCatalog(catalogId: string, data: CatalogUpdate): Promise<Catalog | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const updatedCatalog = await catalogApi.update(catalogId, data);
    // 更新选中的 Catalog
    if (selectedCatalog.value?.id === catalogId) {
      selectedCatalog.value = updatedCatalog;
    }
    // 刷新列表和树
    await Promise.all([fetchCatalogs(), fetchTree()]);
    return updatedCatalog;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "更新 Catalog 失败";
    console.error("updateCatalog error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 选择 Catalog
 * 只展开节点并获取详情，不清除其他状态（由调用方决定是否清除）
 */
async function selectCatalog(catalogId: string): Promise<void> {
  // 先展开该节点
  toggleNodeExpanded(catalogId, true);
  // 获取详情
  await fetchCatalog(catalogId);
}

/**
 * 确保 Catalog 已加载
 * 如果当前选中的 Catalog 不是目标，则加载目标 Catalog
 * @returns 是否发生了 Catalog 切换
 */
async function ensureCatalogLoaded(catalogId: string): Promise<boolean> {
  if (!selectedCatalog.value || selectedCatalog.value.id !== catalogId) {
    await selectCatalog(catalogId);
    return true;
  }
  return false;
}

/**
 * 获取 Schema 列表
 */
async function fetchSchemas(catalogId: string): Promise<Schema[]> {
  loading.schemas = true;
  error.value = null;
  
  try {
    return await schemaApi.list(catalogId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取 Schema 列表失败";
    console.error("fetchSchemas error:", e);
    return [];
  } finally {
    loading.schemas = false;
  }
}

/**
 * 创建 Schema
 */
async function createSchema(catalogId: string, data: SchemaCreate): Promise<Schema | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newSchema = await schemaApi.create(catalogId, data);
    // 刷新当前 Catalog 和树
    await Promise.all([
      fetchCatalog(catalogId),
      fetchTree(),
    ]);
    return newSchema;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建 Schema 失败";
    console.error("createSchema error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 删除 Schema
 */
async function deleteSchema(catalogId: string, schemaName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await schemaApi.delete(catalogId, schemaName);
    // 清除选中状态
    if (selectedSchema.value?.name === schemaName) {
      selectedSchema.value = null;
      currentAssets.value = [];
    }
    // 刷新当前 Catalog 和树
    await Promise.all([
      fetchCatalog(catalogId),
      fetchTree(),
    ]);
    return true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "删除 Schema 失败";
    console.error("deleteSchema error:", e);
    return false;
  } finally {
    loading.deleting = false;
  }
}

/**
 * 更新 Schema
 */
async function updateSchema(catalogId: string, schemaName: string, data: SchemaUpdate): Promise<Schema | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const updatedSchema = await schemaApi.update(catalogId, schemaName, data);
    // 更新选中的 Schema
    if (selectedSchema.value?.name === schemaName) {
      selectedSchema.value = updatedSchema;
    }
    // 刷新当前 Catalog
    await fetchCatalog(catalogId);
    return updatedSchema;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "更新 Schema 失败";
    console.error("updateSchema error:", e);
    return null;
  } finally {
    loading.creating = false;
  }
}

/**
 * 选择 Schema（从树形导航点击）
 * @param catalogId Catalog ID
 * @param schemaName Schema 名称
 */
async function selectSchemaByName(catalogId: string, schemaName: string): Promise<void> {
  // 准备选择 Schema（清除不兼容的选择状态）
  prepareForSelection('schema');
  
  // 确保 Catalog 已加载
  await ensureCatalogLoaded(catalogId);
  
  // 从已加载的 Catalog 中查找 Schema
  const schema = selectedCatalog.value?.schemas.find(s => s.name === schemaName);
  if (schema) {
    selectedSchema.value = schema;
    // 展开 Schema 节点
    toggleNodeExpanded(schema.id, true);
    // 加载 Asset 列表
    await fetchAssets(catalogId, schemaName);
  }
}

/**
 * 选择 Schema
 */
async function selectSchema(catalogId: string, schema: Schema): Promise<void> {
  // 准备选择 Schema
  prepareForSelection('schema');
  
  selectedSchema.value = schema;
  await fetchAssets(catalogId, schema.name);
}

/**
 * 获取 Asset 列表
 */
async function fetchAssets(catalogId: string, schemaName: string): Promise<Asset[]> {
  loading.assets = true;
  error.value = null;
  
  try {
    const assets = await assetApi.list(catalogId, schemaName);
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
async function createAsset(catalogId: string, schemaName: string, data: AssetCreate): Promise<Asset | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newAsset = await assetApi.create(catalogId, schemaName, data);
    // 刷新树和资产列表
    await Promise.all([
      fetchTree(),
      fetchAssets(catalogId, schemaName),
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
async function deleteAsset(catalogId: string, schemaName: string, assetName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await assetApi.delete(catalogId, schemaName, assetName);
    // 刷新树和资产列表
    await Promise.all([
      fetchTree(),
      fetchAssets(catalogId, schemaName),
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
 * 清除 Schema 选中状态
 */
function clearSelectedSchema(): void {
  selectedSchema.value = null;
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
async function selectAssetByName(catalogId: string, schemaName: string, assetName: string): Promise<void> {
  // 准备选择 Asset
  prepareForSelection('asset');
  
  // 确保 Catalog 已加载
  await ensureCatalogLoaded(catalogId);
  
  // 确保 Schema 已选中
  const schema = selectedCatalog.value?.schemas.find(s => s.name === schemaName);
  if (schema) {
    selectedSchema.value = schema;
    // 总是重新加载 Asset 列表，确保数据是最新的
    await fetchAssets(catalogId, schemaName);
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
async function createAgent(catalogId: string, data: AgentCreate): Promise<Agent | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newAgent = await agentApi.create(catalogId, data);
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
async function deleteAgent(catalogId: string, agentName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await agentApi.delete(catalogId, agentName);
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
async function selectAgent(catalogId: string, agentName: string): Promise<void> {
  // 准备选择 Agent（清除 Schema 分支的选择状态）
  prepareForSelection('agent');
  
  try {
    // 确保 Catalog 已加载
    await ensureCatalogLoaded(catalogId);
    
    const agent = await agentApi.get(catalogId, agentName);
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
  selectedPromptName.value = '';
}

/**
 * 刷新当前选中的 Agent 数据
 * 不改变选中状态，只更新 Agent 数据（如 enabled_prompts 列表）
 */
async function refreshSelectedAgent(): Promise<void> {
  if (!selectedAgent.value || !selectedCatalog.value) return;
  
  try {
    const agent = await agentApi.get(selectedCatalog.value.id, selectedAgent.value.name);
    selectedAgent.value = agent;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "刷新 Agent 数据失败";
    console.error("refreshSelectedAgent error:", e);
  }
}

// ============ Prompt 操作 ============

/**
 * 选择 Prompt
 * @param catalogId Catalog ID
 * @param agentName Agent 名称
 * @param promptName Prompt 名称
 */
async function selectPrompt(catalogId: string, agentName: string, promptName: string): Promise<void> {
  // 准备选择 Prompt
  prepareForSelection('prompt');
  
  // 确保 Agent 已选中（selectAgent 会处理 Catalog 加载和状态清除）
  const needLoadAgent = !selectedAgent.value || 
                        selectedAgent.value.name !== agentName || 
                        selectedCatalog.value?.id !== catalogId;
  
  if (needLoadAgent) {
    await selectAgent(catalogId, agentName);
  }
  
  // 设置选中的 Prompt 名称
  selectedPromptName.value = promptName;
}

/**
 * 清除 Prompt 选中状态
 */
function clearSelectedPrompt(): void {
  selectedPromptName.value = '';
}

// ============ Model 操作（Schema 级别） ============

/**
 * 创建 Model
 */
async function createModel(catalogId: string, schemaName: string, data: ModelCreate): Promise<Model | null> {
  loading.creating = true;
  error.value = null;
  
  try {
    const newModel = await modelApi.create(catalogId, schemaName, data);
    // 刷新树
    await fetchTree();
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
async function deleteModel(catalogId: string, schemaName: string, modelName: string): Promise<boolean> {
  loading.deleting = true;
  error.value = null;
  
  try {
    await modelApi.delete(catalogId, schemaName, modelName);
    // 清除选中状态
    if (selectedModel.value?.name === modelName) {
      selectedModel.value = null;
    }
    // 刷新树
    await fetchTree();
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
 * 选择 Model
 */
async function selectModel(catalogId: string, schemaName: string, modelName: string): Promise<void> {
  // 准备选择 Model
  prepareForSelection('model');
  
  try {
    // 确保 Catalog 已加载
    await ensureCatalogLoaded(catalogId);
    
    // 确保 Schema 已选中
    const schema = selectedCatalog.value?.schemas.find(s => s.name === schemaName);
    if (schema) {
      selectedSchema.value = schema;
    }
    
    const model = await modelApi.get(catalogId, schemaName, modelName);
    selectedModel.value = model;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "获取模型详情失败";
    console.error("selectModel error:", e);
  }
}

/**
 * 清除 Model 选中状态
 */
function clearSelectedModel(): void {
  selectedModel.value = null;
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
  catalogs.value = [];
  catalogTree.value = [];
  catalogItems.value = [];
  expandedNodes.value.clear();
  selectedCatalog.value = null;
  selectedSchema.value = null;
  selectedAgent.value = null;
  selectedModel.value = null;
  currentAssets.value = [];
  error.value = null;
}

// ============ 导出 ============

export function useCatalogStore() {
  return {
    // 状态
    catalogs,
    catalogTree,
    catalogItems,
    expandedNodes,
    selectedCatalog,
    selectedSchema,
    selectedAsset,
    selectedAgent,
    selectedModel,
    selectedPromptName,
    selectedNodeId,  // 统一的选中节点 ID 计算
    currentSchemas,
    currentAssets,
    loading,
    error,
    
    // Actions
    fetchCatalogs,
    fetchTree,
    fetchCatalog,
    createCatalog,
    updateCatalog,
    deleteCatalog,
    selectCatalog,
    toggleNodeExpanded,
    fetchSchemas,
    createSchema,
    updateSchema,
    deleteSchema,
    selectSchema,
    selectSchemaByName,
    clearSelectedSchema,
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
    selectPrompt,
    clearSelectedPrompt,
    createModel,
    deleteModel,
    selectModel,
    clearSelectedModel,
    clearError,
    reset,
  };
}

export default useCatalogStore;
