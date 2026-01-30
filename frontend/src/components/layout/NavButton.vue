<template>
  <button
    class="nav-button w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-150"
    :class="{ active: active }"
    :title="label"
  >
    <component :is="iconComponent" class="w-5 h-5" />
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Folder, User } from "lucide-vue-next";

const props = defineProps<{
  icon: string;
  label: string;
  active?: boolean;
}>();

const iconMap: Record<string, any> = {
  folder: Folder,
  user: User,
};

const iconComponent = computed(() => iconMap[props.icon] || Folder);
</script>

<style scoped>
.nav-button {
  color: #64748B;
}

.nav-button:hover {
  background-color: #F1F5F9;
  color: #333333;
}

.nav-button.active {
  background-color: #EBF5FF;
  color: #2563EB;
}
</style>
