/**
 * 文件浏览器组合式函数
 * 提供文件列表、目录导航、文件预览等公共功能
 */
import { ref, computed } from 'vue';
import { 
  listLocalDirectory, 
  readLocalTextFile, 
  readLocalBinaryFile,
  type FileInfo 
} from '@/services/fileService';
import { join } from '@tauri-apps/api/path';

// 支持预览的文件类型
export const PREVIEWABLE_EXTENSIONS = new Set([
  // 图片
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico',
  // PDF
  'pdf',
  // 文本/代码
  'txt', 'log', 'md', 'markdown',
  'js', 'ts', 'jsx', 'tsx', 'vue', 'py', 'java', 'go', 'rs', 'c', 'cpp', 'h',
  'cs', 'rb', 'php', 'swift', 'kt', 'scala', 'sql', 'sh', 'bash', 'zsh', 'ps1',
  'html', 'css', 'scss', 'less', 'json', 'yaml', 'yml', 'xml', 'toml', 'ini', 'conf', 'env',
  // 表格
  'csv', 'xlsx', 'xls',
  // Office 文档
  'doc', 'docx', 'ppt', 'pptx',
]);

// 二进制文件类型
export const BINARY_EXTENSIONS = new Set([
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico',
  'pdf', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt',
]);

// 文件图标颜色映射
export const FILE_ICON_COLORS: Record<string, string> = {
  // 代码文件
  md: 'text-blue-500',
  yaml: 'text-yellow-500',
  yml: 'text-yellow-500',
  json: 'text-orange-500',
  py: 'text-green-500',
  js: 'text-yellow-500',
  ts: 'text-blue-500',
  vue: 'text-green-500',
  jsx: 'text-cyan-500',
  tsx: 'text-blue-500',
  // 文档
  pdf: 'text-red-500',
  doc: 'text-blue-500',
  docx: 'text-blue-500',
  // 表格
  xls: 'text-green-500',
  xlsx: 'text-green-500',
  csv: 'text-green-600',
  // 演示文稿
  ppt: 'text-orange-500',
  pptx: 'text-orange-500',
  // 图片
  jpg: 'text-purple-500',
  jpeg: 'text-purple-500',
  png: 'text-purple-500',
  gif: 'text-purple-500',
  webp: 'text-purple-500',
  svg: 'text-purple-500',
  // 压缩文件
  zip: 'text-yellow-600',
  rar: 'text-yellow-600',
  '7z': 'text-yellow-600',
  // 数据文件
  parquet: 'text-blue-600',
};

// ============= 公共工具函数 =============

/**
 * 检查文件是否可预览
 */
export function isFilePreviewable(fileName: string): boolean {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  return PREVIEWABLE_EXTENSIONS.has(ext);
}

/**
 * 检查文件是否为二进制文件
 */
export function isBinaryFile(fileName: string): boolean {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  return BINARY_EXTENSIONS.has(ext);
}

/**
 * 获取文件图标颜色
 */
export function getFileIconColor(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  return FILE_ICON_COLORS[ext] || 'text-gray-500';
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null || bytes === 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
}

/**
 * 格式化日期
 */
export function formatDate(dateStr?: string): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return dateStr;
  }
}

/**
 * 读取本地文件内容（根据文件类型自动选择二进制或文本模式）
 */
export async function readLocalFileContent(filePath: string): Promise<string | ArrayBuffer> {
  const ext = filePath.split('.').pop()?.toLowerCase() || '';
  if (BINARY_EXTENSIONS.has(ext)) {
    return await readLocalBinaryFile(filePath);
  } else {
    return await readLocalTextFile(filePath);
  }
}

// ============= Composable =============

export interface UseFileBrowserOptions {
  /** 根目录路径 */
  rootPath: string;
  /** 是否显示隐藏文件 */
  showHidden?: boolean;
  /** 文件过滤函数 */
  fileFilter?: (file: FileInfo) => boolean;
}

export interface FileBrowserState {
  files: FileInfo[];
  loading: boolean;
  error: string | null;
  currentPath: string;
}

export function useFileBrowser() {
  // 状态
  const files = ref<FileInfo[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const currentPath = ref('');
  const rootPath = ref('');

  // 路径段
  const pathSegments = computed(() => {
    if (!currentPath.value) return [];
    return currentPath.value.split('/').filter(Boolean);
  });

  // 排序后的文件列表（文件夹优先）
  const sortedFiles = computed(() => {
    return [...files.value].sort((a, b) => {
      if (a.is_directory && !b.is_directory) return -1;
      if (!a.is_directory && b.is_directory) return 1;
      return a.name.localeCompare(b.name);
    });
  });

  // 初始化
  function init(path: string) {
    rootPath.value = path;
    currentPath.value = '';
    files.value = [];
    error.value = null;
  }

  // 刷新文件列表
  async function refreshFiles() {
    if (!rootPath.value) {
      error.value = 'Root path not set';
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      const fullPath = currentPath.value 
        ? await join(rootPath.value, currentPath.value)
        : rootPath.value;
      
      const entries = await listLocalDirectory(fullPath);
      files.value = entries;
    } catch (e) {
      console.error('Failed to list directory:', e);
      error.value = e instanceof Error ? e.message : 'Failed to list directory';
      files.value = [];
    } finally {
      loading.value = false;
    }
  }

  // 导航到根目录
  function navigateToRoot() {
    currentPath.value = '';
    refreshFiles();
  }

  // 导航到指定路径段
  function navigateToSegment(index: number) {
    const newPath = pathSegments.value.slice(0, index + 1).join('/');
    currentPath.value = newPath;
    refreshFiles();
  }

  // 进入文件夹
  function navigateToFolder(file: FileInfo) {
    if (!file.is_directory) return;
    currentPath.value = currentPath.value 
      ? `${currentPath.value}/${file.name}` 
      : file.name;
    refreshFiles();
  }

  // 返回上级目录
  function navigateUp() {
    if (!currentPath.value) return;
    const segments = pathSegments.value;
    if (segments.length > 0) {
      segments.pop();
      currentPath.value = segments.join('/');
      refreshFiles();
    }
  }

  // 获取文件完整路径
  async function getFilePath(file: FileInfo): Promise<string> {
    const basePath = currentPath.value 
      ? await join(rootPath.value, currentPath.value)
      : rootPath.value;
    return await join(basePath, file.name);
  }

  // 读取文件内容
  async function readFileContent(file: FileInfo): Promise<string | ArrayBuffer> {
    const filePath = await getFilePath(file);
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    
    if (BINARY_EXTENSIONS.has(ext)) {
      return await readLocalBinaryFile(filePath);
    } else {
      return await readLocalTextFile(filePath);
    }
  }

  // 检查文件是否可预览
  function isPreviewable(fileName: string): boolean {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return PREVIEWABLE_EXTENSIONS.has(ext);
  }

  // 获取文件图标颜色
  function getFileIconColor(fileName: string): string {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return FILE_ICON_COLORS[ext] || 'text-gray-500';
  }

  // 格式化文件大小
  function formatFileSize(bytes?: number): string {
    if (bytes === undefined || bytes === null || bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
  }

  // 格式化日期
  function formatDate(dateStr?: string): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  }

  return {
    // 状态
    files,
    sortedFiles,
    loading,
    error,
    currentPath,
    rootPath,
    pathSegments,
    
    // 方法
    init,
    refreshFiles,
    navigateToRoot,
    navigateToSegment,
    navigateToFolder,
    navigateUp,
    getFilePath,
    readFileContent,
    isPreviewable,
    getFileIconColor,
    formatFileSize,
    formatDate,
  };
}

export type { FileInfo };
