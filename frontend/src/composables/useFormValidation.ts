/**
 * 表单验证 Composable
 * 提供统一的表单验证逻辑，支持实时验证和提交验证
 */

import { reactive, computed, ref } from 'vue';
import { NAME_REGEX, validate, type ValidationRule } from '@/utils/validationUtils';

/**
 * 字段验证规则配置
 */
export interface FieldConfig {
  /** 字段验证规则 */
  rules: ValidationRule[];
  /** 初始值 */
  initialValue?: string;
}

/**
 * 表单验证 Composable
 * @param fieldsConfig 字段配置对象
 * @returns 表单状态和方法
 */
export function useFormValidation<T extends Record<string, FieldConfig>>(fieldsConfig: T) {
  // 提取字段名类型
  type FieldNames = keyof T;
  
  // 错误状态
  const errors = reactive<Record<FieldNames, string>>(
    Object.keys(fieldsConfig).reduce((acc, key) => {
      acc[key as FieldNames] = '';
      return acc;
    }, {} as Record<FieldNames, string>)
  );
  
  // 验证触发状态（是否已触发过验证）
  const touched = reactive<Record<FieldNames, boolean>>(
    Object.keys(fieldsConfig).reduce((acc, key) => {
      acc[key as FieldNames] = false;
      return acc;
    }, {} as Record<FieldNames, boolean>)
  );
  
  /**
   * 验证单个字段
   * @param fieldName 字段名
   * @param value 字段值
   * @returns 是否验证通过
   */
  function validateField(fieldName: FieldNames, value: string): boolean {
    const config = fieldsConfig[fieldName];
    if (!config) return true;
    
    const error = validate(value, config.rules);
    errors[fieldName] = error;
    touched[fieldName] = true;
    
    return !error;
  }
  
  /**
   * 验证所有字段
   * @param values 字段值对象
   * @returns 是否全部验证通过
   */
  function validateAll(values: Record<FieldNames, string>): boolean {
    let allValid = true;
    
    for (const fieldName of Object.keys(fieldsConfig) as FieldNames[]) {
      const value = values[fieldName] || '';
      const isValid = validateField(fieldName, value);
      if (!isValid) allValid = false;
    }
    
    return allValid;
  }
  
  /**
   * 清除所有错误
   */
  function clearErrors(): void {
    for (const key of Object.keys(errors)) {
      errors[key as FieldNames] = '';
    }
  }
  
  /**
   * 清除单个字段错误
   */
  function clearFieldError(fieldName: FieldNames): void {
    errors[fieldName] = '';
  }
  
  /**
   * 重置验证状态
   */
  function reset(): void {
    clearErrors();
    for (const key of Object.keys(touched)) {
      touched[key as FieldNames] = false;
    }
  }
  
  /**
   * 检查是否有错误
   */
  const hasErrors = computed(() => {
    return Object.values(errors).some(error => !!error);
  });
  
  return {
    errors,
    touched,
    validateField,
    validateAll,
    clearErrors,
    clearFieldError,
    reset,
    hasErrors,
  };
}

/**
 * 创建名称验证规则
 * @param t i18n 翻译函数
 * @param entityType 实体类型（用于错误消息）
 * @returns 验证规则数组
 */
export function createNameRules(
  requiredMessage: string,
  invalidMessage: string
): ValidationRule[] {
  return [
    { required: true, message: requiredMessage },
    { pattern: NAME_REGEX, message: invalidMessage },
  ];
}

/**
 * 创建可选名称验证规则（非必填，但如果填写了需要符合格式）
 * @param invalidMessage 格式错误消息
 * @returns 验证规则数组
 */
export function createOptionalNameRules(invalidMessage: string): ValidationRule[] {
  return [
    { pattern: NAME_REGEX, message: invalidMessage },
  ];
}

/**
 * 简单的表单状态管理
 * 用于不需要复杂验证的简单表单
 */
export function useSimpleForm<T extends Record<string, unknown>>(initialValues: T) {
  const form = reactive({ ...initialValues }) as T;
  const isSubmitting = ref(false);
  const submitError = ref<string | null>(null);
  
  function resetForm(): void {
    Object.assign(form, initialValues);
    submitError.value = null;
  }
  
  async function handleSubmit(
    submitFn: (values: T) => Promise<void>,
    options?: { onSuccess?: () => void; onError?: (e: Error) => void }
  ): Promise<void> {
    isSubmitting.value = true;
    submitError.value = null;
    
    try {
      await submitFn(form);
      options?.onSuccess?.();
    } catch (e) {
      const error = e instanceof Error ? e : new Error(String(e));
      submitError.value = error.message;
      options?.onError?.(error);
    } finally {
      isSubmitting.value = false;
    }
  }
  
  return {
    form,
    isSubmitting,
    submitError,
    resetForm,
    handleSubmit,
  };
}
