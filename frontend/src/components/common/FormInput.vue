<!-- 
  FormInput - 表单输入框组件
  统一输入框样式和行为
-->
<template>
  <input
    :value="modelValue"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :maxlength="maxlength"
    class="w-full px-3 py-2 text-sm bg-background border border-input rounded-lg 
           focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary 
           disabled:opacity-50 disabled:cursor-not-allowed
           placeholder:text-muted-foreground
           transition-colors"
    :class="[sizeClass, { 'pr-10': $slots.suffix }]"
    @input="handleInput"
    @blur="$emit('blur', $event)"
    @focus="$emit('focus', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  modelValue?: string;
  type?: 'text' | 'password' | 'email' | 'number' | 'url';
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  maxlength?: number;
  size?: 'sm' | 'md' | 'lg';
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  type: 'text',
  placeholder: '',
  disabled: false,
  readonly: false,
  maxlength: undefined,
  size: 'md',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'blur', event: FocusEvent): void;
  (e: 'focus', event: FocusEvent): void;
}>();

const sizeClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'h-8 text-xs',
    md: 'h-10 text-sm',
    lg: 'h-12 text-base',
  };
  return sizeMap[props.size] || sizeMap.md;
});

function handleInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
}
</script>
