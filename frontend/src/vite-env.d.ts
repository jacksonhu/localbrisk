/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

// SVG 模块声明
declare module "*.svg" {
  const content: string;
  export default content;
}

// Tauri 全局类型声明
interface Window {
  __TAURI__?: {
    [key: string]: unknown;
  };
}
