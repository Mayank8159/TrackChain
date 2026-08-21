// Scripted Deterministic SSE Alert Simulator for TrackChain DEMO Mode (tc.v1).
// Eradicates Math.random() in favor of a mathematically predictable timeline of railway anomalies.

import type { AlertEvent } from "./types";

export interface ScriptedAlertDef {
  delayMs: number;
  alert: Omit<AlertEvent, "timestamp" | "acknowledged">;
}

export const DEMO_ALERT_SEQUENCE: ScriptedAlertDef[] = [
  {
    delayMs: 6000,
    alert: {
      id: "ALT-SIM-001",
      defectId: "DEF-001",
      severity: "critical",
      defectClass: "crack",
      chainageM: 3420,
      message: "CRITICAL: Transverse Rail Head Crack identified on Right Rail at Km 3+420 (NDLS-AGC Mainline)",
    },
  },
  {
    delayMs: 14000,
    alert: {
      id: "ALT-SIM-002",
      defectId: "DEF-002",
      severity: "high",
      defectClass: "gauge_widening",
      chainageM: 7850,
      message: "WARNING: Track Gauge Exceedance (1448mm / +13mm above nominal) detected at Km 7+850",
    },
  },
  {
    delayMs: 24000,
    alert: {
      id: "ALT-SIM-003",
      defectId: "DEF-003",
      severity: "medium",
      defectClass: "missing_fastener",
      chainageM: 12100,
      message: "NOTICE: Missing Pandrol Clip Fastener confirmed on sleeper #482 at Km 12+100",
    },
  },
  {
    delayMs: 38000,
    alert: {
      id: "ALT-SIM-004",
      defectId: "DEF-004",
      severity: "high",
      defectClass: "squat",
      chainageM: 16750,
      message: "HIGH: Rail Squat Fatigue Flaw & Running Surface Spalling at Km 16+750",
    },
  },
  {
    delayMs: 52000,
    alert: {
      id: "ALT-SIM-005",
      defectId: "DEF-005",
      severity: "critical",
      defectClass: "twist_exceedance",
      chainageM: 21950,
      message: "CRITICAL IAL ALARM: EN 13848 Track Twist Exceedance (6.2 mm/m) detected on Down Main Line",
    },
  },
  {
    delayMs: 70000,
    alert: {
      id: "ALT-SIM-006",
      defectId: "DEF-001",
      severity: "medium",
      defectClass: "corrugation",
      chainageM: 28400,
      message: "NOTICE: Periodic Short-Pitch Rail Corrugation on Curve #14 at Km 28+400",
    },
  },
  {
    delayMs: 90000,
    alert: {
      id: "ALT-SIM-007",
      defectId: "DEF-002",
      severity: "high",
      defectClass: "alignment_fault",
      chainageM: 35120,
      message: "WARNING: Lateral Alignment Deviation (8.4mm) exceeding RDSO Category B limits at Km 35+120",
    },
  },
  {
    delayMs: 115000,
    alert: {
      id: "ALT-SIM-008",
      defectId: "DEF-003",
      severity: "low",
      defectClass: "rough_track",
      chainageM: 42300,
      message: "INFO: Subgrade Ballast Degradation & Rough Track flagged near bridge culvert at Km 42+300",
    },
  },
  {
    delayMs: 145000,
    alert: {
      id: "ALT-SIM-009",
      defectId: "DEF-005",
      severity: "critical",
      defectClass: "crack",
      chainageM: 48900,
      message: "CRITICAL: Thermite Weld Joint Fracture Anomaly detected by Ultrasonic Scanner at Km 48+900",
    },
  },
];

export function createDemoSSESimulator(
  onAlert: (alert: AlertEvent) => void
): { stop: () => void } {
  const timeouts: ReturnType<typeof setTimeout>[] = [];

  DEMO_ALERT_SEQUENCE.forEach(({ delayMs, alert }) => {
    const timer = setTimeout(() => {
      const liveAlert: AlertEvent = {
        ...alert,
        timestamp: new Date().toISOString(),
        acknowledged: false,
      };
      onAlert(liveAlert);
    }, delayMs);

    timeouts.push(timer);
  });

  return {
    stop: () => {
      timeouts.forEach((t) => clearTimeout(t));
    },
  };
}
