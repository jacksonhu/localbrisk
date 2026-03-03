<template>
  <div class="artifact-panel h-full flex flex-col bg-background">
    <!-- 无制品空状态 -->
    <div v-if="!artifactStore.hasArtifacts.value" class="h-full flex flex-col items-center justify-center text-center p-8">
      <Layers class="w-16 h-16 text-muted-foreground/15 mb-4" />
      <h3 class="text-sm font-medium text-muted-foreground mb-1">暂无输出成果</h3>
      <p class="text-xs text-muted-foreground/60">Agent 执行产生的代码、图表等将在此展示，您可以二次编辑</p>
    </div>

    <template v-else>
      <!-- 制品标签栏 -->
      <div class="artifact-tabs flex items-center border-b border-border px-2 py-1 gap-1 overflow-x-auto">
        <button
          v-for="entry in artifactStore.artifacts.value"
          :key="entry.id"
          @click="artifactStore.selectArtifact(entry.id)"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md whitespace-nowrap transition-colors"
          :class="entry.id === artifactStore.activeArtifactId.value
            ? 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          <component :is="getArtifactIcon(getLatestType(entry))" class="w-3.5 h-3.5" />
          <span>{{ getArtifactTitle(entry) }}</span>
          <span v-if="entry.versions.length > 1" class="text-[10px] opacity-60">v{{ entry.currentVersion }}</span>
        </button>
      </div>

      <!-- 制品内容区 -->
      <div class="flex-1 overflow-hidden flex flex-col" v-if="activePayload">
        <!-- 制品头部 -->
        <div class="artifact-header flex items-center justify-between px-4 py-2 border-b border-border/50 bg-muted/20">
          <div class="flex items-center gap-2 min-w-0">
            <component :is="getArtifactIcon(activePayload.artifact_type)" class="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span class="text-sm font-medium truncate">{{ activePayload.title || activePayload.artifact_id }}</span>
            <span v-if="activePayload.language" class="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {{ activePayload.language }}
            </span>
            <span v-if="activePayload.filepath" class="text-xs text-muted-foreground truncate font-mono">
              {{ activePayload.filepath }}
            </span>
          </div>

          <div class="flex items-center gap-2">
            <!-- 编辑/预览切换 -->
            <button
              v-if="isEditable"
              @click="toggleEditMode"
              class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors"
              :class="isEditing ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted'"
            >
              <Pencil v-if="!isEditing" class="w-3.5 h-3.5" />
              <Eye v-else class="w-3.5 h-3.5" />
              {{ isEditing ? '预览' : '编辑' }}
            </button>

            <!-- 版本选择器 -->
            <div v-if="activeArtifact && activeArtifact.versions.length > 1" class="flex items-center gap-1">
              <button
                @click="prevVersion"
                :disabled="!canPrevVersion"
                class="p-1 rounded hover:bg-muted transition-colors disabled:opacity-30"
              >
                <ChevronLeft class="w-3.5 h-3.5" />
              </button>
              <span class="text-xs text-muted-foreground min-w-[60px] text-center">
                v{{ artifactStore.activeVersion.value }} / {{ activeArtifact.versions.length }}
              </span>
              <button
                @click="nextVersion"
                :disabled="!canNextVersion"
                class="p-1 rounded hover:bg-muted transition-colors disabled:opacity-30"
              >
                <ChevronRight class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- 操作按钮 -->
            <div v-if="activePayload.operation" class="text-xs px-1.5 py-0.5 rounded"
              :class="{
                'bg-green-900/30 text-green-400': activePayload.operation === 'create',
                'bg-blue-900/30 text-blue-400': activePayload.operation === 'update',
                'bg-red-900/30 text-red-400': activePayload.operation === 'delete',
                'bg-gray-700 text-gray-300': activePayload.operation === 'view',
              }"
            >{{ getOpLabel(activePayload.operation) }}</div>

            <button @click="copyContent" class="p-1 rounded hover:bg-muted transition-colors" title="复制">
              <Copy class="w-3.5 h-3.5 text-muted-foreground" />
            </button>
          </div>
        </div>

        <!-- 渲染区域 -->
        <div class="flex-1 overflow-auto">
          <!-- 代码类型 -->
          <div v-if="activePayload.artifact_type === 'code'" class="h-full flex flex-col">
            <!-- 编辑模式 -->
            <div v-if="isEditing" class="flex-1 flex flex-col">
              <div class="code-toolbar flex items-center justify-between px-4 py-1.5 bg-gray-900 dark:bg-gray-950 border-b border-gray-700">
                <span class="text-xs text-gray-400">{{ activePayload.language || 'text' }} - 编辑模式</span>
                <div class="flex items-center gap-2">
                  <button
                    @click="saveEdit"
                    class="px-2 py-0.5 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    保存
                  </button>
                  <button
                    @click="cancelEdit"
                    class="px-2 py-0.5 text-xs rounded bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
                  >
                    取消
                  </button>
                </div>
              </div>
              <textarea
                ref="editTextareaRef"
                v-model="editContent"
                class="flex-1 p-4 bg-gray-900 dark:bg-gray-950 text-sm font-mono leading-relaxed text-green-400 resize-none focus:outline-none w-full"
                spellcheck="false"
              ></textarea>
            </div>
            <!-- 预览模式 -->
            <div v-else class="h-full">
              <div class="code-toolbar flex items-center justify-between px-4 py-1.5 bg-gray-900 dark:bg-gray-950 border-b border-gray-700">
                <span class="text-xs text-gray-400">{{ activePayload.language || 'text' }}</span>
              </div>
              <pre class="p-4 bg-gray-900 dark:bg-gray-950 text-sm font-mono leading-relaxed overflow-auto h-[calc(100%-32px)]"><code :class="`language-${activePayload.language || 'text'}`">{{ activePayload.content }}</code></pre>
            </div>
          </div>

          <!-- HTML 预览 -->
          <div v-else-if="activePayload.artifact_type === 'html'" class="h-full flex flex-col">
            <div class="flex items-center justify-between px-4 py-1.5 bg-muted/30 border-b border-border/50">
              <span class="text-xs text-muted-foreground">HTML</span>
              <div class="flex items-center gap-2">
                <button @click="htmlPreviewMode = 'preview'"
                  class="text-xs px-2 py-0.5 rounded transition-colors"
                  :class="htmlPreviewMode === 'preview' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'">
                  预览
                </button>
                <button @click="htmlPreviewMode = 'source'"
                  class="text-xs px-2 py-0.5 rounded transition-colors"
                  :class="htmlPreviewMode === 'source' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'">
                  源码
                </button>
                <button v-if="htmlPreviewMode === 'source' && isEditing" @click="saveEdit"
                  class="px-2 py-0.5 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
                  保存
                </button>
              </div>
            </div>
            <div v-if="htmlPreviewMode === 'preview'" class="flex-1 bg-white">
              <iframe :srcdoc="isEditing ? editContent : activePayload.content" class="w-full h-full border-0" sandbox="allow-scripts allow-same-origin" />
            </div>
            <div v-else class="flex-1">
              <textarea
                v-if="isEditing"
                v-model="editContent"
                class="w-full h-full p-4 bg-gray-900 dark:bg-gray-950 text-sm font-mono leading-relaxed text-green-400 resize-none focus:outline-none"
                spellcheck="false"
              ></textarea>
              <pre v-else class="h-full p-4 bg-gray-900 dark:bg-gray-950 text-sm font-mono leading-relaxed overflow-auto"><code class="language-html">{{ activePayload.content }}</code></pre>
            </div>
          </div>

          <!-- 图表 -->
          <div v-else-if="activePayload.artifact_type === 'chart'" class="h-full flex flex-col">
            <div class="flex items-center px-4 py-1.5 bg-muted/30 border-b border-border/50">
              <span class="text-xs text-muted-foreground">{{ activePayload.chart_type || 'chart' }}</span>
            </div>
            <div class="flex-1 p-4">
              <div v-if="activePayload.chart_config" class="w-full h-full flex items-center justify-center">
                <pre class="text-xs text-muted-foreground bg-muted/30 p-4 rounded-lg overflow-auto max-h-full w-full">{{ JSON.stringify(activePayload.chart_config, null, 2) }}</pre>
              </div>
              <div v-else class="w-full h-full flex items-center justify-center text-muted-foreground">
                <BarChart3 class="w-12 h-12 opacity-20" />
              </div>
            </div>
          </div>

          <!-- 表格 -->
          <div v-else-if="activePayload.artifact_type === 'table'" class="h-full overflow-auto">
            <table v-if="activePayload.headers && activePayload.rows" class="w-full text-sm">
              <thead class="sticky top-0 bg-muted/80 backdrop-blur">
                <tr>
                  <th v-for="header in activePayload.headers" :key="header" class="text-left px-4 py-2 text-xs font-medium text-muted-foreground border-b border-border">
                    {{ header }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in activePayload.rows" :key="idx" class="hover:bg-muted/30 transition-colors">
                  <td v-for="(cell, cidx) in row" :key="cidx" class="px-4 py-2 border-b border-border/50 font-mono text-xs">
                    {{ cell }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="p-4">
              <pre class="text-sm font-mono whitespace-pre-wrap">{{ activePayload.content }}</pre>
            </div>
          </div>

          <!-- 命令 -->
          <div v-else-if="activePayload.artifact_type === 'command'" class="p-4">
            <div class="bg-gray-900 dark:bg-gray-950 rounded-lg overflow-hidden">
              <div class="flex items-center justify-between px-3 py-2 border-b border-gray-700">
                <span class="text-xs text-gray-400 font-mono">Terminal</span>
                <div class="flex items-center gap-2">
                  <span v-if="activePayload.is_dangerous" class="text-xs px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 flex items-center gap-1">
                    <AlertTriangle class="w-3 h-3" /> 危险
                  </span>
                </div>
              </div>
              <div class="p-3">
                <code class="text-green-400 font-mono text-sm">$ {{ activePayload.command || activePayload.content }}</code>
              </div>
              <div v-if="activePayload.command_explanation" class="px-3 pb-3">
                <p class="text-xs text-gray-400">{{ activePayload.command_explanation }}</p>
              </div>
            </div>
          </div>

          <!-- 图片 -->
          <div v-else-if="activePayload.artifact_type === 'image'" class="h-full flex items-center justify-center p-4 bg-muted/10">
            <img v-if="activePayload.content" :src="activePayload.content" class="max-w-full max-h-full object-contain rounded-lg shadow-sm" />
            <ImageIcon v-else class="w-16 h-16 text-muted-foreground/20" />
          </div>

          <!-- 文本/文件/默认 -->
          <div v-else class="h-full">
            <div v-if="isEditing" class="h-full flex flex-col">
              <div class="flex items-center justify-end px-4 py-1.5 bg-muted/30 border-b border-border/50 gap-2">
                <button @click="saveEdit" class="px-2 py-0.5 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">保存</button>
                <button @click="cancelEdit" class="px-2 py-0.5 text-xs rounded bg-muted text-muted-foreground hover:bg-muted/80 transition-colors">取消</button>
              </div>
              <textarea
                v-model="editContent"
                class="flex-1 p-4 text-sm leading-relaxed resize-none focus:outline-none w-full bg-background"
                spellcheck="false"
              ></textarea>
            </div>
            <div v-else class="p-4">
              <div class="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap">
                {{ activePayload.content }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  Layers, Code, FileText, BarChart3, Globe, Table2,
  Terminal, ImageIcon, File, ChevronLeft, ChevronRight,
  Copy, AlertTriangle, Pencil, Eye,
} from "lucide-vue-next";
import { useArtifactStore } from "@/stores/artifactStore";
import type { ArtifactEntry } from "@/stores/artifactStore";
import type { ArtifactType, ArtifactPayload } from "@/types/stream-protocol";

const artifactStore = useArtifactStore();

const htmlPreviewMode = ref<"preview" | "source">("preview");
const isEditing = ref(false);
const editContent = ref("");
const editTextareaRef = ref<HTMLTextAreaElement | null>(null);

const activeArtifact = computed(() => artifactStore.activeArtifact.value);
const activePayload = computed(() => artifactStore.activePayload.value);

const isEditable = computed(() => {
  const type = activePayload.value?.artifact_type;
  return type === "code" || type === "html" || type === "text";
});

const canPrevVersion = computed(() => {
  if (!activeArtifact.value || !artifactStore.activeVersion.value) return false;
  return artifactStore.activeVersion.value > 1;
});

const canNextVersion = computed(() => {
  if (!activeArtifact.value || !artifactStore.activeVersion.value) return false;
  return artifactStore.activeVersion.value < activeArtifact.value.versions.length;
});

function prevVersion() {
  if (canPrevVersion.value && artifactStore.activeVersion.value) {
    artifactStore.selectVersion(artifactStore.activeVersion.value - 1);
  }
}

function nextVersion() {
  if (canNextVersion.value && artifactStore.activeVersion.value) {
    artifactStore.selectVersion(artifactStore.activeVersion.value + 1);
  }
}

function toggleEditMode() {
  if (isEditing.value) {
    // 切换到预览
    isEditing.value = false;
  } else {
    // 切换到编辑
    editContent.value = activePayload.value?.content || "";
    isEditing.value = true;
  }
}

function saveEdit() {
  if (!activePayload.value) return;
  // 更新 artifact 内容（创建新版本）
  const payload = { ...activePayload.value };
  payload.content = editContent.value;
  payload.version = (activeArtifact.value?.versions.length || 0) + 1;
  artifactStore.handleArtifact(payload as ArtifactPayload);
  isEditing.value = false;
}

function cancelEdit() {
  isEditing.value = false;
  editContent.value = "";
}

// 切换制品时退出编辑模式
watch(() => artifactStore.activeArtifactId.value, () => {
  isEditing.value = false;
  editContent.value = "";
});

function getLatestType(entry: ArtifactEntry): ArtifactType {
  const latest = entry.versions[entry.versions.length - 1];
  return latest?.artifact_type || "text";
}

function getArtifactTitle(entry: ArtifactEntry): string {
  const latest = entry.versions[entry.versions.length - 1];
  return latest?.title || latest?.filepath || entry.id;
}

function getArtifactIcon(type: ArtifactType) {
  const iconMap: Record<ArtifactType, any> = {
    code: Code, chart: BarChart3, html: Globe, table: Table2,
    text: FileText, image: ImageIcon, file: File, command: Terminal,
  };
  return iconMap[type] || FileText;
}

function getOpLabel(op?: string): string {
  const labels: Record<string, string> = {
    create: "新建", update: "修改", delete: "删除", view: "查看", diff: "对比",
  };
  return labels[op || "view"] || "";
}

function copyContent() {
  const content = activePayload.value?.content || activePayload.value?.command || "";
  if (content) {
    navigator.clipboard.writeText(content).catch(() => {});
  }
}
</script>

<style scoped>
.artifact-tabs {
  scrollbar-width: thin;
}
.artifact-tabs::-webkit-scrollbar {
  height: 3px;
}
.artifact-tabs::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.2);
  border-radius: 3px;
}

pre code {
  color: #e0e0e0;
}

textarea {
  scrollbar-width: thin;
}
</style>
