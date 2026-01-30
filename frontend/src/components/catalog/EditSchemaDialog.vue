<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[420px] max-h-[80vh] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-lg font-semibold text-foreground">
              {{ t('catalog.editSchema') }}
            </h2>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 表单内容 -->
          <form @submit.prevent="handleSubmit" class="p-6 space-y-5">
            <!-- Schema 名称（只读） -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('catalog.schemaName') }}
              </label>
              <input
                :value="schema?.name"
                type="text"
                disabled
                class="w-full px-3 py-2 bg-muted border border-input rounded-lg text-muted-foreground text-sm cursor-not-allowed"
              />
              <p class="text-xs text-muted-foreground">{{ t('catalog.schemaNameReadonly') }}</p>
            </div>

            <!-- 描述 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('common.description') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <textarea
                v-model="form.description"
                rows="3"
                :placeholder="t('detail.addDescription')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              ></textarea>
            </div>
          </form>
          
          <!-- 底部按钮 -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
            <button
              type="button"
              @click="close"
              class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="handleSubmit"
              :disabled="isSubmitting"
              class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
              {{ t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { X, Loader2 } from 'lucide-vue-next';
import type { Schema, SchemaUpdate } from '@/types/catalog';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
  schema: Schema | null;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, schemaName: string, data: SchemaUpdate): void;
}>();

// 表单状态
const form = reactive<SchemaUpdate>({
  description: '',
});

// 提交状态
const isSubmitting = ref(false);

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  if (isSubmitting.value || !props.schema) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    const data: SchemaUpdate = {};
    
    // 只有当描述发生变化时才提交
    if (form.description !== (props.schema.description || '')) {
      data.description = form.description || undefined;
    }
    
    emit('submit', props.catalogId, props.schema.name, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  if (props.schema) {
    form.description = props.schema.description || '';
  } else {
    form.description = '';
  }
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});

// 监听 schema 变化（深度监听）
watch(() => props.schema, () => {
  if (props.isOpen) {
    resetForm();
  }
}, { deep: true, immediate: true });
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
