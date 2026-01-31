<template>
  <div class="agent-detail-panel h-full flex flex-col">
    <!-- 当查看 Prompt 详情时显示 PromptDetailPanel -->
    <PromptDetailPanel
      v-if="selectedPromptName"
      :catalog-id="selectedCatalog?.id || ''"
      :agent-name="selectedAgent?.name || ''"
      :prompt-name="selectedPromptName"
      @back="store.clearSelectedPrompt()"
      @deleted="handlePromptDeleted"
    />
    
    <!-- 当查看 Skill 详情时显示 SkillDetailPanel -->
    <SkillDetailPanel
      v-else-if="selectedSkillName"
      :catalog-id="selectedCatalog?.id || ''"
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
          { label: selectedCatalog?.display_name || selectedCatalog?.name || '', onClick: goToCatalog },
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
                @click="handleCreatePrompt"
                class="w-full px-4 py-3 text-left text-sm hover:bg-muted transition-colors flex items-center gap-3"
              >
                <FileText class="w-4 h-4 text-blue-500" />
                {{ t('agent.createPrompt') }}
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
        <div v-if="activeTab === 'overview'" class="space-y-6">
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
                <label class="text-muted-foreground">{{ t('catalog.modelReference') }}</label>
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
              <h3 class="font-medium">{{ t('catalog.systemPrompt') }}</h3>
            </div>
            <div class="bg-muted/50 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {{ selectedAgent.system_prompt }}
            </div>
          </div>

          <!-- Skills 列表 -->
          <ItemListCard
            title="Skills"
            :icon="Code"
            :item-icon="FileCode"
            item-icon-color="text-purple-500"
            :items="selectedAgent?.skills || []"
            :items-label="t('agent.items')"
            :empty-text="t('agent.noSkills')"
            :show-toggle="true"
            :is-enabled="isSkillEnabled"
            @item-click="openSkillDetail"
            @toggle="handleSkillToggle"
          />

          <!-- Prompts 列表 -->
          <ItemListCard
            title="Prompts"
            :icon="FileText"
            :item-icon="FileText"
            item-icon-color="text-blue-500"
            :items="selectedAgent?.prompts || []"
            :items-label="t('agent.items')"
            :empty-text="t('agent.noPrompts')"
            :show-toggle="true"
            :is-enabled="isPromptEnabled"
            @item-click="openPromptDetail"
            @toggle="handlePromptToggle"
          />
        </div>

        <!-- 配置 Tab -->
        <div v-if="activeTab === 'config'" class="h-full">
          <div class="card-float h-full flex flex-col">
            <div class="p-4 border-b border-border flex items-center justify-between">
              <h3 class="font-medium flex items-center gap-2">
                <FileCode class="w-4 h-4" />
                {{ t('detail.configFile') }} (agent_spec.yaml)
              </h3>
              <div class="flex items-center gap-2">
                <button
                  @click="saveConfig"
                  :disabled="!configModified || savingConfig"
                  class="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Save class="w-4 h-4" />
                  {{ t('common.save') }}
                </button>
                <button
                  @click="copyConfig"
                  class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2"
                >
                  <Copy class="w-4 h-4" />
                  {{ t('common.copy') }}
                </button>
              </div>
            </div>
            <div class="flex-1 p-4 overflow-hidden">
              <textarea
                v-model="configContent"
                class="w-full h-full font-mono text-sm bg-muted/50 border border-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                spellcheck="false"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Chat Tab (预留) -->
        <div v-if="activeTab === 'chat'" class="h-full">
          <div class="card-float h-full flex flex-col items-center justify-center">
            <MessageSquare class="w-16 h-16 text-muted-foreground/30 mb-4" />
            <h3 class="text-lg font-medium mb-2">{{ t('agent.chatTitle') }}</h3>
            <p class="text-muted-foreground text-sm text-center max-w-md">
              {{ t('agent.chatPlaceholder') }}
            </p>
          </div>
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
      
      <!-- 创建 Prompt 弹窗 -->
      <CreatePromptDialog
        :is-open="showCreatePromptDialog"
        :catalog-id="selectedCatalog?.id || ''"
        :agent-name="selectedAgent?.name || ''"
        @close="showCreatePromptDialog = false"
        @submit="handleSubmitPrompt"
      />

      <!-- 创建 Skill 弹窗 -->
      <CreateSkillDialog
        :is-open="showCreateSkillDialog"
        :catalog-id="selectedCatalog?.id || ''"
        :agent-name="selectedAgent?.name || ''"
        :on-submit="handleSubmitSkill"
        @close="showCreateSkillDialog = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, ChevronDown, Bot, Trash2, Plus,
  FileText, FileCode, Save, Copy, Code, MessageSquare
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import Breadcrumb from "@/components/common/Breadcrumb.vue";
import CreatePromptDialog from "@/components/catalog/CreatePromptDialog.vue";
import CreateSkillDialog from "@/components/catalog/CreateSkillDialog.vue";
import PromptDetailPanel from "@/components/detail/PromptDetailPanel.vue";
import SkillDetailPanel from "@/components/detail/SkillDetailPanel.vue";
import ItemListCard from "@/components/common/ItemListCard.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { agentApi } from "@/services/api";
import { formatDate } from "@/utils/formatUtils";
import type { PromptCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedAgent = computed(() => store.selectedAgent.value);
const selectedPromptName = computed({
  get: () => store.selectedPromptName.value,
  set: (val) => { store.selectedPromptName.value = val; }
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

// 配置内容
const configContent = ref('');
const originalConfig = ref('');
const savingConfig = ref(false);

const configModified = computed(() => configContent.value !== originalConfig.value);

// 弹窗状态
const showDeleteDialog = ref(false);
const showCreatePromptDialog = ref(false);
const showCreateSkillDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 创建下拉菜单状态
const showCreateDropdown = ref(false);
const createDropdownRef = ref<HTMLElement | null>(null);

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
async function handleSubmitSkill(catalogId: string, agentName: string, zipFilePath: string) {
  // 调用 API 导入 Skill，如果失败会抛出异常由 CreateSkillDialog 捕获并显示
  await agentApi.importSkillFromZip(catalogId, agentName, zipFilePath);
  
  // 导入成功后，刷新 Agent 详情以更新 skills 列表
  if (selectedCatalog.value && selectedAgent.value) {
    await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// 创建 Prompt
function handleCreatePrompt() {
  showCreateDropdown.value = false;
  showCreatePromptDialog.value = true;
}

// 提交创建 Prompt
async function handleSubmitPrompt(catalogId: string, agentName: string, data: PromptCreate) {
  try {
    await agentApi.createPrompt(catalogId, agentName, data);
    showCreatePromptDialog.value = false;
    // 刷新 Agent 详情以更新 prompts 列表
    if (selectedCatalog.value && selectedAgent.value) {
      await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
    }
  } catch (e) {
    console.error('Failed to create prompt:', e);
  }
}

// 打开 Prompt 详情
function openPromptDetail(promptName: string | Record<string, unknown>) {
  const name = typeof promptName === 'string' ? promptName : String(promptName.name || '');
  store.selectedPromptName.value = name;
}

// 打开 Skill 详情
function openSkillDetail(skillName: string | Record<string, unknown>) {
  const name = typeof skillName === 'string' ? skillName : String(skillName.name || '');
  store.selectedSkillName.value = name;
}

// 检查 Skill 是否启用（从 capabilities.native_skills）
function isSkillEnabled(item: string | Record<string, unknown>): boolean {
  const skillName = typeof item === 'string' ? item : String(item.name || '');
  const nativeSkills = selectedAgent.value?.capabilities?.native_skills || [];
  return nativeSkills.some(s => s.name === skillName);
}

// 检查 Prompt 是否启用（从 instruction.user_prompt_templates）
function isPromptEnabled(item: string | Record<string, unknown>): boolean {
  const promptName = typeof item === 'string' ? item : String(item.name || '');
  const promptTemplates = selectedAgent.value?.instruction?.user_prompt_templates || [];
  return promptTemplates.some(p => p.name === promptName);
}

// 处理 Skill 开关切换
async function handleSkillToggle(item: string | Record<string, unknown>, enabled: boolean) {
  if (!selectedCatalog.value || !selectedAgent.value) return;
  
  const skillName = typeof item === 'string' ? item : String(item.name || '');
  try {
    await agentApi.toggleSkillEnabled(
      selectedCatalog.value.id,
      selectedAgent.value.name,
      skillName,
      enabled
    );
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
  } catch (e) {
    console.error('Failed to toggle skill enabled:', e);
  }
}

// 处理 Prompt 开关切换
async function handlePromptToggle(item: string | Record<string, unknown>, enabled: boolean) {
  if (!selectedCatalog.value || !selectedAgent.value) return;
  
  const promptName = typeof item === 'string' ? item : String(item.name || '');
  try {
    await agentApi.togglePromptEnabled(
      selectedCatalog.value.id,
      selectedAgent.value.name,
      promptName,
      enabled
    );
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
  } catch (e) {
    console.error('Failed to toggle prompt enabled:', e);
  }
}

// Prompt 被删除后的处理
async function handlePromptDeleted() {
  store.clearSelectedPrompt();
  // 刷新 Agent 详情以更新 prompts 列表
  if (selectedCatalog.value && selectedAgent.value) {
    await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// Skill 被删除后的处理
async function handleSkillDeleted() {
  store.clearSelectedSkill();
  // 刷新 Agent 详情以更新 skills 列表
  if (selectedCatalog.value && selectedAgent.value) {
    await store.selectAgent(selectedCatalog.value.id, selectedAgent.value.name);
  }
  // 刷新目录树
  await store.fetchTree();
}

// 加载配置 - 从后端获取 agent_spec.yaml 文件原始内容
async function loadConfig() {
  if (!selectedCatalog.value || !selectedAgent.value) {
    configContent.value = '';
    originalConfig.value = '';
    return;
  }
  
  try {
    const response = await agentApi.getConfig(selectedCatalog.value.id, selectedAgent.value.name);
    configContent.value = response.content;
    originalConfig.value = response.content;
  } catch (e) {
    console.error('Failed to load agent config:', e);
    configContent.value = '';
    originalConfig.value = '';
  }
}

// 保存配置
async function saveConfig() {
  savingConfig.value = true;
  try {
    // TODO: 调用后端 API 保存配置
    console.log('Save agent config:', configContent.value);
    originalConfig.value = configContent.value;
  } finally {
    savingConfig.value = false;
  }
}

// 复制配置
async function copyConfig() {
  try {
    await navigator.clipboard.writeText(configContent.value);
    // TODO: 显示复制成功提示
  } catch (e) {
    console.error('Failed to copy:', e);
  }
}

// 返回到 Catalog 列表
function goBack() {
  store.clearSelectedAgent();
  store.selectedCatalog.value = null;
}

// 返回到 Catalog 详情
function goToCatalog() {
  store.clearSelectedAgent();
}

// 确认删除 Agent
function confirmDeleteAgent() {
  if (!selectedAgent.value) return;
  deleteMessage.value = t('catalog.confirmDeleteAgent', { name: selectedAgent.value.name });
  deleteDescription.value = t('catalog.confirmDeleteAgentDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedCatalog.value || !selectedAgent.value) return;
  
  const success = await store.deleteAgent(selectedCatalog.value.id, selectedAgent.value.name);
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedAgent();
  }
}

// 记录上一个 Agent 名称，用于判断是否切换了 Agent
const previousAgentName = ref<string | null>(null);

// 监听 Agent 变化，重新加载配置
watch(selectedAgent, (newAgent, oldAgent) => {
  // 只有切换到不同的 Agent 时才清除 Prompt 选中状态
  const newName = newAgent?.name || null;
  const oldName = oldAgent?.name || previousAgentName.value;
  
  if (newName !== oldName) {
    activeTab.value = 'overview';
    store.clearSelectedPrompt();
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
