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

  // --- Normalizers (snake_case -> camelCase) ---
  public normalizeDefect(d: any): DefectEvent {
    if (!d) return d;
    return {
      id: d.id || `def-${Date.now()}`,
      sessionId: d.session_id || d.sessionId || "ses-default",
      deviceId: d.device_id || d.deviceId,
      segmentId: d.segment_id || d.segmentId,
      defectClass: (d.defect_class || d.defectClass || "unclassified_anomaly") as any,
      defectFamily: (d.defect_family || d.defectFamily) as any,
      severity: (d.severity || "medium").toLowerCase() as any,
      decision: (d.decision || "INSPECT_KNOWN") as any,
      chainageM: Number(d.chainage_m ?? d.chainageM ?? 0),
      chainageStartM: d.chainage_start_m ?? d.chainageStartM,
      chainageEndM: d.chainage_end_m ?? d.chainageEndM,
      timestamp: d.timestamp || d.created_at || d.createdAt || new Date().toISOString(),
      coordinates: d.coordinates || (d.latitude && d.longitude ? { lat: d.latitude, lng: d.longitude } : undefined),
      latitude: d.latitude,
      longitude: d.longitude,
      confidence: Number(d.confidence ?? 0.95),
      sourceModel: d.source_model || d.sourceModel || "ML Fusion",
      modelVersion: d.model_version || d.modelVersion || "v1.0.0",
      streamSource: (d.stream_source || d.streamSource || "fused") as any,
      imageUrl: d.image_url || d.imageUrl || "/evidence/track_flaw_sample.jpg",
      evidenceImageId: d.evidence_image_id || d.evidenceImageId,
      videoMediaId: d.video_media_id || d.videoMediaId,
      videoTimestampSec: Number(d.video_timestamp_sec ?? d.videoTimestampSec ?? 0),
      videoOffsetSeconds: d.video_offset_seconds ?? d.videoOffsetSeconds,
      description: d.description || d.notes || "",
      status: (d.status || "open").toLowerCase() as any,
      createdAt: d.created_at || d.createdAt || new Date().toISOString(),
      acknowledgedAt: d.acknowledged_at || d.acknowledgedAt,
      supportingSignals: d.supporting_signals || d.supportingSignals || [],
    };
  }

  public normalizeSession(s: any): MonitoringSession {
    if (!s) return s;
    return {
      id: s.id,
      deviceId: s.device_id || s.deviceId,
      name: s.name || s.id,
      routeName: s.route_name || s.routeName,
      lineName: s.line_name || s.lineName,
      trackId: s.track_id || s.trackId || "TRACK-01",
      trackSection: s.track_section || s.trackSection || "Mainline Corridor",
      trackDirection: s.track_direction || s.trackDirection || "both",
      startTime: s.start_time || s.startTime || new Date().toISOString(),
      endTime: s.end_time || s.endTime,
      startChainageM: Number(s.start_chainage_m ?? s.startChainageM ?? 0),
      endChainageM: Number(s.end_chainage_m ?? s.endChainageM ?? 0),
      status: (s.status || "completed").toLowerCase() as any,
      totalDistanceKm: Number(s.total_distance_km ?? s.totalDistanceKm ?? 0),
      defectsCount: Number(s.defects_count ?? s.defectsCount ?? 0),
      operatorName: s.operator_name || s.operatorName,
      weather: s.weather,
    };
  }

  public normalizeTelemetry(t: any): TelemetryPoint {
    if (!t) return t;
    return {
      id: t.id || `tel-${Date.now()}`,
      sessionId: t.session_id || t.sessionId,
      deviceId: t.device_id || t.deviceId,
      segmentId: t.segment_id || t.segmentId,
      timestamp: t.timestamp || new Date().toISOString(),
      chainageM: Number(t.chainage_m ?? t.chainageM ?? 0),
      latitude: t.latitude,
      longitude: t.longitude,
      speedMps: t.speed_mps ?? t.speedMps,
      speedKmh: t.speed_kmh ?? t.speedKmh,
      verticalRms: t.vertical_rms ?? t.verticalRms,
      lateralRms: t.lateral_rms ?? t.lateralRms,
      longitudinalRms: t.longitudinal_rms ?? t.longitudinalRms,
      vibrationRms: Number(t.vibration_rms ?? t.vibrationRms ?? 0),
      vibrationIndex: t.vibration_index ?? t.vibrationIndex,
      trackGaugeMm: Number(t.track_gauge_mm ?? t.trackGaugeMm ?? 1676.0),
      cantMm: Number(t.cant_mm ?? t.cantMm ?? 0),
      twistMmPerM: Number(t.twist_mm_per_m ?? t.twistMmPerM ?? 0),
      verticalUnevennessMm: t.vertical_unevenness_mm ?? t.verticalUnevennessMm,
      alignmentDevMm: t.alignment_dev_mm ?? t.alignmentDevMm,
      temperatureC: t.temperature_c ?? t.temperatureC,
      batteryVoltageV: t.battery_voltage_v ?? t.batteryVoltageV,
    };
  }

  public normalizeDevice(dev: any): Device {
    if (!dev) return dev;
    return {
      deviceId: dev.device_id || dev.deviceId,
      deviceName: dev.device_name || dev.deviceName || dev.device_id,
      hardwareVersion: dev.hardware_version || dev.hardwareVersion || "Raspberry Pi 5",
      firmwareVersion: dev.firmware_version || dev.firmwareVersion || "v1.0.0",
      cameraModel: dev.camera_model || dev.cameraModel,
      imuModel: dev.imu_model || dev.imuModel,
      gnssModel: dev.gnss_model || dev.gnssModel,
      status: (dev.status || "online").toLowerCase() as any,
      batteryVoltageV: dev.battery_voltage_v ?? dev.batteryVoltageV,
      cpuTempC: dev.cpu_temp_c ?? dev.cpuTempC,
      lastSeenAt: dev.last_seen_at || dev.lastSeenAt,
      latitude: dev.latitude,
      longitude: dev.longitude,
      isDiscovered: dev.is_discovered ?? dev.isDiscovered,
      discoveredAt: dev.discovered_at || dev.discoveredAt,
    };
  }

  public normalizeDashboardSummary(sum: any): DashboardSummary {
    if (!sum) return sum;
    return {
      totalDefects: Number(sum.total_defects ?? sum.totalDefects ?? 0),
      criticalDefects: Number(sum.critical_defects ?? sum.criticalDefects ?? 0),
      distanceCoveredKm: Number(sum.distance_covered_km ?? sum.distanceCoveredKm ?? 0),
      avgSpeedKmh: Number(sum.avg_speed_kmh ?? sum.avgSpeedKmh ?? 0),
      openAlerts: Number(sum.open_alerts ?? sum.openAlerts ?? 0),
      defectCountsByClass: sum.defect_counts_by_class || sum.defectCountsByClass || {},
      severityDistribution: sum.severity_distribution || sum.severityDistribution || {},
    };
  }

  // --- Devices & Fleet Ingestion ---
  public async getDevices(): Promise<Device[]> {
    const raw = await this.request<any[]>("/api/devices");
    return (raw || []).map((d) => this.normalizeDevice(d));
  }

  public async registerDevice(device: Partial<Device>): Promise<Device> {
    const raw = await this.request<any>("/api/devices", {
      method: "POST",
      body: JSON.stringify(device),
    });
    return this.normalizeDevice(raw);
  }

  public async registerEdgeNode(payload: NodeRegistrationPayload): Promise<NodeRegistrationResult> {
    return this.request<NodeRegistrationResult>("/api/devices/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // --- Telemetry Series ---
  public async getTelemetrySeries(sessionId: string, downsample = 100): Promise<TelemetryPoint[]> {
    const raw = await this.request<any>(
      `/api/telemetry?session_id=${sessionId}&downsample=${downsample}`
    );
    const list = Array.isArray(raw) ? raw : (raw?.points || []);
    return list.map((t: any) => this.normalizeTelemetry(t));
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
  }): Promise<DefectEvent[]> {
    const params = new URLSearchParams();
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.severity) params.append("severity", filters.severity);
    if (filters?.defectClass) params.append("defect_class", filters.defectClass);
    if (filters?.status) params.append("status", filters.status);
    const raw = await this.request<any[]>(`/api/defects?${params.toString()}`);
    return (raw || []).map((d) => this.normalizeDefect(d));
  }

  public async postDefect(defect: Partial<DefectEvent>): Promise<DefectEvent> {
    const raw = await this.request<any>("/api/defects", {
      method: "POST",
      body: JSON.stringify(defect),
    });
    return this.normalizeDefect(raw);
  }

  // --- Inspection Sessions ---
  public async getSessions(): Promise<MonitoringSession[]> {
    const raw = await this.request<any[]>("/api/sessions");
    return (raw || []).map((s) => this.normalizeSession(s));
  }

  public async getSessionById(id: string): Promise<MonitoringSession> {
    const raw = await this.request<any>(`/api/sessions/${id}`);
    return this.normalizeSession(raw);
  }

  public async createSession(data: Partial<MonitoringSession>): Promise<MonitoringSession> {
    const raw = await this.request<any>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return this.normalizeSession(raw);
  }

  // --- Dashboard Analytics ---
  public async getDashboardSummary(): Promise<DashboardSummary> {
    const raw = await this.request<any>("/api/dashboard/summary");
    return this.normalizeDashboardSummary(raw);
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
