<template>
  <section class="h-full flex flex-col min-h-0 bg-card">
    <div class="px-5 py-4 border-b border-border">
      <div class="mb-4">
        <p class="text-xs uppercase tracking-[0.24em] text-primary font-semibold mb-1">
          {{ t("nav.foreman") }}
        </p>
        <h2 class="text-lg font-semibold text-foreground">{{ t("foreman.agents") }}</h2>
        <p class="text-sm text-muted-foreground mt-1">{{ t("foreman.previewDescription") }}</p>
      </div>

      <label class="relative block">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          :value="keyword"
          type="text"
          :placeholder="t('foreman.searchConversations')"
          class="w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          @input="handleKeywordInput"
        />
      </label>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto px-3 py-3">
      <div v-if="items.length === 0" class="h-full flex items-center justify-center px-6 text-center">
        <div>
          <MessageSquareText class="w-10 h-10 mx-auto text-muted-foreground/40 mb-3" />
          <p class="text-sm font-medium text-foreground">{{ t("foreman.noAgents") }}</p>
          <p class="text-xs text-muted-foreground mt-1">{{ t("foreman.noAgentsHint") }}</p>
        </div>
      </div>

      <div v-else class="space-y-2">
        <button
          v-for="item in items"
          :key="item.id"
          class="w-full text-left rounded-2xl border px-4 py-3 transition-all duration-150"
          :class="item.id === activeItemId
            ? 'border-primary bg-primary/5 shadow-float'
            : 'border-transparent bg-background hover:border-border hover:bg-muted/60'"
          @click="$emit('select', item)"
        >
          <div class="flex items-start gap-3">
            <div
              class="w-10 h-10 shrink-0 rounded-2xl flex items-center justify-center font-semibold text-sm"
              :style="getItemAvatarStyle(item)"
            >
              {{ getConversationAbbr(item.title) }}
            </div>

            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 mb-1">
                <p class="font-medium truncate text-foreground">{{ item.title }}</p>
                <span class="shrink-0 text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                  {{ t(item.type === 'group' ? 'foreman.group' : 'foreman.agent') }}
                </span>
              </div>
              <p class="text-sm text-muted-foreground line-clamp-2 break-words">
                {{ item.summary || t("foreman.noMessages") }}
              </p>
              <div class="flex items-center justify-between gap-3 mt-3">
                <span class="text-xs text-muted-foreground truncate">
                  {{ item.type === 'group' ? t('foreman.memberCount', { count: item.agentIds.length }) : item.businessUnitName }}
                </span>
                <span v-if="item.updatedAt" class="text-xs text-muted-foreground">
                  {{ formatTime(item.updatedAt) }}
                </span>
              </div>
            </div>
          </div>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { MessageSquareText, Search } from "lucide-vue-next";
import { useI18n } from "vue-i18n";
import type { ForemanSidebarItem } from "@/types/foreman";

defineProps<{
  items: ForemanSidebarItem[];
  activeItemId: string | null;
  keyword: string;
}>();

const emit = defineEmits<{
  (event: "update:keyword", value: string): void;
  (event: "select", item: ForemanSidebarItem): void;
}>();

const { t } = useI18n();

function handleKeywordInput(event: Event): void {
  emit("update:keyword", (event.target as HTMLInputElement).value);
}

function formatTime(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();

  if (sameDay) {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function getConversationAbbr(title: string): string {
  return title
    .split(/\s+/)
    .slice(0, 2)
    .map((chunk) => chunk[0] || "")
    .join("")
    .toUpperCase();
}

function getItemAvatarStyle(item: ForemanSidebarItem): Record<string, string> {
  if (item.type === "agent" && item.accentColor) {
    return {
      backgroundColor: `${item.accentColor}1A`,
      color: item.accentColor,
    };
  }

  return {
    backgroundColor: "rgb(59 130 246 / 0.1)",
    color: "rgb(37 99 235)",
  };
}
</script>
