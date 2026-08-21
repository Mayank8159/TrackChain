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

// ============================================================================
// 10. Pipeline Performance & Latency Tracing (tc.v1)
// ============================================================================

export interface PipelineTrace {
  trace_id: string;
  node_id: string;
  event_type: "TELEMETRY" | "DEFECT" | "MEDIA";
  captured_at: number;
  ingested_at: number;
  inference_ms: number;
  delivered_at?: number;
  e2e_ms?: number;
  transport_ms?: number;
  delivery_ms?: number;
}

export interface NodePerformanceSummary {
  node_id: string;
  hardware_type?: string;
  total_events: number;
  avg_transport_ms: number;
  avg_inference_ms: number;
  avg_e2e_ms: number;
  p95_e2e_ms: number;
  status: "optimal" | "warning" | "critical";
}

export interface PerformanceMetrics {
  window_seconds: number;
  total_events: number;
  throughput_eps: number;
  avg_transport_ms: number;
  avg_inference_ms: number;
  avg_delivery_ms: number;
  avg_e2e_ms: number;
  p95_e2e_ms: number;
  composite_score: number;
  composite_grade: "A" | "B" | "C" | "D" | "F";
  node_summaries: NodePerformanceSummary[];
}

// ============================================================================
// 11. Computer Vision & Model Test Bench Contracts (tc.v1)
// ============================================================================

export interface HoughLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  theta_deg: number;
  rho?: number;
  length?: number;
}

export interface BoundingBox {
  class: string;
  confidence: number;
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

export interface InferenceResult {
  trace_id: string;
  inference_ms: number;
  image_width: number;
  image_height: number;
  rails: HoughLine[];
  sleepers: HoughLine[];
  yolo_boxes: BoundingBox[];
  yolo_weights_loaded: boolean;
  status?: string;
}

export interface ImageProvenance {
  id: string;
  url: string;
  title: string;
  source: string;
  license: string;
  type: "PHOTO" | "AI_GENERATED" | "SYNTHETIC";
  description: string;
  resolution: string;
}

// ============================================================================
// 12. Oracle: Predictive Maintenance & Degradation Forecasting (tc.oracle.v1)
// ============================================================================

/** A single point on the 180-day degradation timeline (90 historical + 90 forecast). */
export interface ForecastPoint {
  timestamp: number;        // Epoch ms
  day: number;              // -90 … +90 (0 = today)
  tqi_actual?: number;      // Historical actuals (days ≤ 0)
  tqi_predicted?: number;   // Probabilistic forecast (days > 0)
  lower_bound_95?: number;  // 95% conformal prediction interval — lower
  upper_bound_95?: number;  // 95% conformal prediction interval — upper
  lower_bound_80?: number;  // 80% conformal prediction interval — lower
  upper_bound_80?: number;  // 80% conformal prediction interval — upper
}

/** Probability of a track segment surviving N days without breaching the critical limit. */
export interface SurvivalProbability {
  horizon_days: 30 | 60 | 90;
  probability: number;  // 0.0 – 1.0
}

/** A named track segment with its forecasting context (Oracle engine). */
export interface OracleSegment {
  id: string;
  label: string;       // e.g. "KM 42–45"
  trackClass: "CLASS_A" | "CLASS_B" | "CLASS_C";
  currentTqi: number;
  breachDayEstimate: number | null; // null = no breach within 90 days
  survivalProbs: SurvivalProbability[];
  forecast: ForecastPoint[];
}

/** Auto-generated RDSO Work Order triggered by the Oracle engine. */
export interface WorkOrder {
  id: string;
  segmentId: string;
  segmentLabel: string;
  recommendedAction: string;
  recommendedDate: string;       // ISO date string
  urgencyDays: number;           // Days until predicted breach
  estimatedCrewSize: number;
  estimatedDurationHours: number;
  estimatedTqiRecovery: number;  // +N TQI points post-intervention
  generatedAt: string;           // ISO timestamp
}

