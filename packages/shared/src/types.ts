// Canonical DTO types: telemetry, defects, sessions, decisions.

export type SeverityLevel = "normal" | "low" | "medium" | "high" | "critical";

export type DefectClass =
  | "crack"
  | "spalling"
  | "corrugation"
  | "missing_fastener"
  | "gauge_widening"
  | "alignment_fault"
  | "twist_exceedance"
  | "squat"
  | "unclassified_anomaly";

export type DecisionType = "OK" | "KNOWN" | "NOVEL";

export interface LineGeometry {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  angle_deg: number;
  length: number;
}

export interface TelemetryPoint {
  id: string;
  sessionId: string;
  timestamp: string;
  chainageM: number;
  speedKmh: number;
  vibrationRms: number;
  trackGaugeMm: number;
  cantMm: number;
  twistMmPerM: number;
  verticalUnevennessMm: number;
  alignmentDevMm: number;
  latitude?: number;
  longitude?: number;
}

export interface DefectEvent {
  id: string;
  sessionId: string;
  timestamp: string;
  chainageM: number;
  defectClass: DefectClass;
  severity: SeverityLevel;
  confidence: number;
  streamSource: "vision" | "geometry" | "fused";
  imageUrl?: string;
  videoTimestampSec?: number;
  description?: string;
  status: "open" | "acknowledged" | "resolved";
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface MonitoringSession {
  id: string;
  name: string;
  trackId: string;
  trackSection: string;
  startTime: string;
  endTime?: string;
  status: "active" | "completed" | "paused" | "failed";
  totalDistanceKm: number;
  defectsCount: number;
  operatorName?: string;
}

export interface SegmentDecision {
  windowId: string;
  startChainageM: number;
  endChainageM: number;
  decision: DecisionType;
  visionScore: number;
  geometryScore: number;
  calibratedProb: number;
  primaryFault?: DefectClass;
  timestamp: string;
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
