<template>
  <div class="app-container h-screen flex flex-col overflow-hidden">
    <!-- 主体内容区域 -->
    <main class="flex-1 overflow-hidden">
      <router-view v-if="backendStatus === 'connected'" />
      
      <!-- 连接中状态 -->
      <div v-else class="h-full flex items-center justify-center">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
            <svg class="w-8 h-8 text-primary animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-medium mb-2">{{ t('header.connectingBackend') }}</h2>
          <p class="text-muted-foreground text-sm">{{ statusMessage }}</p>
          
          <!-- 重试按钮 -->
          <button
            v-if="backendStatus === 'disconnected'"
            @click="initializeBackend"
            class="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary/90"
          >
            {{ t('header.reconnect') }}
          </button>
        </div>
      </div>
    </main>

    <!-- 设置弹窗 -->
    <SettingsDialog
      :is-open="isSettingsOpen"
      @close="isSettingsOpen = false"
      @save="handleSettingsSave"
    />
    
    <!-- 关于弹窗 -->
    <AboutDialog
      :is-open="isAboutOpen"
      :version="appInfo?.version || '0.1.0'"
      @close="isAboutOpen = false"
    />
    
    <!-- Toast 通知容器 -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { UnlistenFn } from "@tauri-apps/api/event";
import tauriService from "@/services/tauri";
import SettingsDialog from "@/components/settings/SettingsDialog.vue";
import AboutDialog from "@/components/settings/AboutDialog.vue";
import ToastContainer from "@/components/common/ToastContainer.vue";
import { setLocale } from "@/i18n";
import logoSvg from "@/assets/logo.svg";

const { t } = useI18n();

// Logo URL - 使用导入的资源
const logoUrl = logoSvg;

// 应用信息
const appInfo = ref<{ name: string; version: string; description: string } | null>(null);

// 后端状态
const backendStatus = ref<"connecting" | "connected" | "disconnected">("connecting");
const statusMessage = ref(t('header.gettingAppInfo'));

// 设置弹窗状态
const isSettingsOpen = ref(false);

// 关于弹窗状态
const isAboutOpen = ref(false);

// Tauri 事件取消订阅函数
let unlistenSettings: UnlistenFn | null = null;
let unlistenAbout: UnlistenFn | null = null;

// 处理设置保存
function handleSettingsSave(settings: any) {
  console.log("设置已保存:", settings);
  // 应用语言设置
  if (settings.language) {
    setLocale(settings.language);
  }
}

// 初始化后端服务
async function initializeBackend() {
  // 如果在 main.ts 初始化阶段已经确认后端就绪，直接使用该结果
  if (window.__BACKEND_READY__) {
    console.log("[App.vue] 后端已在启动阶段确认就绪");
    backendStatus.value = "connected";
    
    // 尝试获取应用信息
    try {
      appInfo.value = await tauriService.getAppInfo();
    } catch {
      appInfo.value = {
        name: "LocalBrisk",
        version: "0.1.0",
        description: t('about.description')
      };
    }
    return;
  }
  
  backendStatus.value = "connecting";
  
  try {
    // 尝试通过 Tauri API 获取应用信息
    try {
      statusMessage.value = t('header.gettingAppInfo');
      appInfo.value = await tauriService.getAppInfo();
      
      // 等待后端就绪（短时间检查，因为启动阶段已经等待过）
      statusMessage.value = t('header.waitingBackend');
      const ready = await tauriService.waitForBackend(5, 500);
      
      if (ready) {
        backendStatus.value = "connected";
        console.log("后端服务已就绪");
      } else {
        console.log("后端未就绪，进入离线模式");
        backendStatus.value = "connected";
      }
    } catch {
      // 非 Tauri 环境（纯 Web 开发模式）
      statusMessage.value = t('header.checkingConnection');
      appInfo.value = {
        name: "LocalBrisk",
        version: "0.1.0",
        description: t('about.description')
      };
      
      try {
        const response = await fetch("http://127.0.0.1:8765/health");
        if (response.ok) {
          backendStatus.value = "connected";
        } else {
          throw new Error("后端服务响应异常");
        }
      } catch {
        console.log("后端未启动，使用模拟模式");
        backendStatus.value = "connected";
      }
    }
  } catch (error) {
    console.error("初始化失败:", error);
    backendStatus.value = "connected";
    statusMessage.value = t('header.offlineMode');
  }
}

// 设置 Tauri 事件监听
async function setupTauriListeners() {
  // 检查是否在 Tauri 环境
  if (typeof window === 'undefined' || !('__TAURI__' in window)) {
    console.log("[App.vue] 非 Tauri 环境，跳过事件监听");
    return;
  }
  
  try {
    console.log("[App.vue] 正在设置 Tauri 事件监听...");
    
    // 动态导入 Tauri 事件 API
    const { listen: tauriListen } = await import("@tauri-apps/api/event");
    
    // 监听 Tauri 事件
    unlistenSettings = await tauriListen("open-settings", (event) => {
      console.log("[App.vue] 收到 open-settings 事件", event);
      isSettingsOpen.value = true;
    });
    
    unlistenAbout = await tauriListen("open-about", (event) => {
      console.log("[App.vue] 收到 open-about 事件", event);
      isAboutOpen.value = true;
    });
    
    console.log("[App.vue] Tauri 事件监听设置完成");
  } catch (e) {
    console.log("[App.vue] 设置 Tauri 事件监听失败:", e);
  }
}

// 添加键盘快捷键支持
function handleKeydown(event: KeyboardEvent) {
  // Cmd+, 或 Ctrl+, 打开设置
  if ((event.metaKey || event.ctrlKey) && event.key === ",") {
    event.preventDefault();
    isSettingsOpen.value = true;
  }
}

onMounted(() => {
  initializeBackend();
  setupTauriListeners();
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  // 清理 Tauri 事件监听
  if (unlistenSettings) unlistenSettings();
  if (unlistenAbout) unlistenAbout();
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.app-container {
  background-color: var(--background);
}
</style>
