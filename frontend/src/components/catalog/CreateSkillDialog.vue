<!--
  CreateSkillDialog - 创建 Skill 弹窗
  支持三种创建方式：
  1. 本地 zip 包导入（使用 Tauri 原生文件选择器）
  2. 从开放市场导入（预留）
  3. AI 辅助创建（预留）
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('skill.create')"
    :icon="Code"
    width="md"
    @close="close"
  >
    <!-- 步骤 1：选择创建方式 -->
    <div v-if="step === 'select'" class="space-y-4">
      <p class="text-sm text-muted-foreground mb-4">{{ t('skill.selectMethodHint') }}</p>
      
      <!-- 创建方式选项 -->
      <div class="space-y-3">
        <!-- 本地 zip 包导入 -->
        <div
          @click="selectMethod('local')"
          class="flex items-start gap-4 p-4 border border-border rounded-lg cursor-pointer transition-all"
          :class="selectedMethod === 'local' 
            ? 'border-primary bg-primary/5' 
            : 'hover:border-primary/50 hover:bg-muted/30'"
        >
          <div class="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
            <Upload class="w-5 h-5 text-purple-500" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <h4 class="font-medium">{{ t('skill.methodLocal') }}</h4>
              <span class="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded">{{ t('common.available') }}</span>
            </div>
            <p class="text-sm text-muted-foreground mt-1">{{ t('skill.methodLocalDesc') }}</p>
          </div>
          <div v-if="selectedMethod === 'local'" class="flex-shrink-0">
            <Check class="w-5 h-5 text-primary" />
          </div>
        </div>

        <!-- 从开放市场导入 -->
        <div
          @click="selectMethod('marketplace')"
          class="flex items-start gap-4 p-4 border border-border rounded-lg cursor-pointer transition-all opacity-60"
          :class="selectedMethod === 'marketplace'
            ? 'border-primary bg-primary/5'
            : 'hover:border-primary/50 hover:bg-muted/30'"
        >
          <div class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
            <ShoppingBag class="w-5 h-5 text-blue-500" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <h4 class="font-medium">{{ t('skill.methodMarketplace') }}</h4>
              <span class="text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded">{{ t('common.comingSoon') }}</span>
            </div>
            <p class="text-sm text-muted-foreground mt-1">{{ t('skill.methodMarketplaceDesc') }}</p>
          </div>
        </div>

        <!-- AI 辅助创建 -->
        <div
          @click="selectMethod('ai')"
          class="flex items-start gap-4 p-4 border border-border rounded-lg cursor-pointer transition-all opacity-60"
          :class="selectedMethod === 'ai'
            ? 'border-primary bg-primary/5'
            : 'hover:border-primary/50 hover:bg-muted/30'"
        >
          <div class="w-10 h-10 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0">
            <Sparkles class="w-5 h-5 text-orange-500" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <h4 class="font-medium">{{ t('skill.methodAI') }}</h4>
              <span class="text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded">{{ t('common.comingSoon') }}</span>
            </div>
            <p class="text-sm text-muted-foreground mt-1">{{ t('skill.methodAIDesc') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 步骤 2：本地 zip 导入 -->
    <div v-if="step === 'local'" class="space-y-5">
      <!-- 返回按钮 -->
      <button
        @click="step = 'select'"
        class="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft class="w-4 h-4" />
        {{ t('common.back') }}
      </button>

      <!-- 文件选择区域 -->
      <div class="space-y-3">
        <label class="block text-sm font-medium">{{ t('skill.selectZipFile') }}</label>
        
        <!-- 点击选择文件区域 -->
        <div
          @click="handleSelectZipFile"
          class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all"
          :class="'border-border hover:border-primary/50 hover:bg-muted/30'"
        >
          <div v-if="!selectedFilePath" class="space-y-3">
            <Upload class="w-10 h-10 text-muted-foreground mx-auto" />
            <div>
              <p class="text-sm font-medium">{{ t('skill.clickToSelect') }}</p>
              <p class="text-xs text-muted-foreground mt-1">{{ t('skill.zipFileOnly') }}</p>
            </div>
          </div>
          
          <div v-else class="space-y-3">
            <FileArchive class="w-10 h-10 text-purple-500 mx-auto" />
            <div>
              <p class="text-sm font-medium">{{ selectedFileName }}</p>
              <p class="text-xs text-muted-foreground mt-1 break-all">{{ selectedFilePath }}</p>
            </div>
            <button
              @click.stop="clearFile"
              class="text-xs text-red-500 hover:text-red-600 transition-colors"
            >
              {{ t('common.remove') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 提示信息 -->
      <div class="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-900">
        <div class="flex gap-2">
          <Info class="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div class="text-xs text-blue-700 dark:text-blue-300 space-y-1">
            <p>{{ t('skill.zipHint1') }}</p>
            <p>{{ t('skill.zipHint2') }}</p>
          </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="p-3 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-900">
        <div class="flex gap-2">
          <AlertCircle class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p class="text-xs text-red-700 dark:text-red-300">{{ errorMessage }}</p>
        </div>
      </div>
    </div>

    <!-- 步骤 2：开放市场导入（预留） -->
    <div v-if="step === 'marketplace'" class="space-y-5">
      <button
        @click="step = 'select'"
        class="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft class="w-4 h-4" />
        {{ t('common.back') }}
      </button>
      
      <div class="flex flex-col items-center justify-center py-8 text-center">
        <ShoppingBag class="w-12 h-12 text-muted-foreground/30 mb-4" />
        <h3 class="text-lg font-medium mb-2">{{ t('skill.methodMarketplace') }}</h3>
        <p class="text-muted-foreground text-sm">{{ t('common.comingSoonDesc') }}</p>
      </div>
    </div>

    <!-- 步骤 2：AI 辅助创建（预留） -->
    <div v-if="step === 'ai'" class="space-y-5">
      <button
        @click="step = 'select'"
        class="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft class="w-4 h-4" />
        {{ t('common.back') }}
      </button>
      
      <div class="flex flex-col items-center justify-center py-8 text-center">
        <Sparkles class="w-12 h-12 text-muted-foreground/30 mb-4" />
        <h3 class="text-lg font-medium mb-2">{{ t('skill.methodAI') }}</h3>
        <p class="text-muted-foreground text-sm">{{ t('common.comingSoonDesc') }}</p>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="flex justify-end gap-3">
        <button
          @click="close"
          class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
        >
          {{ t('common.cancel') }}
        </button>
        
        <!-- 步骤 1 的下一步按钮 -->
        <button
          v-if="step === 'select'"
          @click="goToNextStep"
          :disabled="!selectedMethod || selectedMethod !== 'local'"
          class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ t('common.next') }}
        </button>
        
        <!-- 步骤 2（本地导入）的确认按钮 -->
        <button
          v-if="step === 'local'"
          @click="handleSubmit"
          :disabled="!selectedFilePath || isSubmitting"
          class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
          {{ t('common.confirm') }}
        </button>
      </div>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { 
  Code, Upload, ShoppingBag, Sparkles, Check, ArrowLeft, 
  Info, FileArchive, AlertCircle, Loader2 
} from 'lucide-vue-next';
import { BaseDialog } from '@/components/common';

const { t } = useI18n();

// 检测是否在 Tauri 环境中
const isTauriEnv = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

// Props
const props = defineProps<{
  isOpen: boolean;
  businessUnitId: string;
  agentName: string;
  onSubmit?: (businessUnitId: string, agentName: string, zipFilePath: string) => Promise<void>;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
}>();

// 步骤状态
type Step = 'select' | 'local' | 'marketplace' | 'ai';
const step = ref<Step>('select');

// 创建方式
type Method = 'local' | 'marketplace' | 'ai';
const selectedMethod = ref<Method | null>(null);

// 文件相关 - 只保存路径，不需要 File 对象
const selectedFilePath = ref<string | null>(null);
const errorMessage = ref('');
const isSubmitting = ref(false);

// 计算文件名（从路径中提取）
const selectedFileName = computed(() => {
  if (!selectedFilePath.value) return '';
  // 处理 Windows 和 Unix 路径
  const parts = selectedFilePath.value.split(/[/\\]/);
  return parts[parts.length - 1];
});

// 选择创建方式
function selectMethod(method: Method) {
  // 只允许选择 local，其他方式暂不可用
  if (method === 'local') {
    selectedMethod.value = method;
  }
}

// 进入下一步
function goToNextStep() {
  if (selectedMethod.value === 'local') {
    step.value = 'local';
  } else if (selectedMethod.value === 'marketplace') {
    step.value = 'marketplace';
  } else if (selectedMethod.value === 'ai') {
    step.value = 'ai';
  }
}

// 使用 Tauri 原生对话框选择 zip 文件
async function handleSelectZipFile() {
  if (!isTauriEnv) {
    errorMessage.value = t('skill.errorNotInTauri');
    console.warn('File picker is only available in Tauri app.');
    return;
  }
  
  try {
    const { open } = await import('@tauri-apps/plugin-dialog');
    const selected = await open({
      multiple: false,
      directory: false,
      filters: [
        {
          name: 'ZIP Files',
          extensions: ['zip'],
        },
      ],
      title: t('skill.selectZipFile'),
    });
    
    if (selected) {
      // 验证文件扩展名
      const path = selected as string;
      if (!path.toLowerCase().endsWith('.zip')) {
        errorMessage.value = t('skill.errorNotZip');
        return;
      }
      
      selectedFilePath.value = path;
      errorMessage.value = '';
    }
  } catch (e) {
    console.error('Failed to select file:', e);
    errorMessage.value = t('errors.createSkillFailed');
  }
}

// 清除文件
function clearFile() {
  selectedFilePath.value = null;
  errorMessage.value = '';
}

// 关闭弹窗
function close() {
  emit('close');
}

// 提交
async function handleSubmit() {
  if (!selectedFilePath.value || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = '';
  
  try {
    if (props.onSubmit) {
      await props.onSubmit(props.businessUnitId, props.agentName, selectedFilePath.value);
    }
    // 成功后关闭弹窗
    emit('close');
  } catch (e: any) {
    // 捕获并显示错误信息
    console.error('Failed to import skill:', e);
    errorMessage.value = e.message || t('errors.createSkillFailed');
  } finally {
    isSubmitting.value = false;
  }
}

// 重置状态
function resetState() {
  step.value = 'select';
  selectedMethod.value = null;
  selectedFilePath.value = null;
  errorMessage.value = '';
  isSubmitting.value = false;
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetState();
  }
});
</script>
