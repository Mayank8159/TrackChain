// Websocket/SSE client wrapper with reconnect/backoff.

import type { RealtimePayload } from "./types";

type Listener = (payload: RealtimePayload) => void;
type StatusListener = (status: "connected" | "connecting" | "disconnected") => void;

class RealtimeClient {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners: Set<Listener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private simulationInterval: ReturnType<typeof setInterval> | null = null;
  private status: "connected" | "connecting" | "disconnected" = "disconnected";

  constructor() {
    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/^http/, "ws") ||
      "ws://127.0.0.1:8000";
    this.url = `${baseUrl}/ws/telemetry`;
  }

  public connect() {
    if (typeof window === "undefined") return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setStatus("connecting");

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.setStatus("connected");
        this.reconnectAttempts = 0;
        this.stopSimulation();
      };

      this.ws.onmessage = (event) => {
        try {
          const payload: RealtimePayload = JSON.parse(event.data);
          this.notify(payload);
        } catch {
          // ignore malformed packets
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };

      this.ws.onclose = () => {
        this.setStatus("disconnected");
        this.scheduleReconnect();
      };
    } catch {
      this.setStatus("disconnected");
      this.scheduleReconnect();
    }
  }

  public subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    if (this.status === "disconnected") {
      this.connect();
    }
    return () => {
      this.listeners.delete(listener);
    };
  }

  public subscribeStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  public getStatus() {
    return this.status;
  }

  private setStatus(status: "connected" | "connecting" | "disconnected") {
    this.status = status;
    this.statusListeners.forEach((fn) => fn(status));
  }

  private notify(payload: RealtimePayload) {
    this.listeners.forEach((fn) => fn(payload));
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000);
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    } else {
      // Fallback: start client-side telemetry simulation for standalone demo
      this.startSimulation();
    }
  }

  private startSimulation() {
    if (this.simulationInterval) return;
    this.simulationInterval = setInterval(() => {
      const payload: RealtimePayload = {
        type: "telemetry",
        data: {
          chainageM: 12000 + Math.random() * 200,
          speedKmh: 110 + (Math.random() * 4 - 2),
          vibrationRms: 0.8 + Math.random() * 0.4,
          trackGaugeMm: 1435 + (Math.random() * 2 - 1),
          cantMm: 12 + Math.random() * 2,
          twistMmPerM: 0.9 + Math.random() * 0.3,
        },
        timestamp: new Date().toISOString(),
      };
      this.notify(payload);
    }, 2000);
  }

  private stopSimulation() {
    if (this.simulationInterval) {
      clearInterval(this.simulationInterval);
      this.simulationInterval = null;
    }
  }
}

export const realtimeClient = new RealtimeClient();
