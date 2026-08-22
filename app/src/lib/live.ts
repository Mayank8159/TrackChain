// TrackChain Live Streaming & Alerting Integration

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Connects to the live WebSocket gateway for raw base64 frames and telemetry
 */
export function connectLive(
  session: string,
  onFrame: (dataUrl: string, chainage: number) => void,
  onTelemetry: (data: any) => void
) {
  const wsUrl = `${API.replace("http", "ws")}/ws/live?session=${session}`;
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
  return new EventSource(`${API}/api/v1/alerts/stream`);
};
