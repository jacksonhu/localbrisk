<template>
  <Teleport to="body">
    <Transition name="fade">
      <div 
        v-if="isOpen" 
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- 背景遮罩 -->
        <div 
          class="absolute inset-0 bg-black/70 backdrop-blur-sm" 
          @click="close"
        ></div>
        
        <!-- 查看器容器 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[90vw] h-[90vh] max-w-6xl flex flex-col overflow-hidden">
          <!-- 头部 -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
            <div class="flex items-center gap-3">
              <component :is="fileTypeIcon" class="w-5 h-5" :class="fileTypeColor" />
              <span class="font-medium truncate max-w-md">{{ fileName }}</span>
              <span class="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
                {{ fileExtension.toUpperCase() }}
              </span>
              <span v-if="fileSize" class="text-xs text-muted-foreground">
                {{ formatFileSize(fileSize) }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <!-- 下载按钮 -->
              <button
                v-if="canDownload"
                @click="handleDownload"
                class="p-2 rounded-lg hover:bg-muted transition-colors"
                :title="t('volumeDetail.download')"
              >
                <Download class="w-4 h-4" />
              </button>
              <!-- 全屏按钮 -->
              <button
                @click="toggleFullscreen"
                class="p-2 rounded-lg hover:bg-muted transition-colors"
                :title="isFullscreen ? t('common.exitFullscreen') : t('common.fullscreen')"
              >
                <Maximize2 v-if="!isFullscreen" class="w-4 h-4" />
                <Minimize2 v-else class="w-4 h-4" />
              </button>
              <!-- 关闭按钮 -->
              <button
                @click="close"
                class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                :title="t('common.close')"
              >
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <!-- 内容区域 -->
          <div class="flex-1 overflow-hidden">
            <!-- 加载状态 -->
            <div v-if="loading" class="h-full flex items-center justify-center">
              <Loader2 class="w-8 h-8 animate-spin text-primary" />
              <span class="ml-3 text-muted-foreground">{{ t('common.loading') }}</span>
            </div>
            
            <!-- 错误状态 -->
            <div v-else-if="error" class="h-full flex flex-col items-center justify-center text-center p-8">
              <div class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center mb-4">
                <AlertCircle class="w-8 h-8 text-red-500" />
              </div>
              <p class="text-red-600 dark:text-red-400 mb-2">{{ error }}</p>
              <button
                @click="reload"
                class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
              >
                {{ t('common.retry') }}
              </button>
            </div>
            
            <!-- 文件内容 -->
            <template v-else>
              <!-- PDF 预览 -->
              <PdfViewer 
                v-if="fileType === 'pdf'" 
                :url="fileUrl"
                :content="fileContent"
                @error="handleError"
              />
              
              <!-- 图片预览 -->
              <ImageViewer 
                v-else-if="fileType === 'image'" 
                :url="fileUrl"
                :content="fileContent"
                :file-name="fileName"
                @error="handleError"
              />
              
              <!-- 文本/代码预览 -->
              <TextViewer 
                v-else-if="fileType === 'text' || fileType === 'code'" 
                :content="fileContent"
                :file-name="fileName"
                :language="codeLanguage"
                @error="handleError"
              />
              
              <!-- Markdown 预览 -->
              <MarkdownViewer 
                v-else-if="fileType === 'markdown'" 
                :content="fileContent"
                @error="handleError"
              />
              
              <!-- Office 文档预览 -->
              <OfficeViewer 
                v-else-if="fileType === 'office'" 
                :content="fileContent"
                :file-name="fileName"
                :file-extension="fileExtension"
                @error="handleError"
              />
              
              <!-- Excel/CSV 预览 -->
              <SpreadsheetViewer 
                v-else-if="fileType === 'spreadsheet'" 
                :content="fileContent"
                :file-name="fileName"
                :file-extension="fileExtension"
                @error="handleError"
              />
              
              <!-- 不支持的格式 -->
              <div v-else class="h-full flex flex-col items-center justify-center text-center p-8">
                <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
                  <FileQuestion class="w-8 h-8 text-muted-foreground" />
                </div>
                <p class="text-muted-foreground mb-2">{{ t('viewer.unsupportedFormat') }}</p>
                <p class="text-sm text-muted-foreground">{{ fileExtension.toUpperCase() }}</p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { 
  X, Download, Maximize2, Minimize2, Loader2, AlertCircle,
  FileText, FileCode, FileImage, FileSpreadsheet, FileQuestion,
  File as FileIcon
} from 'lucide-vue-next';
import PdfViewer from './PdfViewer.vue';
import ImageViewer from './ImageViewer.vue';
import TextViewer from './TextViewer.vue';
import MarkdownViewer from './MarkdownViewer.vue';
import OfficeViewer from './OfficeViewer.vue';
import SpreadsheetViewer from './SpreadsheetViewer.vue';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  fileName: string;
  fileUrl?: string;
  fileContent?: string | ArrayBuffer | null;
  fileSize?: number;
  canDownload?: boolean;
  onDownload?: () => void;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'download'): void;
}>();

// 状态
const loading = ref(false);
const error = ref<string | null>(null);
const isFullscreen = ref(false);

// 文件扩展名
const fileExtension = computed(() => {
  const parts = props.fileName.split('.');
  return parts.length > 1 ? parts.pop()?.toLowerCase() || '' : '';
});

// 文件类型映射
const FILE_TYPE_MAP: Record<string, string> = {
  // PDF
  pdf: 'pdf',
  // 图片
  jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', 
  webp: 'image', bmp: 'image', svg: 'image', ico: 'image',
  // Markdown
  md: 'markdown', markdown: 'markdown',
  // Office 文档
  doc: 'office', docx: 'office', 
  ppt: 'office', pptx: 'office',
  // 表格
  xls: 'spreadsheet', xlsx: 'spreadsheet', csv: 'spreadsheet',
  // 代码
  js: 'code', ts: 'code', jsx: 'code', tsx: 'code',
  vue: 'code', py: 'code', java: 'code', go: 'code',
  rs: 'code', c: 'code', cpp: 'code', h: 'code',
  cs: 'code', rb: 'code', php: 'code', swift: 'code',
  kt: 'code', scala: 'code', sql: 'code', sh: 'code',
  bash: 'code', zsh: 'code', ps1: 'code',
  html: 'code', css: 'code', scss: 'code', less: 'code',
  json: 'code', yaml: 'code', yml: 'code', xml: 'code',
  toml: 'code', ini: 'code', conf: 'code',
  // 文本
  txt: 'text', log: 'text', env: 'text',
};

// 代码语言映射
const LANGUAGE_MAP: Record<string, string> = {
  js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  vue: 'vue', py: 'python', java: 'java', go: 'go',
  rs: 'rust', c: 'c', cpp: 'cpp', h: 'c',
  cs: 'csharp', rb: 'ruby', php: 'php', swift: 'swift',
  kt: 'kotlin', scala: 'scala', sql: 'sql', sh: 'shell',
  bash: 'shell', zsh: 'shell', ps1: 'powershell',
  html: 'html', css: 'css', scss: 'scss', less: 'less',
  json: 'json', yaml: 'yaml', yml: 'yaml', xml: 'xml',
  toml: 'toml', ini: 'ini', conf: 'ini',
  md: 'markdown', markdown: 'markdown',
  txt: 'plaintext', log: 'plaintext',
};

// 文件类型
const fileType = computed(() => {
  return FILE_TYPE_MAP[fileExtension.value] || 'unknown';
});

// 代码语言
const codeLanguage = computed(() => {
  return LANGUAGE_MAP[fileExtension.value] || 'plaintext';
});

// 文件类型图标
const fileTypeIcon = computed(() => {
  switch (fileType.value) {
    case 'pdf': return FileText;
    case 'image': return FileImage;
    case 'code': return FileCode;
    case 'text': return FileText;
    case 'markdown': return FileText;
    case 'office': return FileText;
    case 'spreadsheet': return FileSpreadsheet;
    default: return FileIcon;
  }
});

// 文件类型颜色
const fileTypeColor = computed(() => {
  switch (fileType.value) {
    case 'pdf': return 'text-red-500';
    case 'image': return 'text-purple-500';
    case 'code': return 'text-blue-500';
    case 'text': return 'text-gray-500';
    case 'markdown': return 'text-green-500';
    case 'office': return 'text-blue-600';
    case 'spreadsheet': return 'text-green-600';
    default: return 'text-gray-500';
  }
});

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
}

// 关闭
function close() {
  emit('close');
}

// 下载
function handleDownload() {
  emit('download');
}

// 全屏切换
function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value;
}

// 处理错误
function handleError(msg: string) {
  error.value = msg;
}

// 重新加载
function reload() {
  error.value = null;
  // 触发重新加载逻辑
}

// 监听打开状态
watch(() => props.isOpen, (open) => {
  if (open) {
    error.value = null;
    // 按 ESC 关闭
    document.addEventListener('keydown', handleKeydown);
  } else {
    document.removeEventListener('keydown', handleKeydown);
    isFullscreen.value = false;
  }
});

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close();
  }
}
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
