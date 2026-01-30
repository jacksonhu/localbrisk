<template>
  <div class="home-view h-full flex">
    <!-- 左侧导航栏 -->
    <aside class="w-14 bg-card border-r border-border flex flex-col items-center py-4 gap-2">
      <NavButton
        v-for="item in navItems"
        :key="item.id"
        :icon="item.icon"
        :label="item.label"
        :active="activeNav === item.id"
        @click="activeNav = item.id"
      />
    </aside>

    <!-- Catalog 树形面板 -->
    <aside class="w-64 bg-card border-r border-border flex flex-col">
      <CatalogPanel />
    </aside>

    <!-- 主内容区域 -->
    <main class="flex-1 flex flex-col bg-background overflow-hidden">
      <DetailPanel />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import NavButton from "@/components/layout/NavButton.vue";
import CatalogPanel from "@/components/catalog/CatalogPanel.vue";
import DetailPanel from "@/components/detail/DetailPanel.vue";

const { t } = useI18n();

// 导航项（使用计算属性以支持语言切换）
const navItems = computed(() => [
  { id: "catalog", icon: "folder", label: t('nav.catalog') },
  { id: "foreman", icon: "user", label: t('nav.foreman') },
]);

const activeNav = ref("catalog");
</script>

<style scoped>
.home-view {
  min-height: 0;
}
</style>
