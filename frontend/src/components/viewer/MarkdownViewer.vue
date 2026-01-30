<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
      <div class="flex items-center gap-2">
        <button
          @click="viewMode = 'preview'"
          class="px-3 py-1 text-sm rounded transition-colors"
          :class="viewMode === 'preview' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
        >
          {{ t('viewer.preview') }}
        </button>
        <button
          @click="viewMode = 'source'"
          class="px-3 py-1 text-sm rounded transition-colors"
          :class="viewMode === 'source' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
        >
          {{ t('viewer.source') }}
        </button>
        <button
          @click="viewMode = 'split'"
          class="px-3 py-1 text-sm rounded transition-colors"
          :class="viewMode === 'split' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
        >
          {{ t('viewer.split') }}
        </button>
      </div>
      <button
        @click="copyContent"
        class="px-2 py-1 text-xs rounded hover:bg-muted transition-colors flex items-center gap-1"
      >
        <Copy class="w-3 h-3" />
        {{ t('common.copy') }}
      </button>
    </div>
    
    <!-- 内容区域 -->
    <div class="flex-1 overflow-hidden flex">
      <!-- 源码视图 -->
      <div 
        v-if="viewMode === 'source' || viewMode === 'split'"
        class="flex-1 overflow-auto bg-muted/30"
        :class="viewMode === 'split' ? 'border-r border-border' : ''"
      >
        <pre class="p-4 m-0 font-mono text-sm leading-relaxed whitespace-pre-wrap">{{ textContent }}</pre>
      </div>
      
      <!-- 预览视图 -->
      <div 
        v-if="viewMode === 'preview' || viewMode === 'split'"
        class="flex-1 overflow-auto p-6"
      >
        <div 
          class="prose prose-sm dark:prose-invert max-w-none"
          v-html="renderedHtml"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Copy } from 'lucide-vue-next';

const { t } = useI18n();

const props = defineProps<{
  content?: string | ArrayBuffer | null;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
}>();

// 状态
const viewMode = ref<'preview' | 'source' | 'split'>('preview');

// 文本内容
const textContent = computed(() => {
  if (!props.content) return '';
  
  if (typeof props.content === 'string') {
    return props.content;
  }
  
  try {
    const decoder = new TextDecoder('utf-8');
    return decoder.decode(props.content);
  } catch {
    emit('error', 'Failed to decode file content');
    return '';
  }
});

// 渲染后的 HTML
const renderedHtml = computed(() => {
  return renderMarkdown(textContent.value);
});

// 简单的 Markdown 渲染器
function renderMarkdown(md: string): string {
  if (!md) return '';
  
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

// 复制内容
async function copyContent() {
  try {
    await navigator.clipboard.writeText(textContent.value);
  } catch (e) {
    console.error('Failed to copy:', e);
  }
}

onMounted(() => {
  // 初始化
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
</style>
