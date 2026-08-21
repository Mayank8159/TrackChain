// Native Server-Sent Events (SSE) client for TrackChain real-time alerts (tc.v1).

import type { DefectEvent, RealtimePayload } from "./types";

export type ConnectionStatusType = "connecting" | "connected" | "disconnected";
export type AlertStreamListener = (data: Partial<DefectEvent> | any) => void;
export type RealtimeListener = (payload: RealtimePayload) => void;
export type StatusListener = (status: ConnectionStatusType) => void;

class SSEClient {
  private eventSource: EventSource | null = null;
  private status: ConnectionStatusType = "disconnected";
  private alertListeners: Set<AlertStreamListener> = new Set();
  private realtimeListeners: Set<RealtimeListener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isConnecting = false;

  public getStatus(): ConnectionStatusType {
    return this.status;
  }

  public connect() {
    if (typeof window === "undefined") return;
    if (this.eventSource && this.eventSource.readyState === EventSource.OPEN) {
      return;
    }
    if (this.isConnecting) return;

    this.isConnecting = true;
    this.setStatus("connecting");

    const endpoint = process.env.NEXT_PUBLIC_API_BASE_URL
      ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/alerts/stream`
      : "/api/alerts/stream";

    try {
      if (this.eventSource) {
        this.eventSource.close();
      }

      this.eventSource = new EventSource(endpoint);

      this.eventSource.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.setStatus("connected");
      };

      // Listen for custom "defect_alert" event from FastAPI backend
      this.eventSource.addEventListener("defect_alert", (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data);
          this.notifyAlert(parsed);
          this.notifyRealtime({
            type: "defect",
            data: parsed,
            timestamp: new Date().toISOString(),
          });
        } catch {
          // ignore malformed packets
        }
      });

      // Listen for "ping" keepalive events
      this.eventSource.addEventListener("ping", () => {
        if (this.status !== "connected") {
          this.setStatus("connected");
        }
      });

      // Default message listener
      this.eventSource.onmessage = (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.event === "defect_alert" || parsed.defect_class) {
            this.notifyAlert(parsed.data || parsed);
          }
        } catch {
          // ignore
        }
      };

      this.eventSource.onerror = () => {
        this.isConnecting = false;
        this.setStatus("disconnected");
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        this.scheduleReconnect();
      };
    } catch {
      this.isConnecting = false;
      this.setStatus("disconnected");
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnecting = false;
    this.setStatus("disconnected");
  }

  public subscribeAlerts(listener: AlertStreamListener): () => void {
    this.alertListeners.add(listener);
    if (this.status === "disconnected" && !this.isConnecting) {
      this.connect();
    }
    return () => {
      this.alertListeners.delete(listener);
      this.checkAutoDisconnect();
    };
  }

  public subscribe(listener: RealtimeListener): () => void {
    this.realtimeListeners.add(listener);
    if (this.status === "disconnected" && !this.isConnecting) {
      this.connect();
    }
    return () => {
      this.realtimeListeners.delete(listener);
      this.checkAutoDisconnect();
    };
  }

  public subscribeStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  private setStatus(status: ConnectionStatusType) {
    if (this.status !== status) {
      this.status = status;
      this.statusListeners.forEach((fn) => {
        try {
          fn(status);
        } catch {}
      });
    }
  }

  private notifyAlert(data: any) {
    this.alertListeners.forEach((fn) => {
      try {
        fn(data);
      } catch {}
    });
  }

  private notifyRealtime(payload: RealtimePayload) {
    this.realtimeListeners.forEach((fn) => {
      try {
        fn(payload);
      } catch {}
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.alertListeners.size === 0 && this.realtimeListeners.size === 0) return;

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000);
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    }
  }

  private checkAutoDisconnect() {
    if (this.alertListeners.size === 0 && this.realtimeListeners.size === 0) {
      // Keep running or gracefully disconnect when no subscribers
    }
  }
}

export const sseClient = new SSEClient();
