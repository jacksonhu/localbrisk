/**
 * Artifact Store — 管理制品（Artifact）数据
 * 对应右侧面板的制品展示（代码、图表、HTML预览等）
 * 支持版本控制，允许用户翻看历史版本
 */

import { ref, computed } from "vue";
import type { ArtifactPayload, ArtifactType } from "@/types/stream-protocol";

/** 制品条目（包含版本历史） */
export interface ArtifactEntry {
  id: string;
  currentVersion: number;
  versions: ArtifactPayload[];
  createdAt: number;
  updatedAt: number;
}

// ============ 状态 ============

const artifacts = ref<ArtifactEntry[]>([]);
const activeArtifactId = ref<string | null>(null);
const activeVersion = ref<number | null>(null);

// ============ 计算属性 ============

const activeArtifact = computed<ArtifactEntry | null>(() => {
  if (!activeArtifactId.value) {
    // 默认显示最新的制品
    return artifacts.value.length > 0
      ? artifacts.value[artifacts.value.length - 1]
      : null;
  }
  return artifacts.value.find((a) => a.id === activeArtifactId.value) || null;
});

const activePayload = computed<ArtifactPayload | null>(() => {
  const entry = activeArtifact.value;
  if (!entry) return null;
  
  const ver = activeVersion.value ?? entry.currentVersion;
  return entry.versions.find((v) => v.version === ver) || entry.versions[entry.versions.length - 1] || null;
});

const artifactCount = computed(() => artifacts.value.length);

const hasArtifacts = computed(() => artifacts.value.length > 0);

/** 按类型分组的制品列表 */
const artifactsByType = computed(() => {
  const grouped: Record<string, ArtifactEntry[]> = {};
  for (const a of artifacts.value) {
    const latestVersion = a.versions[a.versions.length - 1];
    const type = latestVersion?.artifact_type || "text";
    if (!grouped[type]) {
      grouped[type] = [];
    }
    grouped[type].push(a);
  }
  return grouped;
});

// ============ Actions ============

function handleArtifact(payload: ArtifactPayload) {
  const artifactId = payload.artifact_id;
  const existing = artifacts.value.find((a) => a.id === artifactId);
  
  if (existing) {
    // 更新已有制品（新版本）
    existing.versions.push({ ...payload });
    existing.currentVersion = payload.version;
    existing.updatedAt = Date.now();
  } else {
    // 新制品
    artifacts.value.push({
      id: artifactId,
      currentVersion: payload.version,
      versions: [{ ...payload }],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
  }
  
  // 自动切换到最新制品
  activeArtifactId.value = artifactId;
  activeVersion.value = payload.version;
}

function selectArtifact(artifactId: string, version?: number) {
  activeArtifactId.value = artifactId;
  if (version !== undefined) {
    activeVersion.value = version;
  } else {
    const entry = artifacts.value.find((a) => a.id === artifactId);
    activeVersion.value = entry?.currentVersion || null;
  }
}

function selectVersion(version: number) {
  activeVersion.value = version;
}

function removeArtifact(artifactId: string) {
  artifacts.value = artifacts.value.filter((a) => a.id !== artifactId);
  if (activeArtifactId.value === artifactId) {
    activeArtifactId.value = null;
    activeVersion.value = null;
  }
}

function reset() {
  artifacts.value = [];
  activeArtifactId.value = null;
  activeVersion.value = null;
}

// ============ 导出 ============

export function useArtifactStore() {
  return {
    artifacts,
    activeArtifactId,
    activeVersion,
    activeArtifact,
    activePayload,
    artifactCount,
    hasArtifacts,
    artifactsByType,
    handleArtifact,
    selectArtifact,
    selectVersion,
    removeArtifact,
    reset,
  };
}

export default useArtifactStore;
