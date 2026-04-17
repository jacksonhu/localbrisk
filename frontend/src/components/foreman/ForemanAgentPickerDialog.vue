<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('foreman.addMembers')"
    :icon="UserRoundPlus"
    width="md"
    max-height="screen"
    @close="handleClose"
  >
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground leading-6">
        {{ conversation?.type === 'group' ? t('foreman.addMembersToGroupHint') : t('foreman.upgradeDirectHint') }}
      </p>

      <div v-if="selectableAgents.length > 0" class="space-y-2">
        <label
          v-for="agent in selectableAgents"
          :key="agent.id"
          class="flex items-start gap-3 rounded-2xl border border-border px-4 py-3 cursor-pointer transition-colors hover:border-primary/30 hover:bg-primary/5"
        >
          <input
            :checked="modelValue.includes(agent.id)"
            type="checkbox"
            class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
            @change="toggleAgent(agent.id)"
          />

          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <p class="font-medium text-foreground truncate">{{ agent.displayName }}</p>
              <span class="w-2 h-2 rounded-full shrink-0" :class="presenceClassMap[agent.presence]"></span>
            </div>
            <p class="text-xs text-muted-foreground mt-1 truncate">{{ agent.businessUnitName }}</p>
            <p class="text-sm text-muted-foreground mt-2 line-clamp-2 leading-6">{{ agent.description }}</p>
          </div>
        </label>
      </div>

      <div v-else class="rounded-2xl border border-dashed border-border bg-muted/20 px-4 py-6 text-sm text-center text-muted-foreground">
        {{ t('foreman.noAvailableAgentsToAdd') }}
      </div>
    </div>

    <template #footer>
      <DialogFooter
        :disabled="modelValue.length === 0 || selectableAgents.length === 0"
        :submit-text="submitText"
        @cancel="handleClose"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { UserRoundPlus } from "lucide-vue-next";
import BaseDialog from "@/components/common/BaseDialog.vue";
import DialogFooter from "@/components/common/DialogFooter.vue";
import type { ForemanAgentDirectoryItem, ForemanConversation } from "@/types/foreman";

const props = defineProps<{
  isOpen: boolean;
  conversation: ForemanConversation | null;
  agents: ForemanAgentDirectoryItem[];
  modelValue: string[];
}>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "update:modelValue", value: string[]): void;
  (event: "confirm"): void;
}>();

const { t } = useI18n();

const presenceClassMap: Record<ForemanAgentDirectoryItem["presence"], string> = {
  online: "bg-emerald-500",
  busy: "bg-amber-500",
  offline: "bg-slate-300",
};

const existingAgentIds = computed(() => new Set(props.conversation?.agentIds || []));
const selectableAgents = computed(() => {
  return props.agents.filter((agent) => !existingAgentIds.value.has(agent.id));
});
const submitText = computed(() => {
  return props.conversation?.type === "group" ? t("foreman.confirmAddMembers") : t("foreman.confirmCreateGroup");
});

function toggleAgent(agentId: string): void {
  if (props.modelValue.includes(agentId)) {
    emit(
      "update:modelValue",
      props.modelValue.filter((item) => item !== agentId),
    );
    return;
  }

  emit("update:modelValue", [...props.modelValue, agentId]);
}

function handleClose(): void {
  emit("close");
}

function handleSubmit(): void {
  emit("confirm");
}
</script>
