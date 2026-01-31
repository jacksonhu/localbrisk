<template>
  <div class="config-editor card-float h-full flex flex-col">
    <!-- 标题栏 -->
    <div class="p-4 border-b border-border flex items-center justify-between">
      <h3 class="font-medium flex items-center gap-2">
        <FileCode class="w-4 h-4" />
        {{ title || t('detail.configFile') }}
      </h3>
      <div class="flex items-center gap-2">
        <!-- 格式化按钮 -->
        <button
          @click="formatYaml"
          :disabled="!content || hasError"
          class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          :title="t('config.format')"
        >
          <Sparkles class="w-4 h-4" />
          {{ t('config.format') }}
        </button>
        <!-- 保存按钮 -->
        <button
          @click="handleSave"
          :disabled="!modified || saving || hasError"
          class="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
          <Save v-else class="w-4 h-4" />
          {{ t('common.save') }}
        </button>
        <!-- 复制按钮 -->
        <button
          @click="handleCopy"
          class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2"
        >
          <Copy class="w-4 h-4" />
          {{ t('common.copy') }}
        </button>
      </div>
    </div>
    
    <!-- 编辑器容器 -->
    <div class="flex-1 overflow-hidden relative">
      <div ref="editorContainer" class="w-full h-full"></div>
      
      <!-- YAML 错误提示 -->
      <div 
        v-if="hasError" 
        class="absolute bottom-0 left-0 right-0 bg-red-50 dark:bg-red-950/50 border-t border-red-200 dark:border-red-800 p-3 flex items-start gap-2"
      >
        <AlertCircle class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
        <div class="text-sm">
          <span class="font-medium text-red-600 dark:text-red-400">{{ t('config.yamlError') }}:</span>
          <span class="text-red-600/80 dark:text-red-400/80 ml-1">{{ errorMessage }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { FileCode, Save, Copy, Sparkles, Loader2, AlertCircle } from "lucide-vue-next";
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLine } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { defaultHighlightStyle, syntaxHighlighting, indentOnInput, bracketMatching, foldGutter, foldKeymap } from "@codemirror/language";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { lintKeymap } from "@codemirror/lint";
import { yaml } from "@codemirror/lang-yaml";
import * as jsYaml from "js-yaml";
import { useToast } from "@/composables/useToast";

const props = defineProps<{
  modelValue: string;
  title?: string;
  modified?: boolean;
  saving?: boolean;
  readonly?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'save'): void;
  (e: 'copy'): void;
}>();

const { t } = useI18n();
const toast = useToast();

// 编辑器相关
const editorContainer = ref<HTMLElement | null>(null);
const editorView = ref<EditorView | null>(null);
const themeCompartment = new Compartment();
const readonlyCompartment = new Compartment();

// 内容和状态
const content = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const modified = computed(() => props.modified ?? false);
const saving = computed(() => props.saving ?? false);

// YAML 校验
const hasError = ref(false);
const errorMessage = ref('');

// 校验 YAML 格式
function validateYaml(value: string): boolean {
  if (!value.trim()) {
    hasError.value = false;
    errorMessage.value = '';
    return true;
  }
  
  try {
    jsYaml.load(value);
    hasError.value = false;
    errorMessage.value = '';
    return true;
  } catch (e: any) {
    hasError.value = true;
    errorMessage.value = e.message || 'Invalid YAML format';
    return false;
  }
}

// 格式化 YAML
function formatYaml() {
  if (!content.value.trim()) return;
  
  try {
    const parsed = jsYaml.load(content.value);
    const formatted = jsYaml.dump(parsed, {
      indent: 2,
      lineWidth: 120,
      noRefs: true,
      sortKeys: false,
      quotingType: '"',
      forceQuotes: false
    });
    content.value = formatted;
    updateEditorContent(formatted);
    toast.showSuccess(t('config.formatted'));
  } catch (e: any) {
    toast.showError(t('config.formatFailed') + ': ' + e.message);
  }
}

// 保存
function handleSave() {
  if (hasError.value) {
    toast.showError(t('config.invalidYamlFormat'));
    return;
  }
  emit('save');
}

// 复制
async function handleCopy() {
  try {
    await navigator.clipboard.writeText(content.value);
    emit('copy');
  } catch (e) {
    console.error('Failed to copy:', e);
    toast.showError(t('config.copyFailed'));
  }
}

// 更新编辑器内容
function updateEditorContent(value: string) {
  if (!editorView.value) return;
  
  const currentValue = editorView.value.state.doc.toString();
  if (currentValue !== value) {
    editorView.value.dispatch({
      changes: {
        from: 0,
        to: currentValue.length,
        insert: value
      }
    });
  }
}

// 获取主题扩展
function getThemeExtension(isDark: boolean) {
  const baseTheme = EditorView.theme({
    '&': {
      height: '100%',
      fontSize: '13px',
    },
    '.cm-content': {
      fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
      padding: '16px 0',
    },
    '.cm-gutters': {
      backgroundColor: 'transparent',
      borderRight: 'none',
      paddingRight: '8px',
    },
    '.cm-lineNumbers .cm-gutterElement': {
      padding: '0 8px 0 16px',
      minWidth: '40px',
    },
    '.cm-activeLine': {
      backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'transparent',
    },
    '.cm-selectionBackground': {
      backgroundColor: isDark ? 'rgba(100,149,237,0.3)' : 'rgba(100,149,237,0.2)',
    },
    '&.cm-focused .cm-selectionBackground': {
      backgroundColor: isDark ? 'rgba(100,149,237,0.4)' : 'rgba(100,149,237,0.3)',
    },
    '.cm-cursor': {
      borderLeftColor: isDark ? '#fff' : '#000',
    },
    '.cm-foldGutter .cm-gutterElement': {
      padding: '0 4px',
    }
  });
  
  // 暗色主题高亮
  const darkHighlight = EditorView.theme({
    '.cm-content': {
      color: '#e0e0e0',
    },
    '.cm-line': {
      color: '#e0e0e0',
    },
    // YAML 语法高亮
    '.ͼ1.ͼ5': { color: '#7dd3fc' }, // key
    '.ͼ1.ͼ7': { color: '#86efac' }, // string
    '.ͼ1.ͼ8': { color: '#fca5a5' }, // number
    '.ͼ1.ͼb': { color: '#c4b5fd' }, // keyword (true/false/null)
    '.ͼ1.ͼd': { color: '#94a3b8' }, // comment
    '.ͼ1.ͼe': { color: '#fcd34d' }, // property name
  }, { dark: true });
  
  // 亮色主题高亮
  const lightHighlight = EditorView.theme({
    '.cm-content': {
      color: '#1f2937',
    },
    '.cm-line': {
      color: '#1f2937',
    },
    '.cm-gutters': {
      color: '#9ca3af',
    },
    // YAML 语法高亮
    '.ͼ1.ͼ5': { color: '#0369a1' }, // key
    '.ͼ1.ͼ7': { color: '#16a34a' }, // string
    '.ͼ1.ͼ8': { color: '#dc2626' }, // number
    '.ͼ1.ͼb': { color: '#7c3aed' }, // keyword (true/false/null)
    '.ͼ1.ͼd': { color: '#6b7280' }, // comment
    '.ͼ1.ͼe': { color: '#d97706' }, // property name
  }, { dark: false });
  
  return isDark ? [baseTheme, darkHighlight] : [baseTheme, lightHighlight];
}

// 检测主题
function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

// 初始化编辑器
function initEditor() {
  if (!editorContainer.value) return;
  
  const isDark = isDarkMode();
  
  const state = EditorState.create({
    doc: content.value,
    extensions: [
      // 基础配置
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightSpecialChars(),
      history(),
      foldGutter(),
      drawSelection(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
      indentOnInput(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      rectangularSelection(),
      crosshairCursor(),
      highlightActiveLine(),
      highlightSelectionMatches(),
      
      // 键盘映射
      keymap.of([
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        ...lintKeymap,
        indentWithTab,
        // Ctrl+S 保存
        { key: 'Mod-s', run: () => { handleSave(); return true; } },
        // Ctrl+Shift+F 格式化
        { key: 'Mod-Shift-f', run: () => { formatYaml(); return true; } },
      ]),
      
      // YAML 语言支持
      yaml(),
      
      // 主题
      themeCompartment.of(getThemeExtension(isDark)),
      
      // 只读模式
      readonlyCompartment.of(EditorState.readOnly.of(props.readonly ?? false)),
      
      // 内容变化监听
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newValue = update.state.doc.toString();
          emit('update:modelValue', newValue);
          validateYaml(newValue);
        }
      }),
    ],
  });
  
  editorView.value = new EditorView({
    state,
    parent: editorContainer.value,
  });
}

// 监听主题变化
let themeObserver: MutationObserver | null = null;

function setupThemeObserver() {
  themeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'class' && editorView.value) {
        const isDark = isDarkMode();
        editorView.value.dispatch({
          effects: themeCompartment.reconfigure(getThemeExtension(isDark))
        });
      }
    });
  });
  
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class']
  });
}

// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  if (editorView.value) {
    const currentValue = editorView.value.state.doc.toString();
    if (currentValue !== newValue) {
      updateEditorContent(newValue);
      validateYaml(newValue);
    }
  }
});

// 监听只读状态变化
watch(() => props.readonly, (newValue) => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: readonlyCompartment.reconfigure(EditorState.readOnly.of(newValue ?? false))
    });
  }
});

onMounted(async () => {
  await nextTick();
  initEditor();
  setupThemeObserver();
  // 初始校验
  validateYaml(content.value);
});

onUnmounted(() => {
  if (editorView.value) {
    editorView.value.destroy();
    editorView.value = null;
  }
  if (themeObserver) {
    themeObserver.disconnect();
    themeObserver = null;
  }
});
</script>

<style scoped>
.config-editor {
  min-height: 300px;
}

.config-editor :deep(.cm-editor) {
  height: 100%;
  outline: none;
}

.config-editor :deep(.cm-scroller) {
  overflow: auto;
}
</style>
