/**
 * Toast 通知 Composable
 * 提供统一的消息提示功能
 * 使用简单的浏览器通知或控制台日志作为后备
 */

import { ref } from 'vue';

/** Toast 消息类型 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/** Toast 消息 */
export interface ToastMessage {
  id: number;
  type: ToastType;
  message: string;
  duration: number;
}

/** Toast 消息队列（全局状态） */
const toastMessages = ref<ToastMessage[]>([]);
let toastId = 0;

/**
 * 添加 Toast 消息
 */
function addToast(type: ToastType, message: string, duration: number = 3000): number {
  const id = ++toastId;
  
  toastMessages.value.push({
    id,
    type,
    message,
    duration,
  });
  
  // 自动移除
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }
  
  // 同时输出到控制台
  const logMethod = type === 'error' ? console.error : 
                    type === 'warning' ? console.warn : 
                    console.log;
  logMethod(`[Toast ${type.toUpperCase()}] ${message}`);
  
  return id;
}

/**
 * 移除 Toast 消息
 */
function removeToast(id: number) {
  const index = toastMessages.value.findIndex(t => t.id === id);
  if (index !== -1) {
    toastMessages.value.splice(index, 1);
  }
}

/**
 * Toast 通知 Composable
 * 
 * @example
 * ```ts
 * const { showSuccess, showError } = useToast();
 * 
 * showSuccess('保存成功');
 * showError('操作失败');
 * ```
 */
export function useToast() {
  /**
   * 显示成功消息
   */
  function showSuccess(message: string, duration?: number): number {
    return addToast('success', message, duration);
  }
  
  /**
   * 显示错误消息
   */
  function showError(message: string, duration?: number): number {
    return addToast('error', message, duration ?? 5000);
  }
  
  /**
   * 显示警告消息
   */
  function showWarning(message: string, duration?: number): number {
    return addToast('warning', message, duration);
  }
  
  /**
   * 显示信息消息
   */
  function showInfo(message: string, duration?: number): number {
    return addToast('info', message, duration);
  }
  
  /**
   * 清除所有消息
   */
  function clearAll() {
    toastMessages.value = [];
  }
  
  return {
    // 状态
    toastMessages,
    
    // 方法
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeToast,
    clearAll,
  };
}

export default useToast;
