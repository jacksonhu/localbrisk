import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // 防止 Vite 在 Tauri 开发时清除 Rust 错误
  clearScreen: false,
  // Tauri 需要固定端口
  server: {
    port: 1420,
    strictPort: true,
  },
  // 生产环境使用相对路径（关键！Tauri 打包需要）
  base: "./",
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    // Tauri 在 Windows 上使用 Chromium，在 macOS 和 Linux 上使用 WebKit
    target: process.env.TAURI_PLATFORM === "windows" ? "chrome105" : "safari13",
    // 在 debug 构建中禁用压缩
    minify: !process.env.TAURI_DEBUG ? "esbuild" : false,
    // 在 debug 构建中生成 sourcemap
    sourcemap: !!process.env.TAURI_DEBUG,
  },
});
