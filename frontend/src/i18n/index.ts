/**
 * Vue I18n 国际化配置
 * 支持中文、英文，可扩展其他语言
 */

import { createI18n } from 'vue-i18n';
import zhCN from './locales/zh-CN';
import en from './locales/en';
import tauriService from '@/services/tauri';

// 支持的语言类型
export type SupportedLocale = 'zh-CN' | 'en' | 'zh-TW' | 'ja';

// 语言配置
export const SUPPORTED_LOCALES: Array<{ code: SupportedLocale; name: string; nativeName: string }> = [
  { code: 'zh-CN', name: 'Simplified Chinese', nativeName: '简体中文' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'zh-TW', name: 'Traditional Chinese', nativeName: '繁體中文' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
];

// 验证语言代码是否有效
function isValidLocale(locale: string): locale is SupportedLocale {
  return SUPPORTED_LOCALES.some(l => l.code === locale);
}

// 获取默认语言（同步版本，用于初始化）
function getDefaultLocaleSync(): SupportedLocale {
  // 1. 从 localStorage 获取用户保存的语言偏好（兼容旧版本）
  const stored = localStorage.getItem('localbrisk-settings');
  if (stored) {
    try {
      const settings = JSON.parse(stored);
      if (settings.language && isValidLocale(settings.language)) {
        return settings.language;
      }
    } catch {
      // 忽略解析错误
    }
  }

  // 2. 从浏览器语言设置获取
  const browserLang = navigator.language;
  if (browserLang.startsWith('zh')) {
    return browserLang.includes('TW') || browserLang.includes('HK') ? 'zh-TW' : 'zh-CN';
  }
  if (browserLang.startsWith('ja')) {
    return 'ja';
  }
  
  // 3. 默认中文
  return 'zh-CN';
}

// 创建 i18n 实例
const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: getDefaultLocaleSync(),
  fallbackLocale: 'en',
  messages: {
    'zh-CN': zhCN,
    'en': en,
    // 其他语言可以后续添加，暂时回退到英文
    'zh-TW': zhCN, // 暂时使用简体中文
    'ja': en, // 暂时使用英文
  },
});

// 异步初始化：从 Tauri 配置文件加载语言设置
export async function initLocaleFromSettings(): Promise<void> {
  if (tauriService.isTauriEnv()) {
    try {
      const settings = await tauriService.getAppSettings();
      if (settings.language && isValidLocale(settings.language)) {
        i18n.global.locale.value = settings.language;
        document.documentElement.lang = settings.language;
        console.log('[i18n] 从配置文件加载语言:', settings.language);
      }
    } catch (e) {
      console.warn('[i18n] 无法从 Tauri 读取语言设置:', e);
    }
  }
}

// 切换语言
export async function setLocale(locale: SupportedLocale): Promise<void> {
  if (isValidLocale(locale)) {
    i18n.global.locale.value = locale;
    document.documentElement.lang = locale;
    
    // 保存到 Tauri 配置文件
    if (tauriService.isTauriEnv()) {
      try {
        const currentSettings = await tauriService.getAppSettings();
        await tauriService.saveAppSettings({
          ...currentSettings,
          language: locale,
        });
        console.log('[i18n] 语言已保存到配置文件:', locale);
      } catch (e) {
        console.warn('[i18n] 保存语言设置失败，回退到 localStorage:', e);
        // 回退到 localStorage
        saveToLocalStorage(locale);
      }
    } else {
      // 非 Tauri 环境使用 localStorage
      saveToLocalStorage(locale);
    }
  }
}

// 保存到 localStorage（兼容非 Tauri 环境）
function saveToLocalStorage(locale: SupportedLocale): void {
  try {
    const stored = localStorage.getItem('localbrisk-settings');
    const settings = stored ? JSON.parse(stored) : {};
    settings.language = locale;
    localStorage.setItem('localbrisk-settings', JSON.stringify(settings));
  } catch {
    // 忽略存储错误
  }
}

// 获取当前语言
export function getLocale(): SupportedLocale {
  return i18n.global.locale.value as SupportedLocale;
}

export default i18n;
