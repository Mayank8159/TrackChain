// Typed backend client: fetch telemetry, defects, sessions, devices, dashboard, and media (tc.v1).

import type {
  DefectEvent,
  MonitoringSession,
  TelemetryPoint,
  Device,
  DashboardSummary,
  MLSignal,
  LineGeometry,
  TelemetryBatchIngestRequest,
  PresignUploadRequest,
  PresignUploadResponse,
  PresignDownloadResponse,
} from "./types";

function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    // In browser, if NEXT_PUBLIC_API_BASE_URL is set, use it; otherwise use relative path so Next.js rewrites proxy cleanly
    return process.env.NEXT_PUBLIC_API_BASE_URL || "";
  }
  // In server-side / SSR context, default to direct local backend
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
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
  healthCheck: async (): Promise<boolean> => {
    try {
      const res = await request<{ status: string }>("/health");
      return res && (res.status === "ok" || res.status === "healthy" || !!res.status);
    } catch {
      try {
        const res = await request<{ status: string }>("/api/health");
        return res && (res.status === "ok" || res.status === "healthy" || !!res.status);
      } catch {
        return false;
      }
    }
  },

  // Devices
  getDevices: () => request<Device[]>("/api/devices"),
  registerDevice: (device: Partial<Device>) =>
    request<Device>("/api/devices", {
      method: "POST",
      body: JSON.stringify(device),
    }),

  // Telemetry
  getTelemetrySeries: (sessionId: string, downsample = 100) =>
    request<TelemetryPoint[]>(
      `/api/telemetry?session_id=${sessionId}&downsample=${downsample}`
    ),

  postTelemetryBatch: (payload: TelemetryBatchIngestRequest) =>
    request<{ status: string; inserted: number }>("/api/telemetry", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Defects
  getDefects: (filters?: {
    sessionId?: string;
    severity?: string;
    defectClass?: string;
    status?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.defectClass) params.append("defect_class", filters.defectClass);
    if (filters?.status) params.append("status", filters.status);
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

  // Dashboard KPI
  getDashboardSummary: () =>
    request<DashboardSummary>("/api/dashboard/summary"),

  // ML Signals
  getMLSignals: (sessionId: string, segmentId?: string) => {
    const params = new URLSearchParams({ session_id: sessionId });
    if (segmentId) params.append("segment_id", segmentId);
    return request<MLSignal[]>(`/api/ml/signals?${params.toString()}`);
  },

  // Media & S3
  getPresignedUploadUrl: (filename: string, contentType: string, sessionId = "default") =>
    request<PresignUploadResponse>("/api/media/presign-upload", {
      method: "POST",
      body: JSON.stringify({
        filename,
        contentType,
        session_id: sessionId,
        media_type: filename.endsWith(".mp4") ? "video_segment" : "evidence_image",
      }),
    }),

  getPresignedDownloadUrl: (s3Key: string) =>
    request<PresignDownloadResponse>("/api/media/presign-download", {
      method: "POST",
      body: JSON.stringify({ s3_key: s3Key }),
    }),

  // RDSO / Compliance Report Export
  exportSessionReport: async (sessionId: string, format: "csv" | "parquet" = "csv"): Promise<Blob> => {
    const baseUrl = getBaseUrl();
    const url = `${baseUrl}/api/dashboard/export/${sessionId}?format=${format}`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Export error [${response.status}]: ${errorText}`);
    }
    return response.blob();
  },
};

