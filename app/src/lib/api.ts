// Typed backend client: fetch telemetry, defects, sessions, and presigned media URLs.

import type {
  DefectEvent,
  MonitoringSession,
  TelemetryPoint,
  LineGeometry,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorBody}`);
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: () => request<{ status: string; service: string }>("/health"),

  // Telemetry
  getTelemetrySeries: (sessionId: string, downsample = 100) =>
    request<TelemetryPoint[]>(
      `/api/telemetry?session_id=${sessionId}&downsample=${downsample}`
    ),

  postTelemetryBatch: (points: Partial<TelemetryPoint>[]) =>
    request<{ inserted: number }>("/api/telemetry", {
      method: "POST",
      body: JSON.stringify(points),
    }),

  // Defects
  getDefects: (filters?: {
    sessionId?: string;
    severity?: string;
    defectClass?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.defectClass) params.append("defect_class", filters.defectClass);
    return request<DefectEvent[]>(`/api/defects?${params.toString()}`);
  },

  postDefect: (defect: Partial<DefectEvent>) =>
    request<DefectEvent>("/api/defects", {
      method: "POST",
      body: JSON.stringify(defect),
    }),

  // Sessions
  getSessions: () => request<MonitoringSession[]>("/api/sessions"),

  getSessionById: (id: string) =>
    request<MonitoringSession>(`/api/sessions/${id}`),

  createSession: (data: Partial<MonitoringSession>) =>
    request<MonitoringSession>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Media
  getPresignedUploadUrl: (filename: string, contentType: string) =>
    request<{ uploadUrl: string; fileUrl: string }>("/api/media/presign-upload", {
      method: "POST",
      body: JSON.stringify({ filename, contentType }),
    }),

  // Frame Processing (CV line detection)
  processFrame: (cameraId: string, base64Frame: string) =>
    request<{
      camera_id: string;
      resolution: [number, number];
      line_count: number;
      lines: LineGeometry[];
      processing_ms: number;
      status: string;
    }>("/process-frame", {
      method: "POST",
      body: JSON.stringify({ camera_id: cameraId, frame: base64Frame }),
    }),
};
