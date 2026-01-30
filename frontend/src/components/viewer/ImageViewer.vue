<template>
  <div class="h-full flex items-center justify-center bg-muted/20 overflow-hidden">
    <!-- 加载中状态 -->
    <div v-if="!hasValidSource" class="flex flex-col items-center justify-center text-muted-foreground">
      <Loader2 class="w-8 h-8 animate-spin mb-2" />
      <span class="text-sm">加载图片中...</span>
    </div>
    
    <!-- 图片容器 -->
    <div 
      v-else
      ref="containerRef"
      class="relative w-full h-full flex items-center justify-center overflow-hidden"
      @wheel.prevent="handleWheel"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
    >
      <img
        ref="imageRef"
        :src="imageSrc"
        :alt="fileName"
        :style="imageStyle"
        class="max-w-full max-h-full object-contain select-none transition-transform duration-100"
        @load="handleLoad"
        @error="handleError"
        draggable="false"
      />
    </div>
    
    <!-- 控制栏 -->
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-card/90 backdrop-blur-sm rounded-lg px-4 py-2 shadow-lg">
      <button
        @click="zoomOut"
        :disabled="scale <= 0.1"
        class="p-1.5 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        :title="t('viewer.zoomOut')"
      >
        <ZoomOut class="w-4 h-4" />
      </button>
      <span class="text-sm w-16 text-center">{{ Math.round(scale * 100) }}%</span>
      <button
        @click="zoomIn"
        :disabled="scale >= 5"
        class="p-1.5 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        :title="t('viewer.zoomIn')"
      >
        <ZoomIn class="w-4 h-4" />
      </button>
      <div class="w-px h-4 bg-border mx-1"></div>
      <button
        @click="resetZoom"
        class="p-1.5 rounded hover:bg-muted"
        :title="t('viewer.resetZoom')"
      >
        <RotateCcw class="w-4 h-4" />
      </button>
      <button
        @click="fitToScreen"
        class="p-1.5 rounded hover:bg-muted"
        :title="t('viewer.fitToScreen')"
      >
        <Maximize class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ZoomIn, ZoomOut, RotateCcw, Maximize, Loader2 } from 'lucide-vue-next';

const { t } = useI18n();

const props = defineProps<{
  url?: string;
  content?: string | ArrayBuffer | null;
  fileName: string;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
}>();

// Refs
const containerRef = ref<HTMLDivElement | null>(null);
const imageRef = ref<HTMLImageElement | null>(null);
const objectUrl = ref<string | null>(null);

// 状态
const scale = ref(1);
const translateX = ref(0);
const translateY = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);

// 检查是否有有效的图片源
const hasValidSource = computed(() => {
  if (props.url) return true;
  if (props.content) {
    if (typeof props.content === 'string' && props.content.length > 0) return true;
    if (props.content instanceof ArrayBuffer && props.content.byteLength > 0) return true;
  }
  return false;
});

// 图片源
const imageSrc = computed(() => {
  if (props.url) {
    return props.url;
  }
  if (props.content) {
    if (typeof props.content === 'string') {
      // Base64 或 Data URL
      if (props.content.startsWith('data:')) {
        return props.content;
      }
      return `data:image/png;base64,${props.content}`;
    }
    // ArrayBuffer - 创建 Object URL
    if (props.content instanceof ArrayBuffer && props.content.byteLength > 0) {
      // 清理旧的 Object URL
      if (objectUrl.value) {
        URL.revokeObjectURL(objectUrl.value);
      }
      const blob = new Blob([props.content]);
      objectUrl.value = URL.createObjectURL(blob);
      return objectUrl.value;
    }
  }
  return '';
});

// 图片样式
const imageStyle = computed(() => ({
  transform: `scale(${scale.value}) translate(${translateX.value}px, ${translateY.value}px)`,
  cursor: isDragging.value ? 'grabbing' : (scale.value > 1 ? 'grab' : 'default'),
}));

// 加载完成
function handleLoad() {
  fitToScreen();
}

// 加载错误
function handleError() {
  emit('error', 'Failed to load image');
}

// 缩放
function zoomIn() {
  scale.value = Math.min(5, scale.value * 1.25);
}

function zoomOut() {
  scale.value = Math.max(0.1, scale.value / 1.25);
}

function resetZoom() {
  scale.value = 1;
  translateX.value = 0;
  translateY.value = 0;
}

function fitToScreen() {
  if (!imageRef.value || !containerRef.value) return;
  
  const img = imageRef.value;
  const container = containerRef.value;
  
  const scaleX = container.clientWidth / img.naturalWidth;
  const scaleY = container.clientHeight / img.naturalHeight;
  
  scale.value = Math.min(scaleX, scaleY, 1) * 0.9;
  translateX.value = 0;
  translateY.value = 0;
}

// 滚轮缩放
function handleWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.max(0.1, Math.min(5, scale.value * delta));
  scale.value = newScale;
}

// 拖拽
function handleMouseDown(e: MouseEvent) {
  if (scale.value <= 1) return;
  isDragging.value = true;
  dragStartX.value = e.clientX - translateX.value * scale.value;
  dragStartY.value = e.clientY - translateY.value * scale.value;
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return;
  translateX.value = (e.clientX - dragStartX.value) / scale.value;
  translateY.value = (e.clientY - dragStartY.value) / scale.value;
}

function handleMouseUp() {
  isDragging.value = false;
}

onMounted(() => {
  // 组件挂载
});

// 清理 Object URL
onUnmounted(() => {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = null;
  }
});
</script>
