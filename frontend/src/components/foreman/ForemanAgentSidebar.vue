<template>
  <section class="h-full min-h-0 bg-[#F4F5F7] px-5 py-5 overflow-y-auto">
    <div class="mb-4">
      <h2 class="text-base font-semibold text-slate-600">
        {{ t('foreman.groupMembers') }} · {{ members.length }}
      </h2>
    </div>

    <div v-if="members.length > 0" class="space-y-1">
      <div
        v-for="member in members"
        :key="member.id"
        class="flex items-center justify-between gap-3 rounded-xl px-2 py-2 text-[15px] text-slate-900"
      >
        <span class="truncate leading-8">{{ member.displayName }}</span>
        <Monitor class="w-4 h-4 shrink-0" :class="presenceIconClassMap[member.presence]" />
      </div>
    </div>

    <p v-else class="text-sm text-muted-foreground">{{ t('foreman.emptyMembers') }}</p>
  </section>
</template>

<script setup lang="ts">
import { Monitor } from "lucide-vue-next";
import { useI18n } from "vue-i18n";
import type { ForemanAgentDirectoryItem, ForemanConversation } from "@/types/foreman";

defineProps<{
  conversation: ForemanConversation;
  members: ForemanAgentDirectoryItem[];
}>();

const { t } = useI18n();

const presenceIconClassMap: Record<ForemanAgentDirectoryItem["presence"], string> = {
  online: "text-sky-500",
  busy: "text-sky-500",
  offline: "text-slate-400",
};
</script>
