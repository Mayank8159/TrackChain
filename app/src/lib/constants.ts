// Domain constants: defect classes, severity levels, colors, API routes.

import type { DefectClass, SeverityLevel } from "./types";

export const DEFECT_CLASSES: { value: DefectClass; label: string; stream: string }[] = [
  { value: "missing_fastener", label: "Missing Fastener / Clip", stream: "vision" },
  { value: "damaged_fastener", label: "Damaged Fastener / Clip", stream: "vision" },
  { value: "crack", label: "Rail Crack / Fracture", stream: "vision" },
  { value: "spalling", label: "Surface Spalling", stream: "vision" },
  { value: "corrugation", label: "Rail Corrugation", stream: "fused" },
  { value: "squat", label: "Rail Squat / RCF", stream: "vision" },
  { value: "gauge_widening", label: "Gauge Widening Dev.", stream: "geometry" },
  { value: "alignment_fault", label: "Alignment Versine Fault", stream: "geometry" },
  { value: "twist_exceedance", label: "Track Twist Exceedance", stream: "geometry" },
  { value: "rough_track", label: "Rough Track / Ride Quality", stream: "geometry" },
  { value: "obstruction", label: "Track Obstruction / Foreign Object", stream: "vision" },
  { value: "visual_anomaly", label: "Novel Visual Anomaly", stream: "vision" },
  { value: "geometry_anomaly", label: "Novel Geometry Anomaly", stream: "geometry" },
  { value: "unclassified_anomaly", label: "Unclassified Anomaly", stream: "fused" },
];

export const SEVERITY_CONFIG: Record<
  SeverityLevel,
  { label: string; color: string; bgColor: string; borderColor: string; badgeClass: string }
> = {
  critical: {
    label: "Critical",
    color: "#FF1744",
    bgColor: "rgba(255, 23, 68, 0.15)",
    borderColor: "rgba(255, 23, 68, 0.4)",
    badgeClass: "badge-red",
  },
  high: {
    label: "High",
    color: "#FFB300",
    bgColor: "rgba(255, 179, 0, 0.15)",
    borderColor: "rgba(255, 179, 0, 0.4)",
    badgeClass: "badge-amber",
  },
  medium: {
    label: "Medium",
    color: "#F59E0B",
    bgColor: "rgba(245, 158, 11, 0.12)",
    borderColor: "rgba(245, 158, 11, 0.3)",
    badgeClass: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  },
  low: {
    label: "Low",
    color: "#00F0FF",
    bgColor: "rgba(0, 240, 255, 0.12)",
    borderColor: "rgba(0, 240, 255, 0.3)",
    badgeClass: "badge-cyan",
  },
  normal: {
    label: "Nominal",
    color: "#00E676",
    bgColor: "rgba(0, 230, 118, 0.12)",
    borderColor: "rgba(0, 230, 118, 0.3)",
    badgeClass: "badge-green",
  },
};

export const EN_13848_LIMITS = {
  nominalGaugeMm: 1435.0,
  gaugeWarningMm: 1445.0,
  gaugeCriticalMm: 1455.0,
  twistWarningMmPerM: 3.0,
  twistCriticalMmPerM: 5.0,
  cantLimitMm: 160.0,
};

export const API_ROUTES = {
  HEALTH: "/health",
  READY: "/ready",
  SESSIONS: "/api/v1/sessions",
  TELEMETRY: "/api/v1/telemetry",
  DEFECTS: "/api/v1/defects",
  MEDIA: "/api/v1/media",
  ML_SIGNALS: "/api/v1/ml/signals",
  DASHBOARD: "/api/v1/dashboard",
  PROCESS_FRAME: "/process-frame",
};
