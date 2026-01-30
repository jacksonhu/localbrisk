/**
 * 文件服务
 * 处理本地文件系统和 S3 存储的文件操作
 */

import { invoke } from "@tauri-apps/api/core";

// ==================== 类型定义 ====================

export interface FileInfo {
  name: string;
  is_directory: boolean;
  size?: number;
  modified_time?: string;
  created_time?: string;
  readonly?: boolean;
  owner?: string;
}

export interface S3Config {
  endpoint: string;
  bucket: string;
  accessKey: string;
  secretKey: string;
  region?: string;
}

// ==================== 本地文件系统操作 ====================

/**
 * 检查是否在 Tauri 环境中运行
 * Tauri 2.x 使用 __TAURI_INTERNALS__ 而不是 __TAURI__
 */
export function isTauriEnv(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  // Tauri 2.x 检测方式
  if ('__TAURI_INTERNALS__' in window) {
    return true;
  }
  // Tauri 1.x 兼容检测
  if ('__TAURI__' in window) {
    return true;
  }
  return false;
}

/**
 * 列出目录内容（本地文件系统）
 * @param path 目录路径
 */
export async function listLocalDirectory(path: string): Promise<FileInfo[]> {
  if (!isTauriEnv()) {
    console.warn('Not in Tauri environment, returning mock data');
    return getMockFiles();
  }
  
  try {
    const files = await invoke<FileInfo[]>('list_directory', { path });
    return files;
  } catch (error) {
    console.error('Failed to list directory:', error);
    throw error;
  }
}

/**
 * 创建目录（本地文件系统）
 * @param path 目录路径
 */
export async function createLocalDirectory(path: string): Promise<void> {
  if (!isTauriEnv()) {
    console.warn('Not in Tauri environment');
    return;
  }
  
  try {
    await invoke('create_directory', { path });
  } catch (error) {
    console.error('Failed to create directory:', error);
    throw error;
  }
}

/**
 * 删除文件或目录（本地文件系统）
 * @param path 文件或目录路径
 */
export async function deleteLocalPath(path: string): Promise<void> {
  if (!isTauriEnv()) {
    console.warn('Not in Tauri environment');
    return;
  }
  
  try {
    await invoke('delete_path', { path });
  } catch (error) {
    console.error('Failed to delete path:', error);
    throw error;
  }
}

/**
 * 检查路径是否存在
 * @param path 路径
 */
export async function pathExists(path: string): Promise<boolean> {
  if (!isTauriEnv()) {
    return true;
  }
  
  try {
    return await invoke<boolean>('path_exists', { path });
  } catch (error) {
    console.error('Failed to check path:', error);
    return false;
  }
}

/**
 * 获取文件信息
 * @param path 文件路径
 */
export async function getFileInfo(path: string): Promise<FileInfo> {
  if (!isTauriEnv()) {
    throw new Error('Not in Tauri environment');
  }
  
  try {
    return await invoke<FileInfo>('get_file_info', { path });
  } catch (error) {
    console.error('Failed to get file info:', error);
    throw error;
  }
}

/**
 * 读取文本文件
 * @param path 文件路径
 */
export async function readTextFile(path: string): Promise<string> {
  if (!isTauriEnv()) {
    throw new Error('Not in Tauri environment');
  }
  
  try {
    return await invoke<string>('read_text_file', { path });
  } catch (error) {
    console.error('Failed to read file:', error);
    throw error;
  }
}

/**
 * 读取本地文本文件（别名，供外部使用）
 */
export const readLocalTextFile = readTextFile;

/**
 * 读取二进制文件（返回 ArrayBuffer）
 * @param path 文件路径
 */
export async function readBinaryFile(path: string): Promise<ArrayBuffer> {
  if (!isTauriEnv()) {
    throw new Error('Not in Tauri environment');
  }
  
  try {
    // 后端返回 Base64 编码的字符串
    const base64 = await invoke<string>('read_binary_file', { path });
    
    // 解码 Base64 为 ArrayBuffer
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  } catch (error) {
    console.error('Failed to read binary file:', error);
    throw error;
  }
}

/**
 * 读取本地二进制文件（别名，供外部使用）
 */
export const readLocalBinaryFile = readBinaryFile;

/**
 * 写入文本文件
 * @param path 文件路径
 * @param content 文件内容
 */
export async function writeTextFile(path: string, content: string): Promise<void> {
  if (!isTauriEnv()) {
    throw new Error('Not in Tauri environment');
  }
  
  try {
    await invoke('write_text_file', { path, content });
  } catch (error) {
    console.error('Failed to write file:', error);
    throw error;
  }
}

// ==================== S3 存储操作 ====================

/**
 * S3 客户端类
 * 使用 AWS SDK v4 签名实现基本的 S3 操作
 */
export class S3Client {
  private config: S3Config;
  
  constructor(config: S3Config) {
    this.config = config;
  }
  
  /**
   * 生成 AWS v4 签名
   */
  private async generateSignature(
    method: string,
    path: string,
    queryParams: Record<string, string> = {},
    headers: Record<string, string> = {},
    payload: string = ''
  ): Promise<{ headers: Record<string, string>; url: string }> {
    const region = this.config.region || 'us-east-1';
    const service = 's3';
    const now = new Date();
    const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '');
    const dateStamp = amzDate.slice(0, 8);
    
    // 构建 URL
    let url = `${this.config.endpoint}/${this.config.bucket}${path}`;
    const queryString = Object.entries(queryParams)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .sort()
      .join('&');
    if (queryString) {
      url += `?${queryString}`;
    }
    
    // 规范请求头
    const host = new URL(this.config.endpoint).host;
    const signedHeaders: Record<string, string> = {
      'host': host,
      'x-amz-date': amzDate,
      'x-amz-content-sha256': await this.sha256(payload),
      ...headers,
    };
    
    // 规范请求
    const sortedHeaderKeys = Object.keys(signedHeaders).sort();
    const canonicalHeaders = sortedHeaderKeys
      .map(k => `${k.toLowerCase()}:${signedHeaders[k].trim()}`)
      .join('\n') + '\n';
    const signedHeadersStr = sortedHeaderKeys.map(k => k.toLowerCase()).join(';');
    
    const canonicalQueryString = Object.entries(queryParams)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
    
    const canonicalRequest = [
      method,
      path || '/',
      canonicalQueryString,
      canonicalHeaders,
      signedHeadersStr,
      await this.sha256(payload),
    ].join('\n');
    
    // 创建待签名字符串
    const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;
    const stringToSign = [
      'AWS4-HMAC-SHA256',
      amzDate,
      credentialScope,
      await this.sha256(canonicalRequest),
    ].join('\n');
    
    // 计算签名
    const kDate = await this.hmacSha256(`AWS4${this.config.secretKey}`, dateStamp);
    const kRegion = await this.hmacSha256(kDate, region);
    const kService = await this.hmacSha256(kRegion, service);
    const kSigning = await this.hmacSha256(kService, 'aws4_request');
    const signature = await this.hmacSha256Hex(kSigning, stringToSign);
    
    // 构建授权头
    const authorization = `AWS4-HMAC-SHA256 Credential=${this.config.accessKey}/${credentialScope}, SignedHeaders=${signedHeadersStr}, Signature=${signature}`;
    
    return {
      headers: {
        ...signedHeaders,
        'Authorization': authorization,
      },
      url,
    };
  }
  
  /**
   * SHA256 哈希
   */
  private async sha256(message: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hashBuffer))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
  
  /**
   * HMAC-SHA256
   */
  private async hmacSha256(key: string | ArrayBuffer, message: string): Promise<ArrayBuffer> {
    const encoder = new TextEncoder();
    const keyData = typeof key === 'string' ? encoder.encode(key) : key;
    const cryptoKey = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    return crypto.subtle.sign('HMAC', cryptoKey, encoder.encode(message));
  }
  
  /**
   * HMAC-SHA256 (返回十六进制字符串)
   */
  private async hmacSha256Hex(key: ArrayBuffer, message: string): Promise<string> {
    const result = await this.hmacSha256(key, message);
    return Array.from(new Uint8Array(result))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
  
  /**
   * 列出对象（支持前缀过滤）
   * @param prefix 前缀（相当于目录路径）
   * @param delimiter 分隔符，通常为 '/'
   */
  async listObjects(prefix: string = '', delimiter: string = '/'): Promise<FileInfo[]> {
    try {
      const queryParams: Record<string, string> = {
        'list-type': '2',
      };
      
      if (prefix) {
        queryParams['prefix'] = prefix;
      }
      if (delimiter) {
        queryParams['delimiter'] = delimiter;
      }
      
      const { headers, url } = await this.generateSignature('GET', '/', queryParams);
      
      const response = await fetch(url, {
        method: 'GET',
        headers,
      });
      
      if (!response.ok) {
        throw new Error(`S3 request failed: ${response.status} ${response.statusText}`);
      }
      
      const text = await response.text();
      return this.parseListObjectsResponse(text, prefix);
    } catch (error) {
      console.error('Failed to list S3 objects:', error);
      throw error;
    }
  }
  
  /**
   * 解析 ListObjectsV2 响应
   */
  private parseListObjectsResponse(xml: string, prefix: string): FileInfo[] {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    const files: FileInfo[] = [];
    
    // 解析公共前缀（文件夹）
    const commonPrefixes = doc.querySelectorAll('CommonPrefixes > Prefix');
    commonPrefixes.forEach(node => {
      const fullPath = node.textContent || '';
      // 移除前缀部分，获取文件夹名
      const relativePath = fullPath.slice(prefix.length);
      const folderName = relativePath.replace(/\/$/, ''); // 移除末尾斜杠
      
      if (folderName) {
        files.push({
          name: folderName,
          is_directory: true,
        });
      }
    });
    
    // 解析文件
    const contents = doc.querySelectorAll('Contents');
    contents.forEach(node => {
      const key = node.querySelector('Key')?.textContent || '';
      const size = node.querySelector('Size')?.textContent;
      const lastModified = node.querySelector('LastModified')?.textContent;
      
      // 移除前缀部分，获取文件名
      const relativePath = key.slice(prefix.length);
      
      // 跳过目录标记（以 / 结尾）和空路径
      if (!relativePath || relativePath.endsWith('/')) {
        return;
      }
      
      // 如果包含斜杠，说明是子目录中的文件，跳过
      if (relativePath.includes('/')) {
        return;
      }
      
      files.push({
        name: relativePath,
        is_directory: false,
        size: size ? parseInt(size, 10) : undefined,
        modified_time: lastModified || undefined,
      });
    });
    
    // 排序：文件夹优先
    files.sort((a, b) => {
      if (a.is_directory && !b.is_directory) return -1;
      if (!a.is_directory && b.is_directory) return 1;
      return a.name.localeCompare(b.name);
    });
    
    return files;
  }
  
  /**
   * 删除对象
   * @param key 对象键
   */
  async deleteObject(key: string): Promise<void> {
    try {
      const path = `/${encodeURIComponent(key)}`;
      const { headers, url } = await this.generateSignature('DELETE', path);
      
      const response = await fetch(url, {
        method: 'DELETE',
        headers,
      });
      
      if (!response.ok && response.status !== 204) {
        throw new Error(`S3 delete failed: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to delete S3 object:', error);
      throw error;
    }
  }
  
  /**
   * 创建"文件夹"（实际上是创建一个以 / 结尾的空对象）
   * @param prefix 文件夹路径
   */
  async createFolder(prefix: string): Promise<void> {
    try {
      const folderKey = prefix.endsWith('/') ? prefix : `${prefix}/`;
      const path = `/${encodeURIComponent(folderKey)}`;
      const { headers, url } = await this.generateSignature('PUT', path, {}, {
        'Content-Length': '0',
      });
      
      const response = await fetch(url, {
        method: 'PUT',
        headers,
        body: '',
      });
      
      if (!response.ok) {
        throw new Error(`S3 create folder failed: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to create S3 folder:', error);
      throw error;
    }
  }
}

// ==================== 统一接口 ====================

export interface VolumeFileService {
  listFiles(subPath?: string): Promise<FileInfo[]>;
  createFolder(name: string, subPath?: string): Promise<void>;
  deleteFile(name: string, subPath?: string): Promise<void>;
}

/**
 * 创建本地 Volume 文件服务
 * @param basePath Volume 的基础路径
 */
export function createLocalVolumeService(basePath: string): VolumeFileService {
  // 规范化路径分隔符
  const normalizedBase = basePath.replace(/\\/g, '/');
  
  return {
    async listFiles(subPath = ''): Promise<FileInfo[]> {
      const fullPath = subPath 
        ? `${normalizedBase}/${subPath}`.replace(/\/+/g, '/')
        : normalizedBase;
      
      return listLocalDirectory(fullPath);
    },
    
    async createFolder(name: string, subPath = ''): Promise<void> {
      const baseDirPath = subPath 
        ? `${normalizedBase}/${subPath}`.replace(/\/+/g, '/')
        : normalizedBase;
      const fullPath = `${baseDirPath}/${name}`;
      
      return createLocalDirectory(fullPath);
    },
    
    async deleteFile(name: string, subPath = ''): Promise<void> {
      const baseDirPath = subPath 
        ? `${normalizedBase}/${subPath}`.replace(/\/+/g, '/')
        : normalizedBase;
      const fullPath = `${baseDirPath}/${name}`;
      
      return deleteLocalPath(fullPath);
    },
  };
}

/**
 * 创建 S3 Volume 文件服务
 * @param config S3 配置
 * @param basePrefix 基础前缀（相当于 Volume 在 bucket 中的根目录）
 */
export function createS3VolumeService(config: S3Config, basePrefix: string = ''): VolumeFileService {
  const client = new S3Client(config);
  // 确保前缀以 / 结尾（如果不为空）
  const normalizedPrefix = basePrefix ? (basePrefix.endsWith('/') ? basePrefix : `${basePrefix}/`) : '';
  
  return {
    async listFiles(subPath = ''): Promise<FileInfo[]> {
      const prefix = subPath 
        ? `${normalizedPrefix}${subPath}/`.replace(/\/+/g, '/')
        : normalizedPrefix;
      
      return client.listObjects(prefix);
    },
    
    async createFolder(name: string, subPath = ''): Promise<void> {
      const basePrefixPath = subPath 
        ? `${normalizedPrefix}${subPath}/`.replace(/\/+/g, '/')
        : normalizedPrefix;
      const folderKey = `${basePrefixPath}${name}/`;
      
      return client.createFolder(folderKey);
    },
    
    async deleteFile(name: string, subPath = ''): Promise<void> {
      const basePrefixPath = subPath 
        ? `${normalizedPrefix}${subPath}/`.replace(/\/+/g, '/')
        : normalizedPrefix;
      const key = `${basePrefixPath}${name}`;
      
      return client.deleteObject(key);
    },
  };
}

// ==================== Mock 数据（用于非 Tauri 环境） ====================

function getMockFiles(): FileInfo[] {
  return [
    { name: 'documents', is_directory: true },
    { name: 'images', is_directory: true },
    { name: 'data', is_directory: true },
    { name: 'report.pdf', is_directory: false, size: 2621440, modified_time: '2024-01-15T10:30:00Z', owner: 'admin' },
    { name: 'data.csv', is_directory: false, size: 524288, modified_time: '2024-01-14T15:20:00Z', owner: 'admin' },
    { name: 'config.json', is_directory: false, size: 2048, modified_time: '2024-01-13T09:00:00Z', owner: 'system' },
  ];
}

export default {
  isTauriEnv,
  listLocalDirectory,
  createLocalDirectory,
  deleteLocalPath,
  pathExists,
  getFileInfo,
  readTextFile,
  writeTextFile,
  createLocalVolumeService,
  createS3VolumeService,
  S3Client,
};
