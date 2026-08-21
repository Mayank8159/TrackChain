// Centralized 5-Tier Severity System for Railway Defect Intelligence & Operational SCADA (tc.v1).
// Rule: Severity must NEVER rely on color alone. Always pair color + icon + text.

import React from "react";
import { CheckCircle2, Info, AlertTriangle, AlertOctagon, Flame } from "lucide-react";
import type { SeverityLevel } from "./types";

export type CanonicalSeverity = "ok" | "low" | "medium" | "high" | "critical";

export interface SeverityMeta {
  level: CanonicalSeverity;
  label: string;
  hex: string;
  textClass: string;
  bgClass: string;
  borderClass: string;
  badgeClass: string;
  pulse: boolean;
  Icon: React.ComponentType<{ className?: string; size?: number | string }>;
  rdsoActionTime: string;
}

export const SEVERITY_CONFIG: Record<CanonicalSeverity, SeverityMeta> = {
  ok: {
    level: "ok",
    label: "OK",
    hex: "#10B981",
    textClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    borderClass: "border-emerald-500/30",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    pulse: false,
    Icon: CheckCircle2,
    rdsoActionTime: "Routine Maintenance",
  },
  low: {
    level: "low",
    label: "LOW",
    hex: "#84CC16",
    textClass: "text-lime-400",
    bgClass: "bg-lime-500/10",
    borderClass: "border-lime-500/30",
    badgeClass: "bg-lime-500/10 text-lime-400 border-lime-500/30",
    pulse: false,
    Icon: Info,
    rdsoActionTime: "Inspect within 14 Days",
  },
  medium: {
    level: "medium",
    label: "MEDIUM",
    hex: "#F59E0B",
    textClass: "text-amber-400",
    bgClass: "bg-amber-500/10",
    borderClass: "border-amber-500/30",
    badgeClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    pulse: false,
    Icon: AlertTriangle,
    rdsoActionTime: "Remediate within 72 Hours",
  },
  high: {
    level: "high",
    label: "HIGH",
    hex: "#F97316",
    textClass: "text-orange-400",
    bgClass: "bg-orange-500/10",
    borderClass: "border-orange-500/30",
    badgeClass: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    pulse: false,
    Icon: AlertOctagon,
    rdsoActionTime: "Speed Restriction (Caution Order) within 24h",
  },
  critical: {
    level: "critical",
    label: "CRITICAL",
    hex: "#EF4444",
    textClass: "text-red-400",
    bgClass: "bg-red-500/15",
    borderClass: "border-red-500/40",
    badgeClass: "bg-red-500/15 text-red-400 border-red-500/40",
    pulse: true,
    Icon: Flame,
    rdsoActionTime: "Immediate Action Limit (IAL) — Emergency Track Block",
  },
};

export function normalizeSeverity(val?: string | SeverityLevel | null): CanonicalSeverity {
  if (!val) return "ok";
  const s = val.toLowerCase().trim();
  if (s === "critical" || s === "crit" || s === "emergency") return "critical";
  if (s === "high" || s === "danger") return "high";
  if (s === "medium" || s === "med" || s === "warning" || s === "warn") return "medium";
  if (s === "low" || s === "minor" || s === "info") return "low";
  if (s === "ok" || s === "normal" || s === "nominal" || s === "success") return "ok";
  return "ok";
}

export function getSeverityMeta(val?: string | SeverityLevel | null): SeverityMeta {
  const norm = normalizeSeverity(val);
  return SEVERITY_CONFIG[norm];
}
