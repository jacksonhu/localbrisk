<template>
  <div class="prompt-detail-panel h-full flex flex-col p-6">
    <!-- 面包屑导航 -->
    <Breadcrumb
      :items="[
        { label: selectedCatalog?.display_name || selectedCatalog?.name || '', onClick: goToCatalog },
        { label: selectedAgent?.name || '', onClick: goToAgent },
        { label: selectedPrompt?.name || '' }
      ]"
      @back="goBack"
      class="mb-4"
    />

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <FileText class="w-6 h-6 text-blue-500" />
        <h1 class="text-2xl font-semibold">{{ selectedPrompt?.name }}</h1>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="confirmDeletePrompt"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('common.delete')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
      </div>
      
      <!-- 启用开关 -->
      <div class="flex items-center gap-3">
        <span class="text-sm text-muted-foreground">{{ t('prompt.enabled') }}</span>
        <label class="relative inline-flex items-center cursor-pointer" @click.stop>
          <input
            type="checkbox"
            :checked="isEnabled"
            @change.stop="toggleEnabled"
            class="sr-only peer"
          />
          <div class="w-11 h-6 bg-muted rounded-full peer-checked:bg-primary transition-colors"></div>
          <div class="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow peer-checked:translate-x-5 transition-transform"></div>
        </label>
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
    <div class="flex-1 overflow-hidden">
      <!-- 概览 Tab -->
      <div v-if="activeTab === 'overview'" class="space-y-6 overflow-y-auto h-full">
        <!-- Prompt 基本信息 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-4">{{ t('prompt.info') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('common.name') }}</label>
              <p class="font-medium">{{ selectedPrompt?.name }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('prompt.enabled') }}</label>
              <p class="font-medium">
                <span 
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                  :class="isEnabled 
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'"
                >
                  <span 
                    class="w-1.5 h-1.5 rounded-full"
                    :class="isEnabled ? 'bg-green-500' : 'bg-gray-400'"
                  ></span>
                  {{ isEnabled ? '已启用' : '已禁用' }}
                </span>
              </p>
            </div>
            <div v-if="selectedPrompt?.path" class="col-span-2">
              <label class="text-muted-foreground">{{ t('prompt.filePath') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedPrompt.path }}
              </p>
            </div>
            <div v-if="selectedPrompt?.created_at">
              <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedPrompt.created_at) }}</p>
            </div>
            <div v-if="selectedPrompt?.updated_at">
              <label class="text-muted-foreground">{{ t('common.updatedAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedPrompt.updated_at) }}</p>
            </div>
          </div>
        </div>

        <!-- 内容预览 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-3">{{ t('prompt.content') }}</h3>
          <div class="bg-muted/50 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
            {{ selectedPrompt?.content || t('prompt.noContent') }}
          </div>
        </div>
      </div>

      <!-- 内容编辑 Tab -->
      <div v-if="activeTab === 'content'" class="h-full">
        <div class="card-float h-full overflow-hidden">
          <MarkdownEditor
            ref="editorRef"
            :content="promptContent"
            @save="handleSaveContent"
            @error="handleError"
          />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  FileText, Trash2, Info, FileCode
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import Breadcrumb from "@/components/common/Breadcrumb.vue";
import MarkdownEditor from "@/components/viewer/MarkdownEditor.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { agentApi } from "@/services/api";
import { formatDate } from "@/utils/formatUtils";
import type { Prompt } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// Props
const props = defineProps<{
  catalogId: string;
  agentName: string;
  promptName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'deleted'): void;
}>();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedAgent = computed(() => store.selectedAgent.value);

// Prompt 数据
const selectedPrompt = ref<Prompt | null>(null);
const promptContent = ref('');
const isLoading = ref(false);

// 启用状态从 agent 的 instruction.user_prompt_templates 中计算得出
const isEnabled = computed(() => {
  const promptTemplates = selectedAgent.value?.instruction?.user_prompt_templates || [];
  return promptTemplates.some(p => p.name === props.promptName);
});

// Editor 引用
const editorRef = ref<InstanceType<typeof MarkdownEditor> | null>(null);

// Tab 状态
const activeTab = ref<'overview' | 'content'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('prompt.overview'), icon: Info },
  { id: 'content' as const, label: t('prompt.contentTab'), icon: FileCode },
]);

// 弹窗状态
const showDeleteDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 加载 Prompt 详情
async function loadPrompt() {
  if (!props.catalogId || !props.agentName || !props.promptName) return;
  
  isLoading.value = true;
  try {
    const prompt = await agentApi.getPrompt(props.catalogId, props.agentName, props.promptName);
    selectedPrompt.value = prompt;
    promptContent.value = prompt.content || '';
    // 启用状态通过 computed 从 agent.instruction.user_prompt_templates 中获取，无需手动设置
  } catch (e) {
    console.error('Failed to load prompt:', e);
    handleError(t('errors.loadPromptFailed'));
  } finally {
    isLoading.value = false;
  }
}

// 切换启用状态
async function toggleEnabled() {
  if (!selectedPrompt.value) return;
  
  const newEnabled = !isEnabled.value;
  try {
    await agentApi.togglePromptEnabled(props.catalogId, props.agentName, props.promptName, newEnabled);
    // 刷新 Agent 数据以更新 instruction.user_prompt_templates 列表，但不改变选中状态
    // 使用 refreshSelectedAgent 而不是 selectAgent，避免清除 Prompt 选中状态
    await store.refreshSelectedAgent();
  } catch (e) {
    console.error('Failed to toggle enabled:', e);
    handleError(t('errors.updatePromptFailed'));
  }
}

// 保存内容
async function handleSaveContent(content: string) {
  try {
    await agentApi.updatePrompt(props.catalogId, props.agentName, props.promptName, {
      content,
    });
    promptContent.value = content;
    if (selectedPrompt.value) {
      selectedPrompt.value.content = content;
    }
    // 通知编辑器更新原始内容
    editorRef.value?.updateOriginalContent();
  } catch (e) {
    console.error('Failed to save content:', e);
    handleError(t('errors.updatePromptFailed'));
  }
}

// 错误处理
function handleError(message: string) {
  console.error(message);
  // TODO: 显示错误提示
}

// 返回到 Agent 详情
function goBack() {
  emit('back');
}

// 返回到 Catalog
function goToCatalog() {
  store.clearSelectedAgent();
  store.selectedCatalog.value = null;
}

// 返回到 Agent 详情
function goToAgent() {
  emit('back');
}

// 确认删除 Prompt
function confirmDeletePrompt() {
  if (!selectedPrompt.value) return;
  deleteMessage.value = t('prompt.confirmDelete', { name: selectedPrompt.value.name });
  deleteDescription.value = t('prompt.confirmDeleteDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedPrompt.value) return;
  
  try {
    await agentApi.deletePrompt(props.catalogId, props.agentName, props.promptName);
    showDeleteDialog.value = false;
    emit('deleted');
  } catch (e) {
    console.error('Failed to delete prompt:', e);
    handleError(t('errors.deletePromptFailed'));
  }
}

// 监听 props 变化，重新加载
// 使用 immediate: true 会在组件初始化时立即执行一次
watch([() => props.catalogId, () => props.agentName, () => props.promptName], () => {
  loadPrompt();
}, { immediate: true });

// 注意：不需要在 onMounted 中再次调用 loadPrompt()
// 因为 watch 的 immediate: true 已经会在组件挂载时执行
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
