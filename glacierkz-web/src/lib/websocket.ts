export interface WSEvent {
  type: string;
  data: unknown;
  timestamp: string;
}

export type WSStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

export interface WSOptions {
  url: string;
  protocols?: string | string[];
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onMessage?: (event: WSEvent) => void;
  onError?: (error: Event) => void;
  onStatusChange?: (status: WSStatus) => void;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private protocols?: string | string[];
  private shouldReconnect: boolean;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private heartbeatInterval: number;
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Map<string, Set<(event: WSEvent) => void>> = new Map();
  private statusListeners: Set<(status: WSStatus) => void> = new Set();
  private _status: WSStatus = "disconnected";
  private closed = false;

  constructor(options: WSOptions) {
    this.url = options.url;
    this.protocols = options.protocols;
    this.shouldReconnect = options.reconnect !== false;
    this.reconnectInterval = options.reconnectInterval || 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.heartbeatInterval = options.heartbeatInterval || 30000;

    if (options.onOpen) this.onOpen(options.onOpen);
    if (options.onClose) this.onCloseEvent(options.onClose);
    if (options.onMessage) this.on("*", options.onMessage);
    if (options.onError) this.onErrorEvent(options.onError);
    if (options.onStatusChange) this.onStatusChange(options.onStatusChange);
  }

  get status(): WSStatus {
    return this._status;
  }

  get connected(): boolean {
    return this._status === "connected";
  }

  private setStatus(status: WSStatus): void {
    this._status = status;
    this.statusListeners.forEach((listener) => {
      try {
        listener(status);
      } catch {
        // swallow listener errors
      }
    });
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.closed = false;
    this.setStatus("connecting");

    try {
      this.ws = new WebSocket(this.url, this.protocols);
    } catch {
      this.setStatus("disconnected");
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus("connected");
      this.startHeartbeat();
      this.emit({ type: "connection", data: { status: "connected" }, timestamp: new Date().toISOString() });
    };

    this.ws.onclose = (_event) => {
      this.stopHeartbeat();
      if (this.closed) {
        this.setStatus("disconnected");
        return;
      }
      this.setStatus("disconnected");
      this.emit({ type: "connection", data: { status: "disconnected" }, timestamp: new Date().toISOString() });
      this.scheduleReconnect();
    };

    this.ws.onerror = (_error) => {
      this.emit({ type: "error", data: { message: "WebSocket error" }, timestamp: new Date().toISOString() });
      this.statusListeners.forEach((listener) => {
        try {
          listener(this._status);
        } catch {
          // swallow
        }
      });
    };

    this.ws.onmessage = (messageEvent) => {
      try {
        const event: WSEvent = JSON.parse(messageEvent.data);
        this.emit(event);
      } catch {
        this.emit({
          type: "raw",
          data: messageEvent.data,
          timestamp: new Date().toISOString(),
        });
      }
    };
  }

  disconnect(): void {
    this.closed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
    this.setStatus("disconnected");
  }

  send(data: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }
    this.ws.send(typeof data === "string" ? data : JSON.stringify(data));
  }

  on(type: string, callback: (event: WSEvent) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(callback);
    return () => {
      this.listeners.get(type)?.delete(callback);
    };
  }

  onOpen(callback: () => void): () => void {
    const handler = (e: WSEvent) => {
      if (e.type === "connection" && (e.data as { status: string }).status === "connected") {
        callback();
      }
    };
    return this.on("*", handler);
  }

  onCloseEvent(callback: (event: CloseEvent) => void): () => void {
    return this.on("connection", (e) => {
      if ((e.data as { status: string }).status === "disconnected") {
        callback(new CloseEvent("close"));
      }
    });
  }

  onErrorEvent(callback: (error: Event) => void): () => void {
    return this.on("error", () => {
      callback(new Event("error"));
    });
  }

  onStatusChange(callback: (status: WSStatus) => void): () => void {
    this.statusListeners.add(callback);
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  private emit(event: WSEvent): void {
    const typeListeners = this.listeners.get(event.type);
    if (typeListeners) {
      typeListeners.forEach((cb) => {
        try {
          cb(event);
        } catch {
          // swallow listener errors
        }
      });
    }
    const allListeners = this.listeners.get("*");
    if (allListeners) {
      allListeners.forEach((cb) => {
        try {
          cb(event);
        } catch {
          // swallow listener errors
        }
      });
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: "ping", timestamp: Date.now() });
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.closed) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus("disconnected");
      return;
    }

    this.setStatus("reconnecting");
    this.reconnectAttempts++;

    const delay = Math.min(
      this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1),
      30000
    );

    this.reconnectTimer = setTimeout(() => {
      if (!this.closed) {
        this.connect();
      }
    }, delay);
  }

  destroy(): void {
    this.disconnect();
    this.listeners.clear();
    this.statusListeners.clear();
  }
}

export function createWebSocket(url: string, options?: Partial<WSOptions>): WebSocketClient {
  return new WebSocketClient({ url, reconnect: true, ...options });
}

export function subscribeToEvents(
  url: string,
  eventType: string,
  callback: (data: unknown) => void
): () => void {
  const client = createWebSocket(url, {
    onMessage: (event) => {
      if (event.type === eventType) {
        callback(event.data);
      }
    },
  });
  client.connect();
  return () => client.destroy();
}
