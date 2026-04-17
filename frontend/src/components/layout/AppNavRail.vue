<template>
  <aside class="w-14 bg-card border-r border-border flex flex-col items-center py-4 gap-2">
    <NavButton
      v-for="item in navItems"
      :key="item.id"
      :icon="item.icon"
      :label="item.label"
      :active="activeNav === item.id"
      @click="handleNavClick(item.routeName)"
    />
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import NavButton from "@/components/layout/NavButton.vue";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const navItems = computed(() => [
  { id: "catalog", icon: "folder", label: t("nav.catalog"), routeName: "home" },
  { id: "foreman", icon: "user", label: t("nav.foreman"), routeName: "foreman" },
]);

const activeNav = computed(() => (route.name === "foreman" ? "foreman" : "catalog"));

function handleNavClick(routeName: string): void {
  router.push({ name: routeName });
}
</script>
