/**
 * 异步状态管理 Composable
 * 统一处理加载、错误、数据状态
 */

import { ref, type Ref } from 'vue';

/**
 * 异步状态返回类型
 */
export interface AsyncState<T> {
  /** 数据 */
  data: Ref<T | null>;
  /** 加载状态 */
  loading: Ref<boolean>;
  /** 错误信息 */
  error: Ref<string | null>;
  /** 执行异步操作 */
  execute: (fn: () => Promise<T>) => Promise<T | null>;
  /** 重置状态 */
  reset: () => void;
  /** 清除错误 */
  clearError: () => void;
  /** 设置数据 */
  setData: (data: T) => void;
}

/**
 * 创建异步状态管理
 * @param initialData 初始数据
 * @returns 异步状态对象
 */
export function useAsyncState<T>(initialData: T | null = null): AsyncState<T> {
  const data = ref<T | null>(initialData) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<string | null>(null);
  
  /**
   * 执行异步操作
   */
  async function execute(fn: () => Promise<T>): Promise<T | null> {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await fn();
      data.value = result;
      return result;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      return null;
    } finally {
      loading.value = false;
    }
  }
  
  /**
   * 重置状态
   */
  function reset(): void {
    data.value = initialData;
    loading.value = false;
    error.value = null;
  }
  
  /**
   * 清除错误
   */
  function clearError(): void {
    error.value = null;
  }
  
  /**
   * 设置数据
   */
  function setData(newData: T): void {
    data.value = newData;
  }
  
  return {
    data,
    loading,
    error,
    execute,
    reset,
    clearError,
    setData,
  };
}

/**
 * 创建列表异步状态管理
 * 专门用于列表数据的加载
 */
export function useAsyncList<T>() {
  const items = ref<T[]>([]) as Ref<T[]>;
  const loading = ref(false);
  const error = ref<string | null>(null);
  const total = ref(0);
  
  async function execute(fn: () => Promise<T[]>): Promise<T[]> {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await fn();
      items.value = result;
      total.value = result.length;
      return result;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      return [];
    } finally {
      loading.value = false;
    }
  }
  
  function reset(): void {
    items.value = [];
    loading.value = false;
    error.value = null;
    total.value = 0;
  }
  
  function append(newItems: T[]): void {
    items.value = [...items.value, ...newItems];
    total.value = items.value.length;
  }
  
  function remove(predicate: (item: T) => boolean): void {
    items.value = items.value.filter(item => !predicate(item));
    total.value = items.value.length;
  }
  
  return {
    items,
    loading,
    error,
    total,
    execute,
    reset,
    append,
    remove,
  };
}
