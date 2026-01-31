<!-- 
  FormSelect - 表单下拉选择组件
  统一下拉框样式和行为
-->
<template>
  <select
    :value="modelValue"
    :disabled="disabled"
    class="w-full px-3 py-2 text-sm bg-background border border-input rounded-lg 
           focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary 
           disabled:opacity-50 disabled:cursor-not-allowed
           transition-colors appearance-none cursor-pointer"
    :class="sizeClass"
    @change="handleChange"
  >
    <option v-if="placeholder" value="" disabled>
      {{ placeholder }}
    </option>
    <option
      v-for="option in options"
      :key="getOptionValue(option)"
      :value="getOptionValue(option)"
    >
      {{ getOptionLabel(option) }}
    </option>
  </select>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type OptionValue = string | number;

interface OptionObject {
  label: string;
  value: OptionValue;
  disabled?: boolean;
}

type Option = OptionValue | OptionObject;

interface Props {
  modelValue?: OptionValue;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '',
  disabled: false,
  size: 'md',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: OptionValue): void;
}>();

const sizeClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'h-8 text-xs',
    md: 'h-10 text-sm',
    lg: 'h-12 text-base',
  };
  return sizeMap[props.size] || sizeMap.md;
});

function getOptionValue(option: Option): OptionValue {
  if (typeof option === 'object' && option !== null) {
    return option.value;
  }
  return option;
}

function getOptionLabel(option: Option): string {
  if (typeof option === 'object' && option !== null) {
    return option.label;
  }
  return String(option);
}

function handleChange(event: Event): void {
  const target = event.target as HTMLSelectElement;
  emit('update:modelValue', target.value);
}
</script>

<style scoped>
/* 自定义下拉箭头 */
select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2.5rem;
}
</style>
