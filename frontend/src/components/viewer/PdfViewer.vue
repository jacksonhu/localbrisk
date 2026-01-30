<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">{{ t('viewer.page') }}:</span>
        <button
          @click="prevPage"
          :disabled="currentPage <= 1"
          class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>
        <span class="text-sm">{{ currentPage }} / {{ totalPages }}</span>
        <button
          @click="nextPage"
          :disabled="currentPage >= totalPages"
          class="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="zoomOut"
          :disabled="scale <= 0.5"
          class="p-1.5 rounded hover:bg-muted disabled:opacity-50"
        >
          <ZoomOut class="w-4 h-4" />
        </button>
        <span class="text-sm w-16 text-center">{{ Math.round(scale * 100) }}%</span>
        <button
          @click="zoomIn"
          :disabled="scale >= 3"
          class="p-1.5 rounded hover:bg-muted disabled:opacity-50"
        >
          <ZoomIn class="w-4 h-4" />
        </button>
        <button
          @click="resetZoom"
          class="p-1.5 rounded hover:bg-muted"
        >
          <RotateCcw class="w-4 h-4" />
        </button>
      </div>
    </div>
    
    <!-- PDF 内容 -->
    <div 
      ref="containerRef"
      class="flex-1 overflow-auto bg-muted/50 flex justify-center p-4"
    >
      <!-- 使用 iframe 或 embed 预览 PDF -->
      <template v-if="pdfUrl">
        <iframe
          :src="pdfUrl"
          class="w-full h-full border-0 bg-white rounded-lg shadow-lg"
          :style="{ transform: `scale(${scale})`, transformOrigin: 'top center' }"
        ></iframe>
      </template>
      
      <!-- 如果没有 URL，显示提示 -->
      <div v-else class="flex flex-col items-center justify-center text-center">
        <FileText class="w-16 h-16 text-muted-foreground mb-4" />
        <p class="text-muted-foreground">{{ t('viewer.pdfNotSupported') }}</p>
        <p class="text-sm text-muted-foreground mt-2">{{ t('viewer.pdfDownloadHint') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw, FileText } from 'lucide-vue-next';

const { t } = useI18n();

const props = defineProps<{
  url?: string;
  content?: string | ArrayBuffer | null;
}>();

defineEmits<{
  (e: 'error', message: string): void;
}>();

// Refs
const containerRef = ref<HTMLDivElement | null>(null);

// 状态
const currentPage = ref(1);
const totalPages = ref(1);
const scale = ref(1);
const objectUrl = ref<string | null>(null);

// PDF URL
const pdfUrl = computed(() => {
  if (props.url) {
    return props.url;
  }
  
  if (props.content) {
    // 如果是 ArrayBuffer，创建 Blob URL
    if (props.content instanceof ArrayBuffer) {
      if (objectUrl.value) {
        URL.revokeObjectURL(objectUrl.value);
      }
      const blob = new Blob([props.content], { type: 'application/pdf' });
      objectUrl.value = URL.createObjectURL(blob);
      return objectUrl.value;
    }
    
    // 如果是 Base64 字符串
    if (typeof props.content === 'string') {
      if (props.content.startsWith('data:')) {
        return props.content;
      }
      return `data:application/pdf;base64,${props.content}`;
    }
  }
  
  return null;
});

// 分页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
}

// 缩放
function zoomIn() {
  scale.value = Math.min(3, scale.value + 0.25);
}

function zoomOut() {
  scale.value = Math.max(0.5, scale.value - 0.25);
}

function resetZoom() {
  scale.value = 1;
}

onMounted(() => {
  // 初始化
});

onUnmounted(() => {
  // 清理 Object URL
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
  }
});
</script>
