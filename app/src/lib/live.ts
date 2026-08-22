// TrackChain Live Streaming & Alerting Integration
import { env } from "./env";

export const API = env.apiUrl;

/**
 * Connects to the live WebSocket gateway for raw base64 frames and telemetry
 */
export function connectLive(
  session: string,
  onFrame: (dataUrl: string, chainage: number) => void,
  onTelemetry: (data: any) => void
) {
  const wsUrl = `${env.wsUrl}?session=${session}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data);
      if (m.type === "frame") {
        onFrame(`data:image/jpeg;base64,${m.b64}`, m.chainage);
      }
      if (m.type === "telemetry") {
        onTelemetry(m);
      }
    } catch (err) {
      console.error("Live streaming message parse error:", err);
    }
  };

  return ws;
}

/**
 * Connects to the live Server-Sent Events (SSE) broker for DefectEvents
 */
export const connectAlerts = () => {
  return new EventSource(env.sseUrl);
};
