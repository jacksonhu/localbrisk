<template>
  <div class="agent-detail-panel h-full flex flex-col">
    <!-- 当查看 Memory 详情时显示 MemoryDetailPanel -->
    <MemoryDetailPanel
      v-if="selectedMemoryName"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      :agent-name="selectedAgent?.name || ''"
      :memory-name="selectedMemoryName"
      @back="store.clearSelectedMemory()"
      @deleted="handleMemoryDeleted"
    />
    
    <!-- 当查看 Skill 详情时显示 SkillDetailPanel -->
    <SkillDetailPanel
      v-else-if="selectedSkillName"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      :agent-name="selectedAgent?.name || ''"
      :skill-name="selectedSkillName"
      @back="store.clearSelectedSkill()"
      @deleted="handleSkillDeleted"
    />
    
    <!-- Agent 详情主面板 -->
    <div v-else class="h-full flex flex-col p-6">
      <!-- 面包屑导航 -->
      <Breadcrumb
        :items="[
          { label: selectedBusinessUnit?.display_name || selectedBusinessUnit?.name || '', onClick: goToBusinessUnit },
          { label: selectedAgent?.name || '' }
        ]"
        @back="goBack"
        class="mb-4"
      />

      <!-- 标题区域 -->
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <Bot class="w-6 h-6 text-orange-500" />
          <h1 class="text-2xl font-semibold">{{ selectedAgent?.name }}</h1>
          <!-- 操作图标 -->
          <div class="flex items-center gap-1 ml-2">
            <button
              @click="confirmDeleteAgent"
              class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              :title="t('common.delete')"
            >
              <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
            </button>
          </div>
        </div>
        
        <!-- 创建下拉按钮 -->
        <div class="relative" ref="createDropdownRef">
          <button
            @click="showCreateDropdown = !showCreateDropdown"
            class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <Plus class="w-4 h-4" />
            {{ t('agent.create') }}
            <ChevronDown class="w-4 h-4" />
          </button>
          
          <!-- 下拉菜单 -->
          <Transition name="dropdown">
            <div
              v-if="showCreateDropdown"
              class="absolute right-0 top-full mt-2 w-48 bg-card border border-border rounded-lg shadow-float-lg overflow-hidden z-50"
            >
              <button
                @click="handleCreateSkill"
                class="w-full px-4 py-3 text-left text-sm hover:bg-muted transition-colors flex items-center gap-3"
              >
                <Code class="w-4 h-4 text-purple-500" />
                {{ t('agent.createSkill') }}
              </button>
              <button
                @click="handleCreateMemory"
                class="w-full px-4 py-3 text-left text-sm hover:bg-muted transition-colors flex items-center gap-3"
              >
                <FileText class="w-4 h-4 text-blue-500" />
                {{ t('agent.createMemory') }}
              </button>
              <button
                @click="handleCreateModel"
                class="w-full px-4 py-3 text-left text-sm hover:bg-muted transition-colors flex items-center gap-3"
              >
                <Cpu class="w-4 h-4 text-orange-500" />
                {{ t('model.createModel') }}
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="flex items-center gap-1 border-b border-border mb-6">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2 text-sm font-medium transition-colors relative"
          :class="activeTab === tab.id 
            ? 'text-primary' 
            : 'text-muted-foreground hover:text-foreground'"
        >
          <div class="flex items-center gap-2">
            <component :is="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </div>
          <!-- 激活指示器 -->
          <div
            v-if="activeTab === tab.id"
            class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
          ></div>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="flex-1 overflow-y-auto">
        <!-- 概览 Tab -->
        <div v-show="activeTab === 'overview'" class="space-y-6">
          <!-- 描述卡片 -->
          <div class="card-float p-4">
            <div class="flex items-center justify-between mb-2">
              <h3 class="font-medium">{{ t('common.description') }}</h3>
            </div>
            <p class="text-muted-foreground text-sm">
              {{ selectedAgent?.description || t('detail.noDescription') }}
            </p>
          </div>

          <!-- Agent 基本信息 -->
          <div class="card-float p-4">
            <h3 class="font-medium mb-4">{{ t('agent.info') }}</h3>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label class="text-muted-foreground">{{ t('common.name') }}</label>
                <p class="font-medium">{{ selectedAgent?.name }}</p>
              </div>
              <div>
                <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
                <p class="font-medium">{{ formatDate(selectedAgent?.created_at) }}</p>
              </div>
              <div v-if="selectedAgent?.model_reference">
                <label class="text-muted-foreground">{{ t('businessUnit.modelReference') }}</label>
                <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1">
                  {{ selectedAgent.model_reference }}
                </p>
              </div>
              <div v-if="selectedAgent?.path" class="col-span-2">
                <label class="text-muted-foreground">{{ t('common.path') }}</label>
                <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                  {{ selectedAgent.path }}
                </p>
              </div>
            </div>
          </div>

          <!-- 系统提示词 -->
          <div v-if="selectedAgent?.system_prompt" class="card-float p-4">
            <div class="flex items-center justify-between mb-3">
              <h3 class="font-medium">{{ t('businessUnit.systemPrompt') }}</h3>
            </div>
            <div class="bg-muted/50 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {{ selectedAgent.system_prompt }}
            </div>
          </div>

          <!-- Skills 列表 -->
          <ItemListCard
            title="Skills"
            :title-icon="Code"
            :items="selectedAgent?.skills || []"
            :columns="skillColumns"
            key-field="name"
            show-count
            :count-label="t('agent.items')"
            :empty-text="t('agent.noSkills')"
            row-clickable
            @row-click="handleSkillRowClick"
            @toggle="handleSkillToggleEvent"
          />

          <!-- Memories 列表 -->
          <ItemListCard
            title="Memories"
            :title-icon="FileText"
            :items="selectedAgent?.memories || []"
            :columns="memoryColumns"
            key-field="name"
            show-count
            :count-label="t('agent.items')"
            :empty-text="t('agent.noMemories')"
            row-clickable
            @row-click="handleMemoryRowClick"
            @toggle="handleMemoryToggleEvent"
          />

          <!-- Models 列表 -->
          <ItemListCard
            title="Models"
            :title-icon="Cpu"
            :items="selectedAgent?.models || []"
            :columns="modelColumns"
            key-field="name"
            show-count
            :count-label="t('agent.items')"
            :empty-text="t('agent.noModels')"
            row-clickable
            @row-click="handleModelRowClick"
            @toggle="handleModelToggleEvent"
          />
        </div>

        <!-- 配置 Tab -->
        <div v-show="activeTab === 'config'" class="h-full">
          <ConfigEditor
            v-model="configContent"
            :title="`${t('detail.configFile')} (agent_spec.yaml)`"
            :modified="configModified"
            :saving="savingConfig"
            @save="saveConfig"
            @copy="copyConfig"
          />
        </div>

        <!-- Chat Tab -->
        <div v-show="activeTab === 'chat'" class="h-full">
          <AgentWorkspace
            v-if="selectedBusinessUnit && selectedAgent"
            :business-unit-id="selectedBusinessUnit.id"
            :agent-name="selectedAgent.name"
          />
        </div>
      </div>

      <!-- 确认删除弹窗 -->
      <ConfirmDialog
        :is-open="showDeleteDialog"
        :message="deleteMessage"
        :description="deleteDescription"
        @close="showDeleteDialog = false"
        @confirm="handleConfirmDelete"
      />
      
      <!-- 创建 Memory 弹窗 -->
      <CreateMemoryDialog
        :is-open="showCreateMemoryDialog"
        :business-unit-id="selectedBusinessUnit?.id || ''"
        :agent-name="selectedAgent?.name || ''"
        @close="showCreateMemoryDialog = false"
        @submit="handleSubmitMemory"
      />

      <!-- 创建 Skill 弹窗 -->
      <CreateSkillDialog
        :is-open="showCreateSkillDialog"
        :business-unit-id="selectedBusinessUnit?.id || ''"
        :agent-name="selectedAgent?.name || ''"
        :on-submit="handleSubmitSkill"
        @close="showCreateSkillDialog = false"
      />

      <!-- 创建 Model 弹窗 -->
      <CreateModelDialog
        :is-open="showCreateModelDialog"
        :business-unit-id="selectedBusinessUnit?.id || ''"
        :agent-name="selectedAgent?.name || ''"
        @close="showCreateModelDialog = false"
        @submit="handleSubmitModel"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, ChevronDown, Bot, Trash2, Plus,
  FileText, FileCode, Code, MessageSquare, Cpu
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import Breadcrumb from "@/components/common/Breadcrumb.vue";
import CreateMemoryDialog from "@/components/catalog/CreateMemoryDialog.vue";
import CreateSkillDialog from "@/components/catalog/CreateSkillDialog.vue";
import CreateModelDialog from "@/components/catalog/CreateModelDialog.vue";
import MemoryDetailPanel from "@/components/detail/MemoryDetailPanel.vue";
import SkillDetailPanel from "@/components/detail/SkillDetailPanel.vue";
import AgentWorkspace from "@/components/detail/AgentWorkspace.vue";
import ItemListCard from "@/components/common/ItemListCard.vue";
import ConfigEditor from "@/components/common/ConfigEditor.vue";
import type { ColumnConfig } from "@/components/common/ItemListCard.vue";
import { useBusinessUnitStore } from "@/stores/businessUnitStore";
import { useConfigManager } from "@/composables/useConfigManager";
import { agentApi, modelApi } from "@/services/api";
import { formatDate } from "@/utils/formatUtils";
import type { MemoryCreate, ModelCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useBusinessUnitStore();

// 使用 computed 保持响应式
const selectedBusinessUnit = computed(() => store.selectedBusinessUnit.value);
const selectedAgent = computed(() => store.selectedAgent.value);
const selectedMemoryName = computed({
  get: () => store.selectedMemoryName.value,
  set: (val) => { store.selectedMemoryName.value = val; }
});
const selectedSkillName = computed({
  get: () => store.selectedSkillName.value,
  set: (val) => { store.selectedSkillName.value = val; }
});

// Tab 状态
const activeTab = ref<'overview' | 'config' | 'chat'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
  { id: 'chat' as const, label: 'Chat', icon: MessageSquare },
]);

// 使用配置管理器处理 Agent 配置
const agentConfigManager = useConfigManager({
  type: 'agent',
  getConfigPath: () => {
    if (!selectedAgent.value?.path) return undefined;
    return `${selectedAgent.value.path}/agent_spec.yaml`;
  },
  loadConfig: async () => {
    if (!selectedBusinessUnit.value || !selectedAgent.value) return '';
    try {
      const response = await agentApi.getConfig(selectedBusinessUnit.value.id, selectedAgent.value.name);
      return response.content;
    } catch (e) {
      console.error('Failed to load agent config:', e);
      return '';
    }
  },
  onSaved: async () => {
    // 刷新 agent 数据
    if (selectedBusinessUnit.value && selectedAgent.value) {
      await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
    }
  },
});

// 解构配置管理器的状态和方法
const {
  configContent,
  configModified,
  savingConfig,
  saveConfig,
  copyConfig,
  loadConfigContent: loadConfig,
} = agentConfigManager;

// 弹窗状态
const showDeleteDialog = ref(false);
const showCreateMemoryDialog = ref(false);
const showCreateSkillDialog = ref(false);
const showCreateModelDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 创建下拉菜单状态
const showCreateDropdown = ref(false);
const createDropdownRef = ref<HTMLElement | null>(null);

// ItemListCard 列配置类型
type ItemType = string | number | Record<string, unknown>;

// Skills 列配置
const skillColumns: ColumnConfig[] = [
  { key: 'icon', type: 'icon', icon: FileCode, class: 'text-purple-500' },
  { key: 'name', type: 'text', field: 'name', flex: true, class: 'font-medium' },
  { key: 'enabled', type: 'toggle', isEnabled: isSkillEnabled },
];

// Prompts 列配置
const memoryColumns: ColumnConfig[] = [
  { key: 'icon', type: 'icon', icon: FileText, class: 'text-blue-500' },
  { key: 'name', type: 'text', field: 'name', flex: true, class: 'font-medium' },
  { key: 'enabled', type: 'toggle', isEnabled: isMemoryEnabled },
];

// Models 列配置
const modelColumns: ColumnConfig[] = [
  { key: 'icon', type: 'icon', icon: Cpu, class: 'text-orange-500' },
  { key: 'name', type: 'text', field: 'name', flex: true, class: 'font-medium' },
  { key: 'enabled', type: 'toggle', isEnabled: isModelEnabled },
];

// 点击外部关闭下拉菜单
function handleClickOutside(event: MouseEvent) {
  if (createDropdownRef.value && !createDropdownRef.value.contains(event.target as Node)) {
    showCreateDropdown.value = false;
  }
}

// 创建 Skill
function handleCreateSkill() {
  showCreateDropdown.value = false;
  showCreateSkillDialog.value = true;
}

// 提交创建 Skill（从本地 zip 路径导入）
async function handleSubmitSkill(businessUnitId: string, agentName: string, zipFilePath: string) {
  // 调用 API 导入 Skill，如果失败会抛出异常由 CreateSkillDialog 捕获并显示
  await agentApi.importSkillFromZip(businessUnitId, agentName, zipFilePath);
  
  // 导入成功后，刷新 Agent 详情以更新 skills 列表
  if (selectedBusinessUnit.value && selectedAgent.value) {
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// 创建 Memory
function handleCreateMemory() {
  showCreateDropdown.value = false;
  showCreateMemoryDialog.value = true;
}

// 创建 Model
function handleCreateModel() {
  showCreateDropdown.value = false;
  showCreateModelDialog.value = true;
}

// 提交创建 Model
async function handleSubmitModel(businessUnitId: string, agentName: string, data: ModelCreate) {
  try {
    await store.createModel(businessUnitId, agentName, data);
    showCreateModelDialog.value = false;
    // 刷新 Agent 详情以更新 models 列表
    if (selectedBusinessUnit.value && selectedAgent.value) {
      await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
    }
  } catch (e) {
    console.error('Failed to create model:', e);
  }
}

// 提交创建 Memory
async function handleSubmitMemory(businessUnitId: string, agentName: string, data: MemoryCreate) {
  try {
    await agentApi.createMemory(businessUnitId, agentName, data);
    showCreateMemoryDialog.value = false;
    // 刷新 Agent 详情以更新 prompts 列表
    if (selectedBusinessUnit.value && selectedAgent.value) {
      await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
    }
  } catch (e) {
    console.error('Failed to create prompt:', e);
  }
}

// 打开 Memory 详情
function openMemoryDetail(memoryName: string | Record<string, unknown>) {
  const name = typeof memoryName === 'string' ? memoryName : String(memoryName.name || '');
  store.selectedMemoryName.value = name;
}

// 打开 Skill 详情
function openSkillDetail(skillName: string | Record<string, unknown>) {
  const name = typeof skillName === 'string' ? skillName : String(skillName.name || '');
  store.selectedSkillName.value = name;
}

// 处理 Skill 行点击
function handleSkillRowClick(payload: { item: ItemType; index: number }) {
  openSkillDetail(payload.item as string | Record<string, unknown>);
}

// 处理 Memory 行点击
function handleMemoryRowClick(payload: { item: ItemType; index: number }) {
  openMemoryDetail(payload.item as string | Record<string, unknown>);
}

// 检查 Skill 是否启用（从 capabilities.native_skills）
function isSkillEnabled(item: ItemType): boolean {
  const skillName = typeof item === 'string' ? item : String((item as Record<string, unknown>).name || '');
  const nativeSkills = selectedAgent.value?.capabilities?.native_skills || [];
  return nativeSkills.some(s => s.name === skillName);
}

// 检查 Memory 是否启用（从 instruction.user_prompt_templates）
function isMemoryEnabled(item: ItemType): boolean {
  const memoryName = typeof item === 'string' ? item : String((item as Record<string, unknown>).name || '');
  const memoryTemplates = selectedAgent.value?.instruction?.user_prompt_templates || [];
  return memoryTemplates.some(p => p.name === memoryName);
}

// 检查 Model 是否启用（从 active_model 或 llm_config.llm_model）
function isModelEnabled(item: ItemType): boolean {
  const modelName = typeof item === 'string' ? item : String((item as Record<string, unknown>).name || '');
  // 检查 active_model 字段
  if (selectedAgent.value?.active_model === modelName) {
    return true;
  }
  // 也检查 llm_config.llm_model 是否包含该模型名称
  const llmModel = selectedAgent.value?.llm_config?.llm_model || '';
  return llmModel.includes(modelName);
}

// 处理 Skill 开关切换事件
async function handleSkillToggleEvent(payload: { column: ColumnConfig; item: ItemType; index: number; enabled: boolean }) {
  if (!selectedBusinessUnit.value || !selectedAgent.value) return;
  
  const skillName = typeof payload.item === 'string' ? payload.item : String((payload.item as Record<string, unknown>).name || '');
  try {
    await agentApi.toggleSkillEnabled(
      selectedBusinessUnit.value.id,
      selectedAgent.value.name,
      skillName,
      payload.enabled
    );
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  } catch (e) {
    console.error('Failed to toggle skill enabled:', e);
  }
}

// 处理 Memory 开关切换事件
async function handleMemoryToggleEvent(payload: { column: ColumnConfig; item: ItemType; index: number; enabled: boolean }) {
  if (!selectedBusinessUnit.value || !selectedAgent.value) return;
  
  const memoryName = typeof payload.item === 'string' ? payload.item : String((payload.item as Record<string, unknown>).name || '');
  try {
    await agentApi.toggleMemoryEnabled(
      selectedBusinessUnit.value.id,
      selectedAgent.value.name,
      memoryName,
      payload.enabled
    );
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  } catch (e) {
    console.error('Failed to toggle prompt enabled:', e);
  }
}

// 处理 Model 行点击
function handleModelRowClick(payload: { item: ItemType; index: number }) {
  const modelName = typeof payload.item === 'string' ? payload.item : String((payload.item as Record<string, unknown>).name || '');
  if (selectedBusinessUnit.value && selectedAgent.value) {
    store.selectModel(selectedBusinessUnit.value.id, selectedAgent.value.name, modelName);
  }
}

// 处理 Model 开关切换事件（一个 Agent 只能启用一个 Model）
async function handleModelToggleEvent(payload: { column: ColumnConfig; item: ItemType; index: number; enabled: boolean }) {
  if (!selectedBusinessUnit.value || !selectedAgent.value) return;
  
  const modelName = typeof payload.item === 'string' ? payload.item : String((payload.item as Record<string, unknown>).name || '');
  
  // 如果是要禁用，不做任何操作（一个 Agent 必须有一个启用的 Model，或者都禁用）
  // 如果是要启用，则调用 enable API（后端会自动禁用其他 Model）
  if (!payload.enabled) {
    // 禁用当前模型（清除 active_model）
    try {
      await modelApi.update(
        selectedBusinessUnit.value.id,
        selectedAgent.value.name,
        modelName,
        { enabled: false }
      );
      // 刷新 Agent 详情以更新状态
      await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
    } catch (e) {
      console.error('Failed to disable model:', e);
    }
    return;
  }
  
  try {
    // 启用指定 Model（后端会自动禁用其他 Model）
    await modelApi.enable(
      selectedBusinessUnit.value.id,
      selectedAgent.value.name,
      modelName
    );
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  } catch (e) {
    console.error('Failed to enable model:', e);
  }
}

// Memory 被删除后的处理
async function handleMemoryDeleted() {
  store.clearSelectedMemory();
  // 刷新 Agent 详情以更新 prompts 列表
  if (selectedBusinessUnit.value && selectedAgent.value) {
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// Skill 被删除后的处理
async function handleSkillDeleted() {
  store.clearSelectedSkill();
  // 刷新 Agent 详情以更新 skills 列表
  if (selectedBusinessUnit.value && selectedAgent.value) {
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// 返回到 Business Unit 列表
function goBack() {
  store.clearSelectedAgent();
  store.selectedBusinessUnit.value = null;
}

// 返回到 Business Unit 详情
function goToBusinessUnit() {
  store.clearSelectedAgent();
}

// 确认删除 Agent
function confirmDeleteAgent() {
  if (!selectedAgent.value) return;
  deleteMessage.value = t('businessUnit.confirmDeleteAgent', { name: selectedAgent.value.name });
  deleteDescription.value = t('businessUnit.confirmDeleteAgentDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedBusinessUnit.value || !selectedAgent.value) return;
  
  const success = await store.deleteAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedAgent();
  }
}

// 记录上一个 Agent 名称，用于判断是否切换了 Agent
const previousAgentName = ref<string | null>(null);

// 监听 Agent 变化，重新加载配置
watch(selectedAgent, (newAgent, oldAgent) => {
  // 只有切换到不同的 Agent 时才清除 Memory 选中状态
  const newName = newAgent?.name || null;
  const oldName = oldAgent?.name || previousAgentName.value;
  
  if (newName !== oldName) {
    activeTab.value = 'overview';
    store.clearSelectedMemory();
  }
  
  previousAgentName.value = newName;
  loadConfig();
}, { immediate: true });

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
