// Secure Hardened API Client with Token Injection, 401 Refresh, and 429 Rate Limit Backoff (tc.v1).

import { env } from "./env";
import type {
  DefectEvent,
  MonitoringSession,
  TelemetryPoint,
  Device,
  DashboardSummary,
  MLSignal,
  TelemetryBatchIngestRequest,
  PresignUploadResponse,
  PresignDownloadResponse,
} from "./types";

export interface NodeRegistrationPayload {
  device_id: string;
  name?: string;
  device_name?: string;
  hardware_version?: string;
  firmware_version?: string;
  camera_model?: string;
  imu_model?: string;
  gnss_model?: string;
}

export interface NodeRegistrationResult {
  device_id: string;
  api_key: string;
  message: string;
  status: string;
}

class SecureApiClient {
  private baseURL: string;
  private isRefreshing = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  constructor() {
    this.baseURL = env.apiUrl;
  }

  private getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("trackchain_access_token");
  }

  private getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("trackchain_refresh_token");
  }

  private setTokens(accessToken: string, refreshToken?: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem("trackchain_access_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("trackchain_refresh_token", refreshToken);
    }
  }

  private onTokenRefreshed(token: string) {
    this.refreshSubscribers.forEach((callback) => callback(token));
    this.refreshSubscribers = [];
  }

  private addRefreshSubscriber(callback: (token: string) => void) {
    this.refreshSubscribers.push(callback);
  }

  private async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await fetch(`${this.baseURL}/api/devices/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("trackchain_access_token");
        localStorage.removeItem("trackchain_refresh_token");
      }
      throw new Error("Failed to refresh access token");
    }

    const data = await response.json();
    const newAccessToken = data.access_token;
    this.setTokens(newAccessToken, data.refresh_token);
    return newAccessToken;
  }

  public async request<T>(
    path: string,
    options: RequestInit = {},
    retryCount = 0
  ): Promise<T> {
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const url = `${this.baseURL}${cleanPath}`;
    const token = this.getAccessToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      // Handle Rate Limiting (429 Too Many Requests)
      if (response.status === 429 && retryCount < 3) {
        const retryAfterSec = parseInt(response.headers.get("Retry-After") || "2", 10);
        const delayMs = Math.min(Math.max(retryAfterSec, 1) * 1000, 10000);
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        return this.request<T>(path, options, retryCount + 1);
      }

      // Handle Token Expiry (401 Unauthorized)
      if (response.status === 401 && retryCount === 0 && this.getRefreshToken()) {
        if (!this.isRefreshing) {
          this.isRefreshing = true;
          try {
            const newToken = await this.refreshAccessToken();
            this.isRefreshing = false;
            this.onTokenRefreshed(newToken);
            return this.request<T>(path, options, retryCount + 1);
          } catch (err) {
            this.isRefreshing = false;
            throw err;
          }
        } else {
          return new Promise<T>((resolve, reject) => {
            this.addRefreshSubscriber(async () => {
              try {
                const res = await this.request<T>(path, options, retryCount + 1);
                resolve(res);
              } catch (e) {
                reject(e);
              }
            });
          });
        }
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error [${response.status}]: ${errorText || response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error(`API request timed out after 30s: ${path}`);
      }
      throw error;
    }
  }

  // --- Health Probes ---
  public async getHealth() {
    return this.request<{ status: string; service: string }>("/health");
  }

  public async healthCheck(): Promise<boolean> {
    try {
      const res = await this.request<{ status: string }>("/health");
      return !!res && (res.status === "ok" || res.status === "healthy" || !!res.status);
    } catch {
      try {
        const res = await this.request<{ status: string }>("/api/health");
        return !!res && (res.status === "ok" || res.status === "healthy" || !!res.status);
      } catch {
        return false;
      }
    }
  }

  // --- Devices & Fleet Ingestion ---
  public async getDevices() {
    return this.request<Device[]>("/api/devices");
  }

  public async registerDevice(device: Partial<Device>) {
    return this.request<Device>("/api/devices", {
      method: "POST",
      body: JSON.stringify(device),
    });
  }

  public async registerEdgeNode(payload: NodeRegistrationPayload): Promise<NodeRegistrationResult> {
    return this.request<NodeRegistrationResult>("/api/devices/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // --- Telemetry Series ---
  public async getTelemetrySeries(sessionId: string, downsample = 100) {
    return this.request<TelemetryPoint[]>(
      `/api/telemetry?session_id=${sessionId}&downsample=${downsample}`
    );
  }

  public async postTelemetryBatch(payload: TelemetryBatchIngestRequest) {
    return this.request<{ status: string; inserted: number }>("/api/telemetry", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // --- Defect Registry ---
  public async getDefects(filters?: {
    sessionId?: string;
    severity?: string;
    defectClass?: string;
    status?: string;
  }) {
    const params = new URLSearchParams();
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.defectClass) params.append("defect_class", filters.defectClass);
    if (filters?.status) params.append("status", filters.status);
    return this.request<DefectEvent[]>(`/api/defects?${params.toString()}`);
  }

  public async postDefect(defect: Partial<DefectEvent>) {
    return this.request<DefectEvent>("/api/defects", {
      method: "POST",
      body: JSON.stringify(defect),
    });
  }

  // --- Inspection Sessions ---
  public async getSessions() {
    return this.request<MonitoringSession[]>("/api/sessions");
  }

  public async getSessionById(id: string) {
    return this.request<MonitoringSession>(`/api/sessions/${id}`);
  }

  public async createSession(data: Partial<MonitoringSession>) {
    return this.request<MonitoringSession>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- Dashboard Analytics ---
  public async getDashboardSummary() {
    return this.request<DashboardSummary>("/api/dashboard/summary");
  }

  // --- ML Signal Analytics ---
  public async getMLSignals(sessionId: string, segmentId?: string) {
    const params = new URLSearchParams({ session_id: sessionId });
    if (segmentId) params.append("segment_id", segmentId);
    return this.request<MLSignal[]>(`/api/ml/signals?${params.toString()}`);
  }

  // --- Media & S3 Storage ---
  public async getPresignedUploadUrl(filename: string, contentType: string, sessionId = "default") {
    return this.request<PresignUploadResponse>("/api/media/presign-upload", {
      method: "POST",
      body: JSON.stringify({
        filename,
        contentType,
        session_id: sessionId,
        media_type: filename.endsWith(".mp4") ? "video_segment" : "evidence_image",
      }),
    });
  }

  public async getPresignedDownloadUrl(s3Key: string) {
    return this.request<PresignDownloadResponse>("/api/media/presign-download", {
      method: "POST",
      body: JSON.stringify({ s3_key: s3Key }),
    });
  }

  // --- RDSO / Compliance Report Export ---
  public async exportSessionReport(
    sessionId: string,
    format: "csv" | "parquet" = "csv"
  ): Promise<Blob> {
    const url = `${this.baseURL}/api/dashboard/export/${sessionId}?format=${format}`;
    const token = this.getAccessToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Export error [${response.status}]: ${errorText}`);
    }
    return response.blob();
  }
}

export const api = new SecureApiClient();
