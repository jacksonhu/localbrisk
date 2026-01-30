<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[400px] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-lg font-semibold text-foreground">{{ t('about.title') }}</h2>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 内容区域 -->
          <div class="p-6 text-center">
            <!-- Logo -->
            <div class="flex justify-center mb-4">
              <img :src="logoUrl" alt="LocalBrisk" class="w-20 h-20" />
            </div>
            
            <!-- 应用名称 -->
            <h3 class="text-xl font-bold text-foreground mb-2">LocalBrisk</h3>
            
            <!-- 版本号 -->
            <p class="text-sm text-muted-foreground mb-4">v{{ version }}</p>
            
            <!-- 描述 -->
            <p class="text-sm text-muted-foreground mb-6">
              {{ t('about.description') }}
            </p>
            
            <!-- 分隔线 -->
            <div class="border-t border-border my-4"></div>
            
            <!-- 版权信息 -->
            <p class="text-xs text-muted-foreground">
              {{ t('about.copyright', { year: currentYear }) }}
            </p>
            
            <!-- 链接 -->
            <div class="flex justify-center gap-4 mt-4">
              <a
                href="https://github.com/localbrisk/localbrisk"
                target="_blank"
                class="text-sm text-primary hover:underline flex items-center gap-1"
              >
                <Github class="w-4 h-4" />
                GitHub
              </a>
              <a
                href="https://github.com/localbrisk/localbrisk/issues"
                target="_blank"
                class="text-sm text-primary hover:underline flex items-center gap-1"
              >
                <Bug class="w-4 h-4" />
                {{ t('about.feedback') }}
              </a>
            </div>
          </div>
          
          <!-- 底部按钮 -->
          <div class="flex items-center justify-center px-6 py-4 border-t border-border bg-muted/30">
            <button
              @click="close"
              class="px-6 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              {{ t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { X, Github, Bug } from 'lucide-vue-next';
import logoSvg from '@/assets/logo.svg';

const { t } = useI18n();

// Logo URL
const logoUrl = logoSvg;

// Props
defineProps<{
  isOpen: boolean;
  version?: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
}>();

// 当前年份
const currentYear = computed(() => new Date().getFullYear());

// 关闭弹窗
function close() {
  emit('close');
}
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
