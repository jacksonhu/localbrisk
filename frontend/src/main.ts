import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import i18n, { initLocaleFromSettings } from "./i18n";
import "./styles/index.css";

// 声明全局类型
declare global {
  interface Window {
    __BACKEND_READY__: boolean;
    __APP_INITIALIZED__: boolean;
    __initApp__: () => Promise<boolean>;
  }
}

console.log("[main.ts] 开始初始化应用...");

// 路由配置 - 使用 Hash 模式，兼容 Tauri 打包后的文件协议
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("./views/HomeView.vue"),
    },
    {
      path: "/foreman",
      name: "foreman",
      component: () => import("./views/ForemanView.vue"),
    },
  ],
});

console.log("[main.ts] 路由配置完成");

// 异步初始化应用
async function initializeApp() {
  try {
    // 等待后端服务就绪（由 index.html 中的脚本处理）
    if (typeof window.__initApp__ === "function") {
      console.log("[main.ts] 等待后端服务就绪...");
      const backendReady = await window.__initApp__();
      console.log("[main.ts] 后端状态:", backendReady ? "已就绪" : "离线模式");
    }

    const app = createApp(App);
    console.log("[main.ts] Vue 应用创建成功");

    app.use(router);
    app.use(i18n);
    console.log("[main.ts] 插件加载完成");

    app.mount("#app");
    console.log("[main.ts] 应用挂载成功");
    
    // 从配置文件异步加载语言设置
    await initLocaleFromSettings();
    console.log("[main.ts] 语言设置加载完成");

    // 标记应用已初始化
    window.__APP_INITIALIZED__ = true;

    // 隐藏加载状态
    const loading = document.getElementById("app-loading");
    if (loading) {
      loading.style.display = "none";
    }
  } catch (error) {
    console.error("[main.ts] 应用初始化失败:", error);

    // 显示错误
    const loading = document.getElementById("app-loading");
    const errorDiv = document.getElementById("app-error");
    const errorMsg = document.getElementById("error-message");

    if (loading) loading.style.display = "none";
    if (errorDiv) errorDiv.style.display = "flex";
    if (errorMsg) errorMsg.textContent = String(error);
  }
}

// 启动应用
initializeApp();
