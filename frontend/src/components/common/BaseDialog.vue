<!-- 
  BaseDialog - 通用弹窗基础组件
  封装弹窗的通用结构和行为：遮罩、动画、关闭逻辑等
  
  使用方式：
  <BaseDialog
    :is-open="showDialog"
    :title="t('dialog.title')"
    :icon="Settings"
    width="md"
    @close="showDialog = false"
  >
    <template #default>
      弹窗内容
    </template>
    <template #footer>
      <DialogFooter ... />
    </template>
  </BaseDialog>
-->
<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @keydown.esc="handleClose"
      >
        <!-- 背景遮罩 -->
        <div
          class="absolute inset-0 bg-black/50 backdrop-blur-sm"
          @click="closeOnOverlay && handleClose()"
        />
        
        <!-- 弹窗容器 -->
        <div
          class="relative bg-card rounded-xl shadow-float-lg border border-border overflow-hidden"
          :class="[widthClass, maxHeightClass]"
          role="dialog"
          :aria-labelledby="titleId"
          aria-modal="true"
        >
          <!-- 标题栏 -->
          <div
            v-if="title || $slots.header"
            class="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30"
          >
            <slot name="header">
              <div class="flex items-center gap-3">
                <div
                  v-if="icon"
                  class="w-9 h-9 bg-primary/10 rounded-lg flex items-center justify-center"
                >
                  <component :is="icon" class="w-5 h-5 text-primary" />
                </div>
                <h2 :id="titleId" class="text-lg font-semibold text-foreground">
                  {{ title }}
                </h2>
              </div>
            </slot>
            
            <button
              v-if="showCloseButton"
              type="button"
              class="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              :aria-label="t('common.close')"
              @click="handleClose"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
          
          <!-- 内容区域 -->
          <div class="dialog-content" :class="contentClass">
            <slot />
          </div>
          
          <!-- 底部按钮区域 -->
          <div
            v-if="$slots.footer"
            class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30"
          >
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import { X } from 'lucide-vue-next';

const { t } = useI18n();

// Props 定义
interface Props {
  /** 是否显示弹窗 */
  isOpen: boolean;
  /** 弹窗标题 */
  title?: string;
  /** 标题图标 */
  icon?: Component;
  /** 弹窗宽度：sm | md | lg | xl | 2xl | full */
  width?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  /** 是否显示关闭按钮 */
  showCloseButton?: boolean;
  /** 点击遮罩是否关闭 */
  closeOnOverlay?: boolean;
  /** 内容区域是否有内边距 */
  contentPadding?: boolean;
  /** 最大高度 */
  maxHeight?: 'auto' | 'screen';
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  icon: undefined,
  width: 'md',
  showCloseButton: true,
  closeOnOverlay: true,
  contentPadding: true,
  maxHeight: 'auto',
});

// Emits 定义
const emit = defineEmits<{
  (e: 'close'): void;
}>();

// 唯一标题 ID（用于无障碍）
const titleId = `dialog-title-${Math.random().toString(36).slice(2, 9)}`;

// 宽度样式映射
const widthClass = computed(() => {
  const widthMap: Record<string, string> = {
    sm: 'w-full max-w-sm',
    md: 'w-full max-w-md',
    lg: 'w-full max-w-lg',
    xl: 'w-full max-w-xl',
    '2xl': 'w-full max-w-2xl',
    full: 'w-full max-w-[90vw]',
  };
  return widthMap[props.width] || widthMap.md;
});

// 最大高度样式
const maxHeightClass = computed(() => {
  return props.maxHeight === 'screen' ? 'max-h-[90vh] flex flex-col' : '';
});

// 内容区域样式
const contentClass = computed(() => {
  const classes: string[] = [];
  if (props.contentPadding) {
    classes.push('px-6 py-4');
  }
  if (props.maxHeight === 'screen') {
    classes.push('overflow-y-auto flex-1');
  }
  return classes.join(' ');
});

// 关闭弹窗
function handleClose(): void {
  emit('close');
}

// 阻止背景滚动
onMounted(() => {
  if (props.isOpen) {
    document.body.style.overflow = 'hidden';
  }
});

onUnmounted(() => {
  document.body.style.overflow = '';
});

// 监听 isOpen 变化
import { watch } from 'vue';
watch(
  () => props.isOpen,
  (newVal) => {
    document.body.style.overflow = newVal ? 'hidden' : '';
  }
);
</script>

<style scoped>
/* 弹窗动画 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-active .relative,
.dialog-fade-leave-active .relative {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.dialog-fade-enter-from .relative,
.dialog-fade-leave-to .relative {
  transform: scale(0.95);
  opacity: 0;
}
</style>
