"use client";

import { useState, useEffect } from "react";

type Severity = "info" | "warning" | "critical";

interface Alert {
  id: number;
  timestamp: string;
  severity: Severity;
  camera: string;
  message: string;
  value?: string;
}

const MOCK_ALERTS: Omit<Alert, "id" | "timestamp">[] = [
  {
    severity: "critical",
    camera: "CAM-SECTOR-A1",
    message: "Gauge widening detected",
    value: "+12mm",
  },
  {
    severity: "warning",
    camera: "CAM-SECTOR-B3",
    message: "Cant deficiency approaching limit",
    value: "+38mm",
  },
  {
    severity: "info",
    camera: "CAM-SECTOR-C2",
    message: "Periodic scan complete",
  },
  {
    severity: "warning",
    camera: "CAM-SECTOR-A1",
    message: "Alignment deviation exceeds threshold",
    value: "+9mm",
  },
  {
    severity: "critical",
    camera: "CAM-SECTOR-B3",
    message: "Potential rail fracture signature",
  },
  {
    severity: "info",
    camera: "CAM-SECTOR-C2",
    message: "Camera auto-calibrated",
  },
  {
    severity: "warning",
    camera: "CAM-SECTOR-A1",
    message: "Sleeper spacing anomaly",
    value: "Δ42mm",
  },
  {
    severity: "critical",
    camera: "CAM-SECTOR-B3",
    message: "Bogie detection zone overlap",
  },
  {
    severity: "info",
    camera: "CAM-SECTOR-C2",
    message: "ML inference model updated",
  },
  {
    severity: "warning",
    camera: "CAM-SECTOR-A1",
    message: "Excessive cross-level variation",
    value: "+7mm",
  },
];

const SEVERITY_STYLES: Record<Severity, { dot: string; border: string; badge: string; timeBg: string }> = {
  info: {
    dot: "bg-scada-blue",
    border: "border-l-scada-blue",
    badge: "badge-blue",
    timeBg: "bg-scada-blue/10",
  },
  warning: {
    dot: "bg-scada-amber",
    border: "border-l-scada-amber",
    badge: "badge-amber",
    timeBg: "bg-scada-amber/10",
  },
  critical: {
    dot: "bg-scada-red animate-pulse",
    border: "border-l-scada-red",
    badge: "badge-red",
    timeBg: "bg-scada-red/10",
  },
};

let nextId = 1;

function generateAlert(): Alert {
  const base = MOCK_ALERTS[Math.floor(Math.random() * MOCK_ALERTS.length)];
  return {
    ...base,
    id: nextId++,
    timestamp: new Date().toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }),
  };
}

function AlertRow({ alert }: { alert: Alert }) {
  const style = SEVERITY_STYLES[alert.severity];

  return (
    <div
      className={`animate-fade-in border-l-2 ${style.border} bg-scada-panel/40 p-3`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
          <span className="text-xs font-semibold text-scada-text">
            {alert.message}
          </span>
        </div>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium ${style.timeBg} text-scada-muted`}>
          {alert.timestamp}
        </span>
      </div>
      <div className="mt-1.5 flex items-center gap-2 pl-3.5">
        <span className="text-[10px] text-scada-muted">{alert.camera}</span>
        {alert.value && (
          <span className={`text-[10px] font-bold ${style.badge === "badge-red" ? "text-scada-red" : style.badge === "badge-amber" ? "text-scada-amber" : "text-scada-blue"}`}>
            {alert.value}
          </span>
        )}
      </div>
    </div>
  );
}

export function AnomalyFeed() {
  const [alerts, setAlerts] = useState<Alert[]>(() =>
    Array.from({ length: 6 }, () => generateAlert()),
  );
  const [filter, setFilter] = useState<Severity | "all">("all");

  useEffect(() => {
    const id = setInterval(() => {
      setAlerts((prev) => [generateAlert(), ...prev].slice(0, 30));
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const warningCount = alerts.filter((a) => a.severity === "warning").length;

  return (
    <div className="glass-panel-lg flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-scada-border px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-bold uppercase tracking-widest text-scada-muted">
            Anomaly Feed
          </h2>
          {criticalCount > 0 && (
            <span className="badge-red">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-scada-red" />
              {criticalCount} CRIT
            </span>
          )}
          {warningCount > 0 && (
            <span className="badge-amber">{warningCount} WARN</span>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-scada-border px-4 py-2">
        {(["all", "critical", "warning", "info"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition ${
              filter === f
                ? "bg-scada-cyan/15 text-scada-cyan"
                : "text-scada-muted hover:text-scada-text"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col divide-y divide-scada-border/50">
          {filtered.map((alert) => (
            <AlertRow key={alert.id} alert={alert} />
          ))}
        </div>
        {filtered.length === 0 && (
          <div className="flex items-center justify-center py-12 text-xs text-scada-muted">
            No alerts matching filter
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-scada-border px-4 py-2">
        <p className="text-[10px] text-scada-muted">
          {alerts.length} events in buffer
        </p>
      </div>
    </div>
  );
}
