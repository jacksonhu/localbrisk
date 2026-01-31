/**
 * 通用格式化工具函数
 * 统一日期、文件大小等格式化逻辑，避免各组件重复实现
 */

/**
 * 格式化日期字符串
 * @param dateStr ISO 日期字符串
 * @param options 格式化选项
 * @returns 格式化后的日期字符串，无效输入返回 '-'
 */
export function formatDate(
  dateStr?: string | null,
  options?: {
    showTime?: boolean;
    timeFormat?: '12h' | '24h';
  }
): string {
  if (!dateStr) return '-';
  
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    
    const { showTime = true, timeFormat = '24h' } = options || {};
    
    const dateFormatted = date.toLocaleDateString();
    
    if (!showTime) return dateFormatted;
    
    const timeOptions: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      hour12: timeFormat === '12h',
    };
    
    const timeFormatted = date.toLocaleTimeString([], timeOptions);
    return `${dateFormatted} ${timeFormatted}`;
  } catch {
    return dateStr;
  }
}

/**
 * 格式化文件大小
 * @param bytes 字节数
 * @param decimals 小数位数
 * @returns 格式化后的文件大小字符串
 */
export function formatFileSize(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 B';
  if (!bytes || bytes < 0) return '-';
  
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${units[i]}`;
}

/**
 * 格式化数字（添加千分位分隔符）
 * @param num 数字
 * @returns 格式化后的数字字符串
 */
export function formatNumber(num?: number | null): string {
  if (num === undefined || num === null) return '-';
  return num.toLocaleString();
}

/**
 * 截断文本并添加省略号
 * @param text 原始文本
 * @param maxLength 最大长度
 * @returns 截断后的文本
 */
export function truncateText(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * 格式化相对时间（如 "5 分钟前"）
 * @param dateStr ISO 日期字符串
 * @returns 相对时间字符串
 */
export function formatRelativeTime(dateStr?: string | null): string {
  if (!dateStr) return '-';
  
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;
    if (diffHour < 24) return `${diffHour} 小时前`;
    if (diffDay < 7) return `${diffDay} 天前`;
    
    return formatDate(dateStr, { showTime: false });
  } catch {
    return dateStr;
  }
}

/**
 * 获取文件扩展名
 * @param filename 文件名
 * @returns 小写的扩展名（不含点），无扩展名返回空字符串
 */
export function getFileExtension(filename: string): string {
  if (!filename) return '';
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === 0) return '';
  return filename.slice(lastDot + 1).toLowerCase();
}

/**
 * 获取不含扩展名的文件名
 * @param filename 文件名
 * @returns 不含扩展名的文件名
 */
export function getFileNameWithoutExtension(filename: string): string {
  if (!filename) return '';
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === 0) return filename;
  return filename.slice(0, lastDot);
}
