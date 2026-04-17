<template>
  <div class="home-view h-full flex">
    <AppNavRail />

    <aside class="w-64 bg-card border-r border-border flex flex-col">
      <CatalogPanel />
    </aside>

    <main class="flex-1 flex flex-col bg-background overflow-hidden">
      <DetailPanel />
    </main>
  </div>
</template>

<script setup lang="ts">
import CatalogPanel from "@/components/catalog/CatalogPanel.vue";
import DetailPanel from "@/components/detail/DetailPanel.vue";
import AppNavRail from "@/components/layout/AppNavRail.vue";
</script>

<style scoped>
.home-view {
  min-height: 0;
}
</style>
