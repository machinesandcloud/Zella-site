export type WSMessage = {
  channel: string;
  timestamp: string;
  type?: string;
  [key: string]: unknown;
};

export type WSConnectionOptions = {
  onMessage: (msg: WSMessage) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Event) => void;
  maxRetries?: number;
  enableHeartbeat?: boolean;
};

// Exponential backoff configuration
const INITIAL_RETRY_DELAY = 1000; // 1 second
const MAX_RETRY_DELAY = 30000; // 30 seconds
const BACKOFF_MULTIPLIER = 2;
const HEARTBEAT_INTERVAL = 25000; // 25 seconds (under server's 30s ping)

class WebSocketConnection {
  private ws: WebSocket | null = null;
  private path: string;
  private options: WSConnectionOptions;
  private retryCount = 0;
  private maxRetries: number;
  private retryTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private isIntentionallyClosed = false;
  private lastPongTime = Date.now();

  constructor(path: string, options: WSConnectionOptions) {
    this.path = path;
    this.options = options;
    this.maxRetries = options.maxRetries ?? 10;
    this.connect();
  }

  private connect(): void {
    if (this.isIntentionallyClosed) return;

    const base = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

    try {
      this.ws = new WebSocket(`${base}${this.path}`);
    } catch (error) {
      console.error("WebSocket creation failed:", error);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log(`WebSocket connected: ${this.path}`);
      this.retryCount = 0;
      this.lastPongTime = Date.now();
      this.options.onConnected?.();

      if (this.options.enableHeartbeat !== false) {
        this.startHeartbeat();
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSMessage;

        // Handle heartbeat responses
        if (data.type === "ping" || data.type === "pong") {
          this.lastPongTime = Date.now();
          // Respond to server pings with pong
          if (data.type === "ping" && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "pong", timestamp: new Date().toISOString() }));
          }
          return;
        }

        this.options.onMessage(data);
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onerror = (error) => {
      console.warn(`WebSocket error on ${this.path}:`, error);
      this.options.onError?.(error);
    };

    this.ws.onclose = (event) => {
      console.log(`WebSocket closed: ${this.path} (code: ${event.code}, reason: ${event.reason})`);
      this.stopHeartbeat();
      this.options.onDisconnected?.();

      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.isIntentionallyClosed || this.retryCount >= this.maxRetries) {
      if (this.retryCount >= this.maxRetries) {
        console.error(`WebSocket max retries (${this.maxRetries}) reached for ${this.path}`);
      }
      return;
    }

    const delay = Math.min(
      INITIAL_RETRY_DELAY * Math.pow(BACKOFF_MULTIPLIER, this.retryCount),
      MAX_RETRY_DELAY
    );

    console.log(`WebSocket reconnecting in ${delay}ms (attempt ${this.retryCount + 1}/${this.maxRetries})`);

    this.retryTimeout = setTimeout(() => {
      this.retryCount++;
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        // Check if we've received a response recently
        const timeSinceLastPong = Date.now() - this.lastPongTime;
        if (timeSinceLastPong > HEARTBEAT_INTERVAL * 2) {
          console.warn(`WebSocket heartbeat timeout on ${this.path}, reconnecting...`);
          this.ws.close(4000, "Heartbeat timeout");
          return;
        }

        // Send client-side ping
        try {
          this.ws.send(JSON.stringify({ type: "ping", timestamp: new Date().toISOString() }));
        } catch (error) {
          console.warn("Failed to send heartbeat:", error);
        }
      }
    }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  public close(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();

    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, "Client closed");
      this.ws = null;
    }
  }

  public send(data: unknown): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(data));
        return true;
      } catch (error) {
        console.warn("WebSocket send failed:", error);
      }
    }
    return false;
  }

  public get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  public get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Simple function for backward compatibility
export const connectWebSocket = (path: string, onMessage: (msg: WSMessage) => void): WebSocketConnection => {
  return new WebSocketConnection(path, { onMessage });
};

// Enhanced connection with full options
export const createWebSocketConnection = (path: string, options: WSConnectionOptions): WebSocketConnection => {
  return new WebSocketConnection(path, options);
};

export { WebSocketConnection };
