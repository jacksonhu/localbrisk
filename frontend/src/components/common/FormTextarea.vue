<!-- 
  FormTextarea - 表单文本域组件
  统一文本域样式和行为
-->
<template>
  <textarea
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :maxlength="maxlength"
    :rows="rows"
    class="w-full px-3 py-2 text-sm bg-background border border-input rounded-lg resize-none
           focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary 
           disabled:opacity-50 disabled:cursor-not-allowed
           placeholder:text-muted-foreground
           transition-colors"
    @input="handleInput"
    @blur="$emit('blur', $event)"
    @focus="$emit('focus', $event)"
  />
</template>

<script setup lang="ts">
interface Props {
  modelValue?: string;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  maxlength?: number;
  rows?: number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '',
  disabled: false,
  readonly: false,
  maxlength: undefined,
  rows: 3,
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'blur', event: FocusEvent): void;
  (e: 'focus', event: FocusEvent): void;
}>();

function handleInput(event: Event): void {
  const target = event.target as HTMLTextAreaElement;
  emit('update:modelValue', target.value);
}
</script>
