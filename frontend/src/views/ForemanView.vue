<template>
  <div class="foreman-view h-full flex min-h-0">
    <AppNavRail />

    <div class="flex-1 min-w-0 flex bg-background">
      <aside class="w-[320px] shrink-0 border-r border-border min-h-0">
        <ForemanConversationList
          :items="sidebarItems"
          :active-item-id="activeSidebarItemId"
          :keyword="conversationKeyword"
          @update:keyword="conversationKeyword = $event"
          @select="selectSidebarItem"
        />
      </aside>

      <main class="flex-1 min-w-0 min-h-0">
        <ForemanChatWorkspace
          v-model="draftMessage"
          :conversation="activeConversation"
          :members="activeMembers"
          :all-agents="directoryAgents"
          :typing-agent-ids="typingAgentIds"
          :is-sending="isSending"
          @send="handleSendMessage"
          @add-agents="addAgentsToConversation"
        />
      </main>

      <aside
        v-if="activeConversation?.type === 'group'"
        class="w-[260px] shrink-0 border-l border-border min-h-0"
      >
        <ForemanAgentSidebar
          :conversation="activeConversation"
          :members="activeMembers"
        />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import AppNavRail from "@/components/layout/AppNavRail.vue";
import ForemanAgentSidebar from "@/components/foreman/ForemanAgentSidebar.vue";
import ForemanChatWorkspace from "@/components/foreman/ForemanChatWorkspace.vue";
import ForemanConversationList from "@/components/foreman/ForemanConversationList.vue";
import { useForemanChat } from "@/composables/useForemanChat";

const draftMessage = ref("");
const {
  activeConversation,
  activeMembers,
  activeSidebarItemId,
  addAgentsToConversation,
  conversationKeyword,
  directoryAgents,
  sidebarItems,
  typingAgentIds,
  isSending,
  selectSidebarItem,
  sendMessage,
} = useForemanChat();

async function handleSendMessage(): Promise<void> {
  const content = draftMessage.value.trim();
  if (!content) {
    return;
  }

  draftMessage.value = "";
  await sendMessage(content);
}
</script>

<style scoped>
.foreman-view {
  min-height: 0;
}
</style>
