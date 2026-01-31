<!--
  AboutDialog - 关于弹窗
  使用 BaseDialog 基础组件
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('about.title')"
    width="sm"
    :show-close-button="true"
    @close="close"
  >
    <div class="text-center py-4">
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
      <div class="border-t border-border my-4" />
      
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

    <template #footer>
      <button
        @click="close"
        class="px-6 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
      >
        {{ t('common.close') }}
      </button>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Github, Bug } from 'lucide-vue-next';
import logoSvg from '@/assets/logo.svg';
import BaseDialog from '@/components/common/BaseDialog.vue';

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
