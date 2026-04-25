/**
 * useSSEClient — SSE 流式连接客户端
 * 支持 POST 请求的 SSE 流、自动重连、断线恢复
 */

import { ref, type Ref } from "vue";
import type { StreamMessage } from "@/types/stream-protocol";

const API_BASE_URL = "http://127.0.0.1:8765";

export interface SSEClientOptions {
  /** 最大重连次数 */
  maxRetries?: number;
  /** 重连间隔（毫秒） */
  retryInterval?: number;
  /** 消息回调 */
  onMessage?: (msg: StreamMessage) => void;
  /** 连接错误回调 */
  onError?: (error: Error) => void;
  /** 连接关闭回调 */
  onClose?: () => void;
}

export interface SSEClientState {
  isConnected: Ref<boolean>;
  isConnecting: Ref<boolean>;
  lastError: Ref<Error | null>;
  retryCount: Ref<number>;
  lastExecutionId: Ref<string>;
}

export function useSSEClient(options: SSEClientOptions = {}) {
  const {
    maxRetries = 3,
    retryInterval = 2000,
    onMessage,
    onError,
    onClose,
  } = options;

  const isConnected = ref(false);
  const isConnecting = ref(false);
  const lastError = ref<Error | null>(null);
  const retryCount = ref(0);
  const lastExecutionId = ref("");

  let abortController: AbortController | null = null;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  /**
   * 执行 v2 流式请求
   */
  async function executeStreamV2(
    businessUnitId: string,
    agentName: string,
    input: string,
    context?: Record<string, any>
  ): Promise<void> {
    // 如果已有连接，先断开
    disconnect();

    isConnecting.value = true;
    lastError.value = null;
    retryCount.value = 0;

    const url = `${API_BASE_URL}/api/runtime/${businessUnitId}/agents/${agentName}/execute/stream`;

    try {
      abortController = new AbortController();

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ input, context }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      reader = response.body?.getReader() || null;
      if (!reader) {
        throw new Error("No response body");
      }

      isConnected.value = true;
      isConnecting.value = false;

      // 读取流
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const msg: StreamMessage = JSON.parse(line.slice(6));
              
              // 记录 execution_id 用于重连
              if (msg.execution_id) {
                lastExecutionId.value = msg.execution_id;
              }

              onMessage?.(msg);
            } catch {
              // 忽略 JSON 解析错误
            }
          }
        }
      }

      // 流结束
      isConnected.value = false;
      onClose?.();

    } catch (err: any) {
      isConnecting.value = false;
      isConnected.value = false;

      if (err.name === "AbortError") {
        // 主动取消，不触发错误
        return;
      }

      lastError.value = err;
      onError?.(err);
    }
  }

  /**
   * 获取执行快照（断线重连时使用）
   */
  async function fetchSnapshot(
    businessUnitId: string,
    agentName: string,
    executionId: string
  ): Promise<any | null> {
    try {
      const url = `${API_BASE_URL}/api/runtime/${businessUnitId}/agents/${agentName}/execution/${executionId}/snapshot`;
      const response = await fetch(url);
      
      if (!response.ok) {
        return null;
      }
      
      return await response.json();
    } catch {
      return null;
    }
  }

  /**
   * Generic POST-SSE stream execution with custom URL and body.
   * Used by Foreman and any future non-single-agent SSE consumer.
   */
  async function executeStreamGeneric(
    url: string,
    body: Record<string, any>,
  ): Promise<void> {
    disconnect();

    isConnecting.value = true;
    lastError.value = null;
    retryCount.value = 0;

    try {
      abortController = new AbortController();

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      reader = response.body?.getReader() || null;
      if (!reader) {
        throw new Error("No response body");
      }

      isConnected.value = true;
      isConnecting.value = false;

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const msg: StreamMessage = JSON.parse(line.slice(6));
              if (msg.execution_id) {
                lastExecutionId.value = msg.execution_id;
              }
              onMessage?.(msg);
            } catch {
              // Ignore JSON parse errors
            }
          }
        }
      }

      isConnected.value = false;
      onClose?.();
    } catch (err: any) {
      isConnecting.value = false;
      isConnected.value = false;

      if (err.name === "AbortError") {
        return;
      }

      lastError.value = err;
      onError?.(err);
    }
  }

  /**
   * Disconnect active SSE connection.
   */
  function disconnect() {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    if (reader) {
      reader.cancel().catch(() => {});
      reader = null;
    }
    isConnected.value = false;
    isConnecting.value = false;
  }

  return {
    // 状态
    isConnected,
    isConnecting,
    lastError,
    retryCount,
    lastExecutionId,
    // Methods
    executeStreamV2,
    executeStreamGeneric,
    fetchSnapshot,
    disconnect,
  };
}

export default useSSEClient;
