<template>
  <div class="skill-detail-panel h-full flex flex-col p-6">
    <!-- 面包屑导航 -->
    <Breadcrumb
      :items="[
        { label: selectedCatalog?.display_name || selectedCatalog?.name || '', onClick: goToCatalog },
        { label: selectedAgent?.name || '', onClick: goToAgent },
        { label: skillName || '' }
      ]"
      @back="goBack"
      class="mb-4"
    />

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <Code class="w-6 h-6 text-cyan-500" />
        <h1 class="text-2xl font-semibold">{{ skillName }}</h1>
        <!-- 类型标识 -->
        <span class="px-2 py-0.5 text-xs bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400 rounded">
          Skill
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="confirmDeleteSkill"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('common.delete')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
      </div>
      
      <!-- 启用开关 -->
      <div class="flex items-center gap-3">
        <span class="text-sm text-muted-foreground">{{ t('skill.enabled') }}</span>
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
      <div v-if="activeTab === 'overview'" class="h-full overflow-y-auto space-y-6">
          <!-- Skill 基本信息 -->
          <div class="card-float p-4">
            <h3 class="font-medium mb-4">{{ t('skill.info') }}</h3>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label class="text-muted-foreground">{{ t('common.name') }}</label>
                <p class="font-medium">{{ skillName }}</p>
              </div>
              <div>
                <label class="text-muted-foreground">{{ t('skill.enabled') }}</label>
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
                    {{ isEnabled ? t('common.enabled') : t('common.disabled') }}
                  </span>
                </p>
              </div>
              <div class="col-span-2">
                <label class="text-muted-foreground">{{ t('skill.path') }}</label>
                <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                  {{ skillPath }}
                </p>
              </div>
            </div>
          </div>

          <!-- 文件列表 -->
          <div class="card-float overflow-hidden">
            <div class="p-4 border-b border-border flex items-center justify-between">
              <h3 class="font-medium flex items-center gap-2">
                <FolderOpen class="w-4 h-4 text-green-500" />
                {{ t('skill.files') }}
              </h3>
              <button
                @click="refreshFiles"
                :disabled="fileBrowser.loading.value"
                class="p-1.5 rounded hover:bg-muted transition-colors"
                :title="t('common.refresh')"
              >
                <RefreshCw class="w-4 h-4 text-muted-foreground" :class="fileBrowser.loading.value ? 'animate-spin' : ''" />
              </button>
            </div>

            <!-- 路径导航 -->
            <div v-if="fileBrowser.currentPath.value" class="flex items-center gap-2 px-4 py-2 bg-muted/30 text-sm border-b border-border">
              <button
                @click="fileBrowser.navigateToRoot"
                class="text-primary hover:underline"
              >
                {{ skillName }}
              </button>
              <template v-for="(segment, index) in fileBrowser.pathSegments.value" :key="index">
                <ChevronRight class="w-3 h-3 text-muted-foreground" />
                <button 
                  @click="fileBrowser.navigateToSegment(index)"
                  class="text-primary hover:underline"
                >
                  {{ segment }}
                </button>
              </template>
            </div>

            <!-- 文件列表内容 -->
            <div class="max-h-64 overflow-y-auto">
              <div v-if="fileBrowser.loading.value" class="flex items-center justify-center py-8">
                <Loader2 class="w-5 h-5 animate-spin text-primary mr-2" />
                <span class="text-muted-foreground text-sm">{{ t('common.loading') }}</span>
              </div>
              
              <div v-else-if="fileBrowser.sortedFiles.value.length > 0">
                <div
                  v-for="file in fileBrowser.sortedFiles.value"
                  :key="file.name"
                  class="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                  @click="handleFileClick(file)"
                >
                  <Folder v-if="file.is_directory" class="w-4 h-4 text-yellow-500" />
                  <FileIcon v-else class="w-4 h-4" :class="fileBrowser.getFileIconColor(file.name)" />
                  <span class="flex-1 text-sm truncate" :class="file.is_directory ? 'text-primary font-medium' : ''">
                    {{ file.name }}
                  </span>
                  <span class="text-xs text-muted-foreground">
                    {{ file.is_directory ? '-' : fileBrowser.formatFileSize(file.size) }}
                  </span>
                </div>
              </div>

              <div v-else class="flex flex-col items-center justify-center py-8 text-center">
                <FolderOpen class="w-8 h-8 text-muted-foreground/30 mb-2" />
                <p class="text-sm text-muted-foreground">{{ t('skill.noFiles') }}</p>
              </div>
            </div>
          </div>
      </div>

      <!-- SKILL.md 内容 Tab -->
      <div v-if="activeTab === 'content'" class="h-full">
        <div class="card-float h-full overflow-hidden">
          <MarkdownEditor
            ref="editorRef"
            :content="skillMdContent"
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

    <!-- 文件查看器 -->
    <UniversalViewer
      :is-open="showViewer"
      :file-name="viewerFileName"
      :file-content="viewerFileContent"
      :file-size="viewerFileSize"
      @close="closeViewer"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  Code, Trash2, FolderOpen, Folder, RefreshCw, Loader2, File as FileIcon, Info, FileCode, ChevronRight
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import Breadcrumb from "@/components/common/Breadcrumb.vue";
import MarkdownEditor from "@/components/viewer/MarkdownEditor.vue";
import UniversalViewer from "@/components/viewer/UniversalViewer.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { agentApi } from "@/services/api";
import { 
  useFileBrowser, 
  type FileInfo,
  BINARY_EXTENSIONS,
  PREVIEWABLE_EXTENSIONS,
} from "@/composables/useFileBrowser";

const { t } = useI18n();
const store = useCatalogStore();

// Props
const props = defineProps<{
  catalogId: string;
  agentName: string;
  skillName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'deleted'): void;
}>();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedAgent = computed(() => store.selectedAgent.value);

// 文件浏览器
const fileBrowser = useFileBrowser();

// Skill 数据
const skillMdContent = ref('');
const skillPath = ref('');  // 从后端获取的完整路径
const isLoading = ref(false);

// 启用状态从 agent 的 capabilities.native_skills 中计算得出
const isEnabled = computed(() => {
  const nativeSkills = selectedAgent.value?.capabilities?.native_skills || [];
  return nativeSkills.some(s => s.name === props.skillName);
});

// Editor 引用
const editorRef = ref<InstanceType<typeof MarkdownEditor> | null>(null);

// Tab 状态
const activeTab = ref<'overview' | 'content'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('skill.overview'), icon: Info },
  { id: 'content' as const, label: 'SKILL.md', icon: FileCode },
]);

// 弹窗状态
const showDeleteDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 文件查看器状态
const showViewer = ref(false);
const viewerFileName = ref('');
const viewerFileContent = ref<string | ArrayBuffer | null>(null);
const viewerFileSize = ref<number | undefined>(undefined);

// 加载 Skill 详情
async function loadSkill() {
  if (!props.catalogId || !props.agentName || !props.skillName) return;
  
  isLoading.value = true;
  try {
    // 获取 SKILL.md 内容和路径
    const response = await agentApi.getSkill(props.catalogId, props.agentName, props.skillName);
    skillMdContent.value = response.content || '';
    skillPath.value = response.path || '';
    
    // 初始化文件浏览器
    if (skillPath.value) {
      fileBrowser.init(skillPath.value);
      fileBrowser.refreshFiles();
    }
  } catch (e) {
    console.error('Failed to load skill:', e);
    handleError(t('errors.loadSkillFailed'));
  } finally {
    isLoading.value = false;
  }
}

// 刷新文件列表
function refreshFiles() {
  if (!skillPath.value) return;
  fileBrowser.refreshFiles();
}

// 处理文件点击
function handleFileClick(file: FileInfo) {
  if (file.is_directory) {
    // 进入文件夹
    fileBrowser.navigateToFolder(file);
  } else {
    // 打开文件预览
    openFileViewer(file);
  }
}

// 切换启用状态
async function toggleEnabled() {
  const newEnabled = !isEnabled.value;
  try {
    await agentApi.toggleSkillEnabled(props.catalogId, props.agentName, props.skillName, newEnabled);
    // 刷新 Agent 数据以更新 capabilities.native_skills 列表
    await store.refreshSelectedAgent();
  } catch (e) {
    console.error('Failed to toggle enabled:', e);
    handleError(t('errors.updateSkillFailed'));
  }
}

// 保存 SKILL.md 内容
async function handleSaveContent(content: string) {
  try {
    await agentApi.createSkill(props.catalogId, props.agentName, props.skillName, content);
    skillMdContent.value = content;
    // 通知编辑器更新原始内容
    editorRef.value?.updateOriginalContent();
  } catch (e) {
    console.error('Failed to save content:', e);
    handleError(t('errors.updateSkillFailed'));
  }
}

// 打开文件查看器
async function openFileViewer(file: FileInfo) {
  if (file.is_directory) return;
  
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  
  if (!fileBrowser.isPreviewable(file.name)) {
    console.log('File type not supported for preview:', ext);
    return;
  }
  
  viewerFileName.value = file.name;
  viewerFileSize.value = file.size;
  viewerFileContent.value = null;
  showViewer.value = true;
  
  try {
    viewerFileContent.value = await fileBrowser.readFileContent(file);
  } catch (e) {
    console.error('Failed to load file content:', e);
    viewerFileContent.value = `Error loading file: ${e instanceof Error ? e.message : 'Unknown error'}`;
  }
}

// 关闭文件查看器
function closeViewer() {
  showViewer.value = false;
  viewerFileName.value = '';
  viewerFileContent.value = null;
  viewerFileSize.value = undefined;
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

// 确认删除 Skill
function confirmDeleteSkill() {
  deleteMessage.value = t('skill.confirmDelete', { name: props.skillName });
  deleteDescription.value = t('skill.confirmDeleteDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  try {
    await agentApi.deleteSkill(props.catalogId, props.agentName, props.skillName);
    showDeleteDialog.value = false;
    emit('deleted');
  } catch (e) {
    console.error('Failed to delete skill:', e);
    handleError(t('errors.deleteSkillFailed'));
  }
}

// 监听 props 变化，重新加载
watch([() => props.catalogId, () => props.agentName, () => props.skillName], async () => {
  await loadSkill();
}, { immediate: true });
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
