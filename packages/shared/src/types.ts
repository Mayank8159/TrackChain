// Canonical DTO types: telemetry, defects, sessions, decisions, devices, media, and SOTA contracts (tc.v1).

export const SCHEMA_VERSION = "tc.v1" as const;
export type SchemaVersion = typeof SCHEMA_VERSION;

// ============================================================================
// 1. Enums & Classification Types
// ============================================================================

export type SeverityLevel = "normal" | "low" | "medium" | "high" | "critical";

export type DecisionType = "OK" | "INSPECT_KNOWN" | "INSPECT_NOVEL" | "KNOWN" | "NOVEL";

export type DefectFamily =
  | "visual_component"
  | "visual_surface"
  | "geometry"
  | "novel_anomaly"
  | "obstruction";

export type DefectClass =
  | "missing_fastener"
  | "damaged_fastener"
  | "crack"
  | "corrugation"
  | "spalling"
  | "squat"
  | "gauge_widening"
  | "alignment_fault"
  | "twist_exceedance"
  | "rough_track"
  | "obstruction"
  | "visual_anomaly"
  | "geometry_anomaly"
  | "unclassified_anomaly";

export type MediaType =
  | "video_segment"
  | "evidence_image"
  | "thumbnail"
  | "imu_burst"
  | "report_file";

export type UploadStatus =
  | "pending"
  | "uploading"
  | "uploaded"
  | "failed"
  | "expired";

export type SessionStatus =
  | "active"
  | "created"
  | "running"
  | "completed"
  | "failed"
  | "uploaded"
  | "processing"
  | "paused";

export type DefectStatus =
  | "open"
  | "acknowledged"
  | "assigned"
  | "resolved"
  | "false_positive";

export type SignalType =
  | "visual_known"
  | "visual_novel"
  | "geometry_known"
  | "geometry_novel"
  | "geometry_fault_type";

export type CalibrationMethod =
  | "temperature_scaling"
  | "platt_scaling"
  | "isotonic"
  | "fpr_threshold"
  | "manual_threshold"
  | "standard_limit";

// ============================================================================
// 2. Core Domain Entities
// ============================================================================

export interface Device {
  deviceId: string;
  deviceName: string;
  hardwareVersion: string;
  firmwareVersion: string;
  cameraModel?: string;
  imuModel?: string;
  gnssModel?: string;
  status: "online" | "offline" | "recording" | "error";
  batteryVoltageV?: number;
  cpuTempC?: number;
  lastSeenAt?: string;
}

export interface MonitoringSession {
  id: string;
  deviceId?: string;
  name: string;
  routeName?: string;
  lineName?: string;
  trackId: string;
  trackSection: string;
  trackDirection?: "up" | "down" | "both";
  startTime: string;
  endTime?: string;
  startChainageM?: number;
  endChainageM?: number;
  status: SessionStatus;
  totalDistanceKm: number;
  defectsCount: number;
  operatorName?: string;
  weather?: string;
}

export interface TrackSegment {
  segmentId: string;
  sessionId: string;
  chainageStartM: number;
  chainageEndM: number;
  timestampStart: string;
  timestampEnd: string;
  latStart?: number;
  lonStart?: number;
  latEnd?: number;
  lonEnd?: number;
  speedAvgMps?: number;
}

export interface TelemetryPoint {
  id: string;
  sessionId: string;
  deviceId?: string;
  segmentId?: string;
  timestamp: string;
  chainageM: number;

  // Spatial & Kinematics
  latitude?: number;
  longitude?: number;
  altitudeM?: number;
  gnssFixQuality?: number;
  gnssSatellites?: number;
  speedMps?: number;
  speedKmh?: number;

  // Raw IMU
  imuAx?: number;
  imuAy?: number;
  imuAz?: number;
  imuGx?: number;
  imuGy?: number;
  imuGz?: number;
  rollDeg?: number;
  pitchDeg?: number;
  yawDeg?: number;

  // Aggregated Dynamics & EN 13848 Track Geometry
  verticalRms?: number;
  lateralRms?: number;
  longitudinalRms?: number;
  vibrationRms: number;
  vibrationIndex?: number;
  trackGaugeMm: number;
  cantMm: number;
  twistMmPerM: number;
  verticalUnevennessMm?: number;
  alignmentDevMm?: number;

  // Diagnostics
  temperatureC?: number;
  batteryVoltageV?: number;
}

export interface MediaAsset {
  mediaId: string;
  sessionId: string;
  deviceId?: string;
  segmentId?: string;
  mediaType: MediaType;
  s3Bucket: string;
  s3Key: string;
  contentType: string;
  sizeBytes: number;
  durationSeconds?: number;
  timestampStart?: string;
  timestampEnd?: string;
  chainageStartM?: number;
  chainageEndM?: number;
  uploadStatus: UploadStatus;
  checksum?: string;
  createdAt: string;
}

export interface MLSignal {
  signalId: string;
  sessionId: string;
  segmentId: string;
  defectId?: string;
  modelName: string;
  modelVersion: string;
  signalType: SignalType;
  rawScore: number;
  calibratedScore: number;
  threshold: number;
  fired: boolean;
  label?: DefectClass;
  bbox?: [number, number, number, number]; // [x1, y1, x2, y2]
  explanation?: string;
  timestamp: string;
}

export interface DefectEvent {
  id: string;
  sessionId: string;
  deviceId?: string;
  segmentId?: string;

  defectClass: DefectClass;
  defectFamily?: DefectFamily;
  severity: SeverityLevel;
  decision?: DecisionType;

  chainageM: number;
  chainageStartM?: number;
  chainageEndM?: number;
  timestamp: string;

  coordinates?: {
    lat: number;
    lng: number;
  };
  latitude?: number;
  longitude?: number;

  confidence: number;
  sourceModel?: string;
  modelVersion?: string;
  streamSource: "vision" | "geometry" | "fused";

  imageUrl?: string;
  evidenceImageId?: string;
  videoMediaId?: string;
  videoTimestampSec?: number;
  videoOffsetSeconds?: number;

  description?: string;
  status: DefectStatus;
  supportingSignals?: MLSignal[];
  createdAt?: string;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
  resolvedAt?: string;
  notes?: string;
}

export interface SegmentDecision {
  windowId: string;
  segmentId?: string;
  startChainageM: number;
  endChainageM: number;
  decision: DecisionType;
  confidence: number;
  visionScore?: number;
  geometryScore?: number;
  calibratedProb?: number;
  primaryFault?: DefectClass;
  defectFamily?: DefectFamily;
  severity?: SeverityLevel;
  allModelSignals?: MLSignal[];
  evidenceReference?: string;
  timestamp: string;
}

export interface CalibrationArtifact {
  calibrationId: string;
  modelName: string;
  modelVersion: string;
  method: CalibrationMethod;
  targetFpr: number;
  threshold: number;
  temperature?: number;
  validationDataset: string;
  createdAt: string;
  metricsSummary: Record<string, number>;
}

export interface ModelRegistryRecord {
  modelName: string;
  modelVersion: string;
  modelType: string;
  artifactUri: string;
  inputContractVersion: string;
  outputContractVersion: string;
  trainedOn?: string;
  metrics?: Record<string, number>;
  createdAt: string;
  isActive: boolean;
}

export interface DashboardSummary {
  totalDefects: number;
  criticalDefects: number;
  distanceCoveredKm: number;
  avgSpeedKmh: number;
  openAlerts: number;
  defectCountsByClass: Record<string, number>;
  severityDistribution: Record<SeverityLevel, number>;
}

// ============================================================================
// 3. Request & Ingestion Envelopes
// ============================================================================

export interface IdempotentPayload {
  schemaVersion: SchemaVersion;
  idempotencyKey: string;
  timestamp: string;
}

export interface TelemetryBatchIngestRequest extends IdempotentPayload {
  sessionId: string;
  deviceId: string;
  samples: Omit<TelemetryPoint, "id" | "sessionId">[];
}

export interface MLSignalBatchRequest extends IdempotentPayload {
  sessionId: string;
  segmentId: string;
  signals: Omit<MLSignal, "signalId" | "sessionId">[];
  decision?: SegmentDecision;
}

export interface PresignUploadRequest {
  sessionId: string;
  deviceId?: string;
  mediaType: MediaType;
  filename: string;
  contentType: string;
  sizeBytes?: number;
  chainageStartM?: number;
  chainageEndM?: number;
}

export interface PresignUploadResponse {
  mediaId: string;
  uploadUrl: string;
  s3Bucket: string;
  s3Key: string;
  fileUrl?: string;
  expiresInSeconds: number;
}

export interface PresignDownloadResponse {
  mediaId: string;
  downloadUrl: string;
  expiresInSeconds: number;
}

export interface LineGeometry {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  angle_deg: number;
  length: number;
}

export interface ProcessFramePayload {
  cameraId: string;
  frame: string;
}

export interface ProcessFrameResult {
  cameraId: string;
  resolution: [number, number];
  lineCount: number;
  lines: LineGeometry[];
  processingMs: number;
  status: string;
}
