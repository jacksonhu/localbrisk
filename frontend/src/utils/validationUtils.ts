/**
 * 通用验证工具函数
 * 统一名称、URL 等验证逻辑
 */

/**
 * 验证名称格式（字母开头，只能包含字母、数字、下划线、连字符）
 */
export const NAME_REGEX = /^[a-zA-Z][a-zA-Z0-9_-]*$/;

/**
 * 验证名称格式（允许中文）
 */
export const NAME_REGEX_WITH_CHINESE = /^[\u4e00-\u9fa5a-zA-Z][\u4e00-\u9fa5a-zA-Z0-9_-]*$/;

/**
 * 验证 URL 格式
 */
export const URL_REGEX = /^https?:\/\/.+/;

/**
 * 验证名称是否有效
 * @param name 名称
 * @param allowChinese 是否允许中文
 * @returns 验证结果
 */
export function isValidName(name: string, allowChinese = false): boolean {
  if (!name) return false;
  const regex = allowChinese ? NAME_REGEX_WITH_CHINESE : NAME_REGEX;
  return regex.test(name);
}

/**
 * 验证 URL 是否有效
 * @param url URL 字符串
 * @returns 验证结果
 */
export function isValidUrl(url: string): boolean {
  if (!url) return false;
  return URL_REGEX.test(url);
}

/**
 * 验证端口号是否有效
 * @param port 端口号
 * @returns 验证结果
 */
export function isValidPort(port: number | string): boolean {
  const portNum = typeof port === 'string' ? parseInt(port, 10) : port;
  return !isNaN(portNum) && portNum >= 1 && portNum <= 65535;
}

/**
 * 验证规则类型定义
 */
export interface ValidationRule {
  /** 是否必填 */
  required?: boolean;
  /** 最小长度 */
  minLength?: number;
  /** 最大长度 */
  maxLength?: number;
  /** 正则表达式 */
  pattern?: RegExp;
  /** 自定义验证函数 */
  validator?: (value: string) => boolean;
  /** 错误消息（或错误消息函数） */
  message: string | ((value: string) => string);
}

/**
 * 执行验证
 * @param value 要验证的值
 * @param rules 验证规则数组
 * @returns 第一个失败的错误消息，全部通过返回空字符串
 */
export function validate(value: string, rules: ValidationRule[]): string {
  for (const rule of rules) {
    // 必填验证
    if (rule.required && !value) {
      return typeof rule.message === 'function' ? rule.message(value) : rule.message;
    }
    
    // 如果值为空且不是必填，跳过后续验证
    if (!value && !rule.required) continue;
    
    // 最小长度验证
    if (rule.minLength !== undefined && value.length < rule.minLength) {
      return typeof rule.message === 'function' ? rule.message(value) : rule.message;
    }
    
    // 最大长度验证
    if (rule.maxLength !== undefined && value.length > rule.maxLength) {
      return typeof rule.message === 'function' ? rule.message(value) : rule.message;
    }
    
    // 正则验证
    if (rule.pattern && !rule.pattern.test(value)) {
      return typeof rule.message === 'function' ? rule.message(value) : rule.message;
    }
    
    // 自定义验证
    if (rule.validator && !rule.validator(value)) {
      return typeof rule.message === 'function' ? rule.message(value) : rule.message;
    }
  }
  
  return '';
}
