<template>
  <section class="h-full flex flex-col min-h-0 bg-background">
    <div v-if="conversation" class="px-6 py-4 border-b border-border bg-card/80 backdrop-blur-sm">
      <div class="flex items-center justify-between gap-4">
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <h2 class="text-lg font-semibold text-foreground truncate">{{ conversation.title }}</h2>
            <span class="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
              {{ t(conversation.type === 'group' ? 'foreman.group' : 'foreman.direct') }}
            </span>
            <span class="text-[11px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
              {{ t('foreman.frontendOnly') }}
            </span>
          </div>
          <p class="text-sm text-muted-foreground mt-1 truncate">
            {{ memberLine }}
          </p>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <div class="text-right">
            <p class="text-xs uppercase tracking-[0.24em] text-muted-foreground">{{ t('foreman.members') }}</p>
            <p class="text-sm font-medium text-foreground">{{ members.length }}</p>
          </div>

          <button
            type="button"
            class="h-11 w-11 rounded-xl border border-border bg-background text-foreground flex items-center justify-center transition-colors hover:bg-muted"
            :title="t('foreman.addMembers')"
            @click="showPicker = true"
          >
            <UserRoundPlus class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="conversation" ref="messageContainerRef" class="flex-1 min-h-0 overflow-y-auto px-6 py-5 space-y-5">
      <div
        v-for="message in conversation.messages"
        :key="message.id"
        class="flex"
        :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div v-if="message.role === 'system'" class="mx-auto max-w-2xl text-center">
          <div class="inline-flex items-center rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
            {{ message.content }}
          </div>
        </div>

        <div
          v-else
          class="max-w-[78%]"
          :class="message.role === 'user' ? 'items-end' : 'items-start'"
        >
          <p
            v-if="message.role === 'agent'"
            class="text-xs font-medium text-muted-foreground mb-1 px-1"
          >
            {{ message.senderName }}
          </p>
          <div
            class="rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm"
            :class="message.role === 'user'
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-card border border-border text-foreground rounded-tl-sm'"
          >
            {{ message.content }}
          </div>
          <p class="text-[11px] text-muted-foreground mt-1 px-1">
            {{ formatMessageTime(message.createdAt) }}
          </p>
        </div>
      </div>

      <div v-if="typingMembers.length > 0" class="flex justify-start">
        <div class="max-w-[70%] rounded-2xl rounded-tl-sm border border-dashed border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          {{ t('foreman.typing', { names: typingMembers.join('、') }) }}
        </div>
      </div>
    </div>

    <div v-else class="flex-1 min-h-0 flex items-center justify-center px-8">
      <div class="max-w-md text-center">
        <MessagesSquare class="w-14 h-14 mx-auto text-muted-foreground/35 mb-4" />
        <h3 class="text-lg font-semibold text-foreground">{{ t('foreman.emptyTitle') }}</h3>
        <p class="text-sm text-muted-foreground mt-2 leading-6">{{ t('foreman.emptyDescription') }}</p>
      </div>
    </div>

    <div class="px-6 pb-6 pt-4 border-t border-border bg-card/90 backdrop-blur-sm">
      <div class="rounded-3xl border border-border bg-card shadow-sm px-4 py-3">
        <textarea
          :value="modelValue"
          rows="3"
          :placeholder="conversation ? t('foreman.inputPlaceholder') : t('foreman.inputDisabledPlaceholder')"
          class="w-full resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-muted-foreground/80 disabled:cursor-not-allowed"
          :disabled="!conversation || isSending"
          @input="handleInput"
          @keydown="handleKeydown"
        />
        <div class="mt-3 flex items-center justify-between gap-3">
          <p class="text-xs text-muted-foreground">{{ t('foreman.inputHint') }}</p>
          <button
            class="inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-medium transition-colors"
            :class="canSend
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'"
            :disabled="!canSend"
            @click="$emit('send')"
          >
            <SendHorizontal class="w-4 h-4" />
            <span>{{ isSending ? t('foreman.sending') : t('foreman.send') }}</span>
          </button>
        </div>
      </div>
    </div>

    <ForemanAgentPickerDialog
      v-model="selectedAgentIds"
      :is-open="showPicker"
      :conversation="conversation"
      :agents="allAgents"
      @close="handleClosePicker"
      @confirm="handleConfirmAddAgents"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { MessagesSquare, SendHorizontal, UserRoundPlus } from "lucide-vue-next";
import { useI18n } from "vue-i18n";
import ForemanAgentPickerDialog from "@/components/foreman/ForemanAgentPickerDialog.vue";
import type { ForemanAgentDirectoryItem, ForemanConversation } from "@/types/foreman";

const props = defineProps<{
  conversation: ForemanConversation | null;
  members: ForemanAgentDirectoryItem[];
  allAgents: ForemanAgentDirectoryItem[];
  typingAgentIds: string[];
  modelValue: string;
  isSending: boolean;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
  (event: "send"): void;
  (event: "add-agents", agentIds: string[]): void;
}>();

const { t } = useI18n();
const messageContainerRef = ref<HTMLElement | null>(null);
const showPicker = ref(false);
const selectedAgentIds = ref<string[]>([]);

const memberLine = computed(() => props.members.map((member) => member.displayName).join("、"));
const typingMembers = computed(() => {
  return props.typingAgentIds
    .map((agentId) => props.members.find((member) => member.id === agentId)?.displayName)
    .filter((name): name is string => Boolean(name));
});
const canSend = computed(() => Boolean(props.conversation) && Boolean(props.modelValue.trim()) && !props.isSending);

function handleInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLTextAreaElement).value);
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (canSend.value) {
      emit("send");
    }
  }
}

function formatMessageTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function handleClosePicker(): void {
  showPicker.value = false;
  selectedAgentIds.value = [];
}

function handleConfirmAddAgents(): void {
  if (selectedAgentIds.value.length === 0) {
    return;
  }

  emit("add-agents", selectedAgentIds.value);
  handleClosePicker();
}

async function scrollToBottom(): Promise<void> {
  await nextTick();
  if (messageContainerRef.value) {
    messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
  }
}

watch(
  () => props.conversation?.messages.length,
  () => {
    scrollToBottom();
  },
  { immediate: true },
);

watch(
  () => props.conversation?.id,
  () => {
    handleClosePicker();
    scrollToBottom();
  },
  { immediate: true },
);
</script>
