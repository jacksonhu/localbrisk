<template>
  <div class="volume-detail-panel h-full flex flex-col p-6">
    <!-- 面包屑导航 -->
    <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4">
      <button 
        class="flex items-center gap-1 hover:text-foreground transition-colors"
        @click="goBack"
      >
        <ArrowLeft class="w-4 h-4" />
      </button>
      <span class="text-primary cursor-pointer hover:underline" @click="goToCatalog">
        {{ selectedCatalog?.display_name || selectedCatalog?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span class="text-primary cursor-pointer hover:underline" @click="goToSchema">
        {{ selectedSchema?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span>{{ selectedAsset?.name }}</span>
    </div>

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <FolderOpen class="w-6 h-6 text-green-500" />
        <h1 class="text-2xl font-semibold">{{ selectedAsset?.name }}</h1>
        <!-- 类型标识 -->
        <span class="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
          Volume
        </span>
        <!-- 存储类型标识 -->
        <span 
          :class="volumeType === 'local' 
            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
            : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'"
          class="px-2 py-0.5 text-xs rounded flex items-center gap-1"
        >
          <HardDrive v-if="volumeType === 'local'" class="w-3 h-3" />
          <Cloud v-else class="w-3 h-3" />
          {{ volumeType === 'local' ? t('asset.volumeTypeLocal') : t('asset.volumeTypeS3') }}
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="confirmDeleteVolume"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('volumeDetail.deleteVolume')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
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
    <div class="flex-1 overflow-hidden flex flex-col">
      <!-- 概览 Tab -->
      <template v-if="activeTab === 'overview'">
        <!-- 描述区域 -->
        <div class="card-float p-4 mb-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium flex items-center gap-2">
              {{ t('common.description') }}
              <button 
                @click="editDescription"
                class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center"
              >
                <Pencil class="w-4 h-4 text-muted-foreground" />
              </button>
            </h3>
          </div>
          <p class="text-muted-foreground text-sm">
            {{ volumeDescription || t('detail.noDescription') }}
          </p>
        </div>

        <!-- 操作栏 -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <button
              v-if="volumeType === 'local'"
              @click="createFolder"
              class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2"
            >
              <FolderPlus class="w-4 h-4" />
              {{ t('volumeDetail.createFolder') }}
            </button>
            <button
              @click="refreshFiles"
              :disabled="loadingFiles"
              class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw class="w-4 h-4" :class="loadingFiles ? 'animate-spin' : ''" />
              {{ t('common.refresh') }}
            </button>
            <button
              v-if="volumeType === 'local'"
              @click="downloadSelected"
              :disabled="selectedFiles.length === 0"
              class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download class="w-4 h-4" />
              {{ t('volumeDetail.download') }}
            </button>
          </div>
          
          <!-- 搜索框 -->
          <div class="relative w-64">
            <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              v-model="fileFilter"
              type="text"
              :placeholder="t('volumeDetail.searchFiles')"
              class="w-full pl-9 pr-4 py-1.5 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background"
            />
          </div>
        </div>

        <!-- 当前路径 -->
        <div class="flex items-center gap-2 text-sm mb-4 px-1">
          <span class="text-muted-foreground">{{ t('volumeDetail.currentPath') }}:</span>
          <div class="flex items-center gap-1">
            <button 
              @click="navigateToRoot"
              class="text-primary hover:underline flex items-center gap-1"
            >
              <FolderOpen class="w-4 h-4" />
              {{ selectedAsset?.name }}
            </button>
            <template v-for="(segment, index) in pathSegments" :key="index">
              <ChevronRight class="w-3 h-3 text-muted-foreground" />
              <button 
                @click="navigateToSegment(index)"
                class="text-primary hover:underline"
              >
                {{ segment }}
              </button>
            </template>
          </div>
          <button 
            v-if="currentPath"
            @click="refreshFiles"
            class="ml-2 p-1 rounded hover:bg-muted"
            :title="t('common.refresh')"
          >
            <RefreshCw class="w-3 h-3 text-muted-foreground" />
          </button>
        </div>

        <!-- 文件列表 -->
        <div class="flex-1 card-float overflow-hidden flex flex-col">
          <!-- 表头 -->
          <div class="grid grid-cols-12 gap-4 text-sm font-medium text-muted-foreground border-b border-border px-4 py-3 bg-muted/30">
            <div class="col-span-1 flex items-center">
              <input
                type="checkbox"
                v-model="selectAll"
                @change="toggleSelectAll"
                class="w-4 h-4 rounded border-border"
              />
            </div>
            <span class="col-span-5">{{ t('volumeDetail.fileName') }}</span>
            <span class="col-span-2">{{ t('volumeDetail.size') }}</span>
            <span class="col-span-2">{{ t('volumeDetail.modifiedTime') }}</span>
            <span class="col-span-2">{{ t('common.actions') }}</span>
          </div>

          <!-- 文件行 -->
          <div class="flex-1 overflow-y-auto">
            <!-- 加载状态 -->
            <div v-if="loadingFiles" class="flex items-center justify-center py-12">
              <Loader2 class="w-6 h-6 animate-spin text-primary" />
              <span class="ml-2 text-muted-foreground">{{ t('common.loading') }}</span>
            </div>

            <!-- 错误状态 -->
            <div v-else-if="errorMessage" class="flex flex-col items-center justify-center py-12 text-center">
              <div class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center mb-4">
                <FolderOpen class="w-8 h-8 text-red-500" />
              </div>
              <p class="text-red-600 dark:text-red-400 mb-2">{{ errorMessage }}</p>
              <button
                @click="refreshFiles"
                class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
              >
                {{ t('common.refresh') }}
              </button>
            </div>

            <!-- 文件列表 -->
            <template v-else-if="filteredFiles.length > 0">
              <div
                v-for="file in filteredFiles"
                :key="file.name"
                class="grid grid-cols-12 gap-4 text-sm px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                @click="handleFileClick(file)"
                @dblclick="handleFileDoubleClick(file)"
              >
                <div class="col-span-1 flex items-center">
                  <input
                    type="checkbox"
                    :checked="selectedFiles.includes(file.name)"
                    @click.stop
                    @change="toggleFileSelect(file.name)"
                    class="w-4 h-4 rounded border-border"
                  />
                </div>
                <div class="col-span-5 flex items-center gap-2">
                  <Folder v-if="file.is_directory" class="w-4 h-4 text-yellow-500" />
                  <FileIcon v-else class="w-4 h-4 text-gray-500" :class="getFileIconColor(file.name)" />
                  <span 
                    v-if="file.is_directory"
                    class="font-medium truncate text-primary hover:underline cursor-pointer"
                    @click.stop="navigateToFolder(file)"
                  >
                    {{ file.name }}
                  </span>
                  <span v-else class="font-medium truncate">
                    {{ file.name }}
                  </span>
                </div>
                <span class="col-span-2 text-muted-foreground">
                  {{ file.is_directory ? '-' : formatFileSize(file.size) }}
                </span>
                <span class="col-span-2 text-muted-foreground">
                  {{ file.modified_time ? formatDate(file.modified_time) : '-' }}
                </span>
               
                <div class="col-span-2 flex items-center gap-1">
                  <!-- 预览按钮 -->
                  <button
                    v-if="!file.is_directory && isPreviewable(file.name)"
                    @click.stop="openFileViewer(file)"
                    class="p-1 rounded hover:bg-primary/10 text-muted-foreground hover:text-primary"
                    :title="t('viewer.preview')"
                  >
                    <Eye class="w-4 h-4" />
                  </button>
                  <!-- 下载按钮 -->
                  <button
                    v-if="!file.is_directory && volumeType === 's3'"
                    @click.stop="downloadFile(file)"
                    class="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                    :title="t('volumeDetail.download')"
                  >
                    <Download class="w-4 h-4" />
                  </button>
                  <!-- 删除按钮 -->
                  <button
                    @click.stop="confirmDeleteFile(file)"
                    class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-muted-foreground hover:text-red-600"
                    :title="t('common.delete')"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </template>

            <!-- 空状态 -->
            <div v-else class="flex flex-col items-center justify-center py-12 text-center">
              <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
                <FolderOpen class="w-8 h-8 text-muted-foreground" />
              </div>
              <p class="text-muted-foreground">{{ t('volumeDetail.emptyFolder') }}</p>
            </div>
          </div>

          <!-- 底部统计和分页 -->
          <div class="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/30 text-sm">
            <span class="text-muted-foreground">
              {{ t('volumeDetail.totalItems', { count: allFilteredFiles.length }) }}
            </span>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">{{ t('volumeDetail.itemsPerPage') }}</span>
              <select 
                v-model="pageSize" 
                class="px-2 py-1 border border-border rounded bg-background text-sm"
              >
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
              <div class="flex items-center gap-1 ml-4">
                <button 
                  @click="goToFirstPage"
                  :disabled="currentPage === 1"
                  class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronsLeft class="w-4 h-4" />
                </button>
                <button 
                  @click="goToPrevPage"
                  :disabled="currentPage === 1"
                  class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft class="w-4 h-4" />
                </button>
                <span class="px-3">{{ currentPage }}</span>
                <span class="text-muted-foreground">/ {{ totalPages }} {{ t('volumeDetail.pages') }}</span>
                <button 
                  @click="goToNextPage"
                  :disabled="currentPage === totalPages"
                  class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight class="w-4 h-4" />
                </button>
                <button 
                  @click="goToLastPage"
                  :disabled="currentPage === totalPages"
                  class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronsRight class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 配置 Tab -->
      <div v-if="activeTab === 'config'" class="flex-1">
        <div class="card-float h-full flex flex-col">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h3 class="font-medium flex items-center gap-2">
              <FileCode class="w-4 h-4" />
              {{ t('detail.configFile') }}
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
    </div>

    <!-- 确认删除弹窗 -->
    <ConfirmDialog
      :is-open="showDeleteDialog"
      :message="deleteMessage"
      :description="deleteDescription"
      @close="showDeleteDialog = false"
      @confirm="handleConfirmDelete"
    />

    <!-- 创建文件夹弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showCreateFolderDialog" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showCreateFolderDialog = false"></div>
          <div class="relative bg-card rounded-xl shadow-float-lg w-[400px] p-6">
            <h3 class="text-lg font-semibold mb-4">{{ t('volumeDetail.createFolder') }}</h3>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium mb-2">{{ t('volumeDetail.folderName') }}</label>
                <input
                  v-model="newFolderName"
                  type="text"
                  :placeholder="t('volumeDetail.folderNameHint')"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  @keyup.enter="handleCreateFolder"
                />
              </div>
              <div class="flex justify-end gap-3">
                <button
                  @click="showCreateFolderDialog = false"
                  class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
                >
                  {{ t('common.cancel') }}
                </button>
                <button
                  @click="handleCreateFolder"
                  :disabled="!newFolderName.trim()"
                  class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {{ t('common.create') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 文件查看器 -->
    <UniversalViewer
      :is-open="showViewer"
      :file-name="viewerFileName"
      :file-content="viewerFileContent"
      :file-size="viewerFileSize"
      :can-download="volumeType === 's3'"
      @close="closeViewer"
      @download="downloadViewerFile"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight,
  FolderOpen, Folder, Pencil, Search, Trash2, RefreshCw, Download,
  FolderPlus, File as FileIcon, Loader2, HardDrive, Cloud,
  FileText, FileCode, Save, Copy, Eye
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import UniversalViewer from "@/components/viewer/UniversalViewer.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { assetApi } from "@/services/api";
import { 
  createLocalVolumeService, 
  createS3VolumeService,
  type FileInfo,
  type VolumeFileService,
  type S3Config
} from "@/services/fileService";
import { 
  PREVIEWABLE_EXTENSIONS, 
  BINARY_EXTENSIONS, 
  FILE_ICON_COLORS,
  isFilePreviewable,
  isBinaryFile,
  getFileIconColor,
  formatFileSize,
  formatDate,
  readLocalFileContent,
} from "@/composables/useFileBrowser";

const { t } = useI18n();
const store = useCatalogStore();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedSchema = computed(() => store.selectedSchema.value);
const selectedAsset = computed(() => store.selectedAsset.value);

// Tab 状态
const activeTab = ref<'overview' | 'config'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// Volume 信息
const volumeDescription = computed(() => {
  return selectedAsset.value?.metadata?.description || '';
});

const volumeType = computed(() => {
  return selectedAsset.value?.metadata?.volume_type || 'local';
});

// 存储路径
const storageLocation = computed(() => {
  return selectedAsset.value?.metadata?.storage_location || '';
});

// S3 配置
const s3Config = computed<S3Config | null>(() => {
  const meta = selectedAsset.value?.metadata;
  if (!meta || volumeType.value !== 's3') return null;
  
  return {
    endpoint: meta.s3_endpoint || '',
    bucket: meta.s3_bucket || '',
    accessKey: meta.s3_access_key || '',
    secretKey: meta.s3_secret_key || '',
    region: meta.s3_region,
  };
});

// 文件服务实例
const fileService = ref<VolumeFileService | null>(null);

// 配置内容
const configContent = ref('');
const originalConfig = ref('');
const savingConfig = ref(false);

const configModified = computed(() => configContent.value !== originalConfig.value);

// 文件列表状态
const files = ref<FileInfo[]>([]);
const loadingFiles = ref(false);
const currentPath = ref('');
const fileFilter = ref('');
const selectedFiles = ref<string[]>([]);
const selectAll = ref(false);
const errorMessage = ref<string | null>(null);

// 分页状态
const pageSize = ref(20);
const currentPage = ref(1);

// 弹窗状态
const showDeleteDialog = ref(false);
const showCreateFolderDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');
const deleteTarget = ref<'volume' | 'file'>('volume');
const fileToDelete = ref<FileInfo | null>(null);
const newFolderName = ref('');

// 文件查看器状态
const showViewer = ref(false);
const viewerFileName = ref('');
const viewerFileContent = ref<string | ArrayBuffer | null>(null);
const viewerFileSize = ref<number | undefined>(undefined);
const loadingViewer = ref(false);

// 路径段
const pathSegments = computed(() => {
  if (!currentPath.value) return [];
  return currentPath.value.split('/').filter(Boolean);
});

// 所有过滤后的文件（用于计算总数）
const allFilteredFiles = computed(() => {
  let result = files.value;
  
  if (fileFilter.value) {
    const filter = fileFilter.value.toLowerCase();
    result = result.filter(f => f.name.toLowerCase().includes(filter));
  }
  
  // 文件夹优先排序
  return [...result].sort((a, b) => {
    if (a.is_directory && !b.is_directory) return -1;
    if (!a.is_directory && b.is_directory) return 1;
    return a.name.localeCompare(b.name);
  });
});

// 分页后的文件
const filteredFiles = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return allFilteredFiles.value.slice(start, end);
});

// 总页数
const totalPages = computed(() => {
  return Math.max(1, Math.ceil(allFilteredFiles.value.length / pageSize.value));
});

// 初始化文件服务
function initFileService() {
  if (volumeType.value === 'local' && storageLocation.value) {
    fileService.value = createLocalVolumeService(storageLocation.value);
  } else if (volumeType.value === 's3' && s3Config.value) {
    const config = s3Config.value;
    if (config.endpoint && config.bucket && config.accessKey && config.secretKey) {
      fileService.value = createS3VolumeService(config);
    } else {
      fileService.value = null;
      errorMessage.value = 'S3 configuration is incomplete';
    }
  } else {
    fileService.value = null;
  }
}

// 加载配置 - 从后端获取配置文件原始内容
async function loadConfig() {
  if (!selectedCatalog.value || !selectedSchema.value || !selectedAsset.value) {
    configContent.value = '';
    originalConfig.value = '';
    return;
  }
  
  try {
    const response = await assetApi.getConfig(
      selectedCatalog.value.id, 
      selectedSchema.value.name, 
      selectedAsset.value.name
    );
    configContent.value = response.content;
    originalConfig.value = response.content;
  } catch (e) {
    console.error('Failed to load asset config:', e);
    configContent.value = '';
    originalConfig.value = '';
  }
}

// 保存配置
async function saveConfig() {
  savingConfig.value = true;
  try {
    // TODO: 调用后端 API 保存配置
    console.log('Save config:', configContent.value);
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

// 导航函数
function goBack() {
  store.clearSelectedAsset();
}

function goToCatalog() {
  store.clearSelectedAsset();
  store.clearSelectedSchema();
}

function goToSchema() {
  store.clearSelectedAsset();
}

function navigateToRoot() {
  currentPath.value = '';
  refreshFiles();
}

function navigateToSegment(index: number) {
  const newPath = pathSegments.value.slice(0, index + 1).join('/');
  currentPath.value = newPath;
  refreshFiles();
}

// 文件操作
function handleFileClick(file: FileInfo) {
  // 单击选中 - 如果是文件，可以预览
  if (!file.is_directory) {
    openFileViewer(file);
  }
}

function handleFileDoubleClick(file: FileInfo) {
  if (file.is_directory) {
    navigateToFolder(file);
  } else {
    // 双击文件也打开预览
    openFileViewer(file);
  }
}

// 进入文件夹
function navigateToFolder(file: FileInfo) {
  if (!file.is_directory) return;
  currentPath.value = currentPath.value 
    ? `${currentPath.value}/${file.name}` 
    : file.name;
  currentPage.value = 1; // 重置分页
  refreshFiles();
}

// 检查文件是否可预览
function isPreviewable(fileName: string): boolean {
  return isFilePreviewable(fileName);
}

// 打开文件查看器
async function openFileViewer(file: FileInfo) {
  if (file.is_directory) return;
  
  if (!isPreviewable(file.name)) {
    // 不支持预览，可以考虑提示用户
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    console.log('File type not supported for preview:', ext);
    return;
  }
  
  loadingViewer.value = true;
  viewerFileName.value = file.name;
  viewerFileSize.value = file.size;
  viewerFileContent.value = null;
  showViewer.value = true;
  
  try {
    // 构建完整文件路径
    const fullPath = currentPath.value 
      ? `${storageLocation.value}/${currentPath.value}/${file.name}`
      : `${storageLocation.value}/${file.name}`;
    
    if (volumeType.value === 'local') {
      // 本地文件 - 使用公共函数读取
      viewerFileContent.value = await readLocalFileContent(fullPath);
    } else if (volumeType.value === 's3' && fileService.value) {
      // S3 文件 - 需要通过 fileService 读取
      // TODO: 实现 S3 文件内容读取
      viewerFileContent.value = 'S3 file preview not yet implemented';
    }
  } catch (e) {
    console.error('Failed to load file content:', e);
    viewerFileContent.value = `Error loading file: ${e instanceof Error ? e.message : 'Unknown error'}`;
  } finally {
    loadingViewer.value = false;
  }
}

// 关闭文件查看器
function closeViewer() {
  showViewer.value = false;
  viewerFileName.value = '';
  viewerFileContent.value = null;
  viewerFileSize.value = undefined;
}

// 下载查看器中的文件
function downloadViewerFile() {
  // TODO: 实现下载功能
  console.log('Download file:', viewerFileName.value);
}

function toggleSelectAll() {
  if (selectAll.value) {
    selectedFiles.value = filteredFiles.value.map(f => f.name);
  } else {
    selectedFiles.value = [];
  }
}

function toggleFileSelect(filename: string) {
  const index = selectedFiles.value.indexOf(filename);
  if (index === -1) {
    selectedFiles.value.push(filename);
  } else {
    selectedFiles.value.splice(index, 1);
  }
  selectAll.value = selectedFiles.value.length === filteredFiles.value.length;
}

// 刷新文件列表
async function refreshFiles() {
  if (!fileService.value) {
    errorMessage.value = volumeType.value === 'local' 
      ? 'Storage location not configured' 
      : 'S3 configuration is incomplete';
    files.value = [];
    return;
  }
  
  loadingFiles.value = true;
  errorMessage.value = null;
  selectedFiles.value = [];
  selectAll.value = false;
  
  try {
    const result = await fileService.value.listFiles(currentPath.value);
    files.value = result;
  } catch (e) {
    console.error('Failed to load files:', e);
    errorMessage.value = e instanceof Error ? e.message : 'Failed to load files';
    files.value = [];
  } finally {
    loadingFiles.value = false;
  }
}

// 编辑描述
function editDescription() {
  // TODO: 实现编辑描述功能
  console.log('Edit description - Not implemented yet');
}

// 创建文件夹
function createFolder() {
  newFolderName.value = '';
  showCreateFolderDialog.value = true;
}

async function handleCreateFolder() {
  if (!newFolderName.value.trim() || !fileService.value) return;
  
  try {
    await fileService.value.createFolder(newFolderName.value.trim(), currentPath.value);
    showCreateFolderDialog.value = false;
    await refreshFiles();
  } catch (e) {
    console.error('Failed to create folder:', e);
    errorMessage.value = e instanceof Error ? e.message : 'Failed to create folder';
  }
}

// 下载文件
function downloadFile(file: FileInfo) {
  // TODO: 实现下载功能
  console.log('Download file:', file.name);
}

function downloadSelected() {
  // TODO: 实现批量下载
  console.log('Download selected:', selectedFiles.value);
}

// 删除操作
function confirmDeleteVolume() {
  if (!selectedAsset.value) return;
  deleteTarget.value = 'volume';
  deleteMessage.value = t('volumeDetail.confirmDeleteVolume', { name: selectedAsset.value.name });
  deleteDescription.value = t('volumeDetail.confirmDeleteVolumeDesc');
  showDeleteDialog.value = true;
}

function confirmDeleteFile(file: FileInfo) {
  fileToDelete.value = file;
  deleteTarget.value = 'file';
  deleteMessage.value = t('volumeDetail.confirmDeleteFile', { name: file.name });
  deleteDescription.value = file.is_directory 
    ? t('volumeDetail.confirmDeleteFolderDesc') 
    : t('volumeDetail.confirmDeleteFileDesc');
  showDeleteDialog.value = true;
}

async function handleConfirmDelete() {
  if (deleteTarget.value === 'volume') {
    if (!selectedCatalog.value || !selectedSchema.value || !selectedAsset.value) return;
    
    const success = await store.deleteAsset(
      selectedCatalog.value.id, 
      selectedSchema.value.name, 
      selectedAsset.value.name
    );
    if (success) {
      showDeleteDialog.value = false;
      store.clearSelectedAsset();
    }
  } else if (deleteTarget.value === 'file' && fileToDelete.value && fileService.value) {
    try {
      await fileService.value.deleteFile(fileToDelete.value.name, currentPath.value);
      showDeleteDialog.value = false;
      fileToDelete.value = null;
      await refreshFiles();
    } catch (e) {
      console.error('Failed to delete file:', e);
      errorMessage.value = e instanceof Error ? e.message : 'Failed to delete file';
    }
  }
}

// 分页函数
function goToFirstPage() {
  currentPage.value = 1;
}

function goToPrevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
}

function goToNextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
}

function goToLastPage() {
  currentPage.value = totalPages.value;
}

// 监听资产变化
watch(selectedAsset, () => {
  activeTab.value = 'overview';
  currentPath.value = '';
  currentPage.value = 1;
  fileFilter.value = '';
  selectedFiles.value = [];
  errorMessage.value = null;
  loadConfig();
  initFileService();
  refreshFiles();
}, { immediate: true });

// 监听分页大小变化
watch(pageSize, () => {
  currentPage.value = 1;
});

// 组件挂载时初始化
onMounted(() => {
  initFileService();
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
