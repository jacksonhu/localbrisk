<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">{{ t('viewer.split') }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="isModified" class="text-xs text-amber-500 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          已修改
        </span>
        <button
          @click="handleSave"
          :disabled="!isModified || isSaving"
          class="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="isSaving" class="w-4 h-4 animate-spin" />
          <Save v-else class="w-4 h-4" />
          {{ t('common.save') }}
        </button>
        <button
          @click="copyContent"
          class="px-2 py-1.5 text-sm rounded hover:bg-muted transition-colors flex items-center gap-1"
        >
          <Copy class="w-4 h-4" />
          {{ t('common.copy') }}
        </button>
      </div>
    </div>
    
    <!-- 内容区域 - 左右分栏（可拖拽） -->
    <div ref="containerRef" class="flex-1 overflow-hidden flex">
      <!-- 左侧编辑区 -->
      <div 
        class="flex flex-col border-r border-border min-w-[200px]"
        :style="{ width: `${leftPanelWidth}%` }"
      >
        <div class="px-3 py-1.5 border-b border-border bg-muted/50 flex items-center gap-2">
          <Edit3 class="w-4 h-4 text-muted-foreground" />
          <span class="text-xs text-muted-foreground font-medium">编辑</span>
        </div>
        <div class="flex-1 overflow-hidden">
          <textarea
            ref="editorRef"
            v-model="editContent"
            class="w-full h-full p-4 font-mono text-sm leading-relaxed bg-background resize-none focus:outline-none"
            spellcheck="false"
            :placeholder="t('prompt.contentHint')"
          ></textarea>
        </div>
      </div>
      
      <!-- 可拖拽的分隔条 -->
      <div 
        class="resizer"
        :class="{ 'resizing': isResizing }"
        @mousedown="startResize"
      >
        <div class="resizer-handle"></div>
      </div>
      
      <!-- 右侧预览区 -->
      <div 
        class="flex flex-col min-w-[200px]"
        :style="{ width: `calc(${100 - leftPanelWidth}% - 6px)` }"
      >
        <div class="px-3 py-1.5 border-b border-border bg-muted/50 flex items-center gap-2">
          <Eye class="w-4 h-4 text-muted-foreground" />
          <span class="text-xs text-muted-foreground font-medium">{{ t('viewer.preview') }}</span>
        </div>
        <div class="flex-1 overflow-auto p-6">
          <div 
            class="prose prose-sm dark:prose-invert max-w-none"
            v-html="renderedHtml"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Copy, Save, Edit3, Eye, Loader2 } from 'lucide-vue-next';

const { t } = useI18n();

const props = defineProps<{
  content?: string;
  readonly?: boolean;
}>();

const emit = defineEmits<{
  (e: 'save', content: string): void;
  (e: 'change', content: string): void;
  (e: 'error', message: string): void;
}>();

// 状态
const editorRef = ref<HTMLTextAreaElement | null>(null);
const containerRef = ref<HTMLElement | null>(null);
const editContent = ref('');
const originalContent = ref('');
const isSaving = ref(false);

// 分栏拖拽状态
const leftPanelWidth = ref(50); // 默认左侧面板占 50%
const isResizing = ref(false);
const startX = ref(0);
const startWidth = ref(0);

// 是否已修改
const isModified = computed(() => editContent.value !== originalContent.value);

// 渲染后的 HTML
const renderedHtml = computed(() => {
  return renderMarkdown(editContent.value);
});

// 简单的 Markdown 渲染器
function renderMarkdown(md: string): string {
  if (!md) return '<p class="text-muted-foreground">暂无内容</p>';
  
  let html = md;
  
  // 转义 HTML 特殊字符
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  // 代码块 (```code```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre class="bg-muted rounded-lg p-4 overflow-x-auto"><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
  });
  
  // 行内代码 (`code`)
  html = html.replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-sm">$1</code>');
  
  // 标题
  html = html.replace(/^######\s+(.+)$/gm, '<h6 class="text-base font-semibold mt-4 mb-2">$1</h6>');
  html = html.replace(/^#####\s+(.+)$/gm, '<h5 class="text-lg font-semibold mt-4 mb-2">$1</h5>');
  html = html.replace(/^####\s+(.+)$/gm, '<h4 class="text-xl font-semibold mt-5 mb-2">$1</h4>');
  html = html.replace(/^###\s+(.+)$/gm, '<h3 class="text-2xl font-semibold mt-6 mb-3">$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2 class="text-3xl font-bold mt-8 mb-4 border-b pb-2">$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h1 class="text-4xl font-bold mt-8 mb-4">$1</h1>');
  
  // 粗体和斜体
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // 删除线
  html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');
  
  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary hover:underline" target="_blank" rel="noopener">$1</a>');
  
  // 图片
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full rounded-lg my-4" />');
  
  // 水平线
  html = html.replace(/^---+$/gm, '<hr class="my-6 border-border" />');
  html = html.replace(/^\*\*\*+$/gm, '<hr class="my-6 border-border" />');
  
  // 引用块
  html = html.replace(/^>\s+(.+)$/gm, '<blockquote class="border-l-4 border-primary/30 pl-4 my-4 text-muted-foreground italic">$1</blockquote>');
  
  // 无序列表
  html = html.replace(/^[\*\-]\s+(.+)$/gm, '<li class="ml-4">$1</li>');
  html = html.replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="list-disc list-inside my-4 space-y-1">$&</ul>');
  
  // 有序列表
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li class="ml-4">$1</li>');
  
  // 任务列表
  html = html.replace(/^[\*\-]\s+\[x\]\s+(.+)$/gim, '<li class="ml-4 flex items-center gap-2"><input type="checkbox" checked disabled class="rounded" /><span>$1</span></li>');
  html = html.replace(/^[\*\-]\s+\[\s*\]\s+(.+)$/gim, '<li class="ml-4 flex items-center gap-2"><input type="checkbox" disabled class="rounded" /><span>$1</span></li>');
  
  // 段落
  html = html.replace(/\n\n+/g, '</p><p class="my-4">');
  html = '<p class="my-4">' + html + '</p>';
  
  // 清理空段落
  html = html.replace(/<p class="my-4">\s*<\/p>/g, '');
  
  // 换行
  html = html.replace(/\n/g, '<br />');
  
  return html;
}

// 保存
async function handleSave() {
  if (!isModified.value || isSaving.value) return;
  
  isSaving.value = true;
  try {
    emit('save', editContent.value);
    // 等待父组件保存完成后会更新 content prop
  } finally {
    isSaving.value = false;
  }
}

// 复制内容
async function copyContent() {
  try {
    await navigator.clipboard.writeText(editContent.value);
  } catch (e) {
    console.error('Failed to copy:', e);
  }
}

// ============ 拖拽分栏功能 ============

// 开始拖拽
function startResize(e: MouseEvent) {
  isResizing.value = true;
  startX.value = e.clientX;
  startWidth.value = leftPanelWidth.value;
  
  // 添加全局事件监听
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
  
  // 禁止文本选择
  document.body.style.userSelect = 'none';
  document.body.style.cursor = 'col-resize';
}

// 拖拽中
function handleResize(e: MouseEvent) {
  if (!isResizing.value || !containerRef.value) return;
  
  const containerWidth = containerRef.value.offsetWidth;
  const deltaX = e.clientX - startX.value;
  const deltaPercent = (deltaX / containerWidth) * 100;
  
  // 计算新宽度，限制在 20% - 80% 之间
  let newWidth = startWidth.value + deltaPercent;
  newWidth = Math.max(20, Math.min(80, newWidth));
  
  leftPanelWidth.value = newWidth;
}

// 停止拖拽
function stopResize() {
  isResizing.value = false;
  
  // 移除全局事件监听
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
  
  // 恢复文本选择
  document.body.style.userSelect = '';
  document.body.style.cursor = '';
}

// 更新原始内容（当保存成功后由父组件更新 content prop）
function updateOriginalContent() {
  originalContent.value = editContent.value;
}

// 监听 content 变化
watch(() => props.content, (newContent) => {
  if (newContent !== undefined) {
    editContent.value = newContent;
    originalContent.value = newContent;
  }
}, { immediate: true });

// 监听 editContent 变化，通知父组件
watch(editContent, (newContent) => {
  emit('change', newContent);
});

// 暴露方法给父组件
defineExpose({
  updateOriginalContent,
});

onMounted(() => {
  // 初始化
});

onUnmounted(() => {
  // 清理事件监听
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
});
</script>

<style scoped>
.prose :deep(pre) {
  margin: 1rem 0;
}

.prose :deep(code) {
  font-family: 'Fira Code', 'Monaco', 'Menlo', monospace;
}

.prose :deep(ul) {
  list-style-type: disc;
}

.prose :deep(ol) {
  list-style-type: decimal;
}

.prose :deep(blockquote) {
  margin: 1rem 0;
}

/* 可拖拽分隔条样式 */
.resizer {
  width: 6px;
  background: transparent;
  cursor: col-resize;
  position: relative;
  flex-shrink: 0;
  transition: background-color 0.2s;
}

.resizer:hover,
.resizer.resizing {
  background: hsl(var(--primary) / 0.1);
}

.resizer-handle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 40px;
  background: hsl(var(--border));
  border-radius: 2px;
  transition: background-color 0.2s, height 0.2s;
}

.resizer:hover .resizer-handle,
.resizer.resizing .resizer-handle {
  background: hsl(var(--primary));
  height: 60px;
}
</style>
