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
      children = convertTreeToItems(node.children, node.node_type);
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
  catalogItems.value = convertTreeToItems(catalogTree.value);
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
  // 更新树形数据
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
 */
async function selectCatalog(catalogId: string): Promise<void> {
  // 先展开该节点
  toggleNodeExpanded(catalogId, true);
  // 获取详情
  await fetchCatalog(catalogId);
  selectedSchema.value = null;
  currentAssets.value = [];
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
  // 清除 Asset 选中状态（重要：必须在显示 Schema 详情前清除）
  selectedAsset.value = null;
  
  // 先确保 Catalog 已加载
  if (!selectedCatalog.value || selectedCatalog.value.id !== catalogId) {
    await fetchCatalog(catalogId);
  }
  
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
  // 清除 Asset 选中状态
  selectedAsset.value = null;
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
  selectedAsset.value = asset;
}

/**
 * 通过名称选择 Asset（从树形导航点击）
 */
async function selectAssetByName(catalogId: string, schemaName: string, assetName: string): Promise<void> {
  // 先确保 Catalog 已加载
  if (!selectedCatalog.value || selectedCatalog.value.id !== catalogId) {
    await fetchCatalog(catalogId);
  }
  
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
  try {
    const agent = await agentApi.get(catalogId, agentName);
    selectedAgent.value = agent;
    // 清除其他选中状态
    selectedSchema.value = null;
    selectedAsset.value = null;
    currentAssets.value = [];
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
  try {
    const model = await modelApi.get(catalogId, schemaName, modelName);
    selectedModel.value = model;
    // 清除其他选中状态（保留 schema 选中状态）
    selectedAsset.value = null;
    selectedAgent.value = null;
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
    clearSelectedAgent,
    createModel,
    deleteModel,
    selectModel,
    clearSelectedModel,
    clearError,
    reset,
  };
}

export default useCatalogStore;
