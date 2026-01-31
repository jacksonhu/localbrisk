<!-- 
  FormField - 表单字段包装组件
  统一表单字段的标签、错误提示、帮助文本样式
  
  使用方式：
  <FormField
    label="名称"
    :error="errors.name"
    required
    hint="只能包含字母、数字、下划线"
  >
    <input v-model="form.name" class="input-base" />
  </FormField>
-->
<template>
  <div class="space-y-1.5">
    <!-- 标签行 -->
    <label v-if="label" class="block text-sm font-medium text-foreground">
      {{ label }}
      <span v-if="required" class="text-red-500 ml-0.5">*</span>
      <span v-if="optional" class="text-muted-foreground text-xs ml-1.5">
        ({{ optionalText || t('common.optional') }})
      </span>
    </label>
    
    <!-- 输入区域 -->
    <div :class="{ 'has-error': !!error }">
      <slot />
    </div>
    
    <!-- 错误/提示信息 -->
    <p v-if="error" class="text-xs text-red-500 flex items-center gap-1">
      <AlertCircle class="w-3 h-3" />
      {{ error }}
    </p>
    <p v-else-if="hint" class="text-xs text-muted-foreground">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { AlertCircle } from 'lucide-vue-next';

const { t } = useI18n();

interface Props {
  /** 字段标签 */
  label?: string;
  /** 是否必填 */
  required?: boolean;
  /** 是否可选（显示可选标记） */
  optional?: boolean;
  /** 可选文本 */
  optionalText?: string;
  /** 错误信息 */
  error?: string;
  /** 提示信息 */
  hint?: string;
}

withDefaults(defineProps<Props>(), {
  label: '',
  required: false,
  optional: false,
  optionalText: '',
  error: '',
  hint: '',
});
</script>

<style scoped>
/* 错误状态下的输入框样式 */
.has-error :deep(input),
.has-error :deep(textarea),
.has-error :deep(select) {
  border-color: theme('colors.red.500') !important;
}
</style>
