<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">{{ t('viewer.language') }}:</span>
        <span class="text-sm font-medium">{{ displayLanguage }}</span>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="toggleLineNumbers"
          class="px-2 py-1 text-xs rounded hover:bg-muted transition-colors"
          :class="showLineNumbers ? 'bg-primary/10 text-primary' : ''"
        >
          {{ t('viewer.lineNumbers') }}
        </button>
        <button
          @click="toggleWordWrap"
          class="px-2 py-1 text-xs rounded hover:bg-muted transition-colors"
          :class="wordWrap ? 'bg-primary/10 text-primary' : ''"
        >
          {{ t('viewer.wordWrap') }}
        </button>
        <button
          @click="copyContent"
          class="px-2 py-1 text-xs rounded hover:bg-muted transition-colors flex items-center gap-1"
        >
          <Copy class="w-3 h-3" />
          {{ t('common.copy') }}
        </button>
      </div>
    </div>
    
    <!-- 代码内容 -->
    <div class="flex-1 overflow-auto">
      <div class="min-h-full">
        <pre 
          class="h-full m-0 p-4 font-mono text-sm leading-relaxed"
          :class="wordWrap ? 'whitespace-pre-wrap break-all' : 'whitespace-pre'"
        ><code ref="codeRef" :class="`language-${language}`">{{ textContent }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { Copy } from 'lucide-vue-next';

const { t } = useI18n();

const props = defineProps<{
  content?: string | ArrayBuffer | null;
  fileName: string;
  language?: string;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
}>();

// Refs
const codeRef = ref<HTMLElement | null>(null);

// 状态
const showLineNumbers = ref(true);
const wordWrap = ref(false);

// 语言显示名称
const LANGUAGE_NAMES: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  java: 'Java',
  go: 'Go',
  rust: 'Rust',
  c: 'C',
  cpp: 'C++',
  csharp: 'C#',
  ruby: 'Ruby',
  php: 'PHP',
  swift: 'Swift',
  kotlin: 'Kotlin',
  scala: 'Scala',
  sql: 'SQL',
  shell: 'Shell',
  powershell: 'PowerShell',
  html: 'HTML',
  css: 'CSS',
  scss: 'SCSS',
  less: 'LESS',
  json: 'JSON',
  yaml: 'YAML',
  xml: 'XML',
  toml: 'TOML',
  ini: 'INI',
  markdown: 'Markdown',
  plaintext: 'Plain Text',
  vue: 'Vue',
};

// 显示语言名称
const displayLanguage = computed(() => {
  return LANGUAGE_NAMES[props.language || 'plaintext'] || props.language || 'Plain Text';
});

// 文本内容
const textContent = computed(() => {
  if (!props.content) return '';
  
  if (typeof props.content === 'string') {
    return props.content;
  }
  
  // ArrayBuffer 转字符串
  try {
    const decoder = new TextDecoder('utf-8');
    return decoder.decode(props.content);
  } catch {
    emit('error', 'Failed to decode file content');
    return '';
  }
});

// 带行号的内容（预留功能）
const contentWithLineNumbers = computed(() => {
  if (!showLineNumbers.value) return textContent.value;
  
  const lines = textContent.value.split('\n');
  const maxLineNum = lines.length;
  const padWidth = String(maxLineNum).length;
  
  return lines.map((line, i) => {
    const lineNum = String(i + 1).padStart(padWidth, ' ');
    return `${lineNum} │ ${line}`;
  }).join('\n');
});

// 导出供外部使用（避免未使用警告）
defineExpose({
  contentWithLineNumbers
});

// 切换行号
function toggleLineNumbers() {
  showLineNumbers.value = !showLineNumbers.value;
}

// 切换换行
function toggleWordWrap() {
  wordWrap.value = !wordWrap.value;
}

// 复制内容
async function copyContent() {
  try {
    await navigator.clipboard.writeText(textContent.value);
    // TODO: 显示复制成功提示
  } catch (e) {
    console.error('Failed to copy:', e);
  }
}

// 应用语法高亮（如果有 Prism.js）
async function applyHighlight() {
  await nextTick();
  if (codeRef.value && typeof window !== 'undefined' && 'Prism' in window) {
    (window as unknown as { Prism: { highlightElement: (el: HTMLElement) => void } }).Prism.highlightElement(codeRef.value);
  }
}

watch(() => props.content, () => {
  applyHighlight();
});

onMounted(() => {
  applyHighlight();
});
</script>

<style scoped>
pre {
  background-color: var(--muted);
  color: var(--foreground);
}

code {
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}
</style>
