// Live anomaly event feed displaying edge-detected defects and severity levels (tc.v1).

"use client";

import { useState } from "react";
import { useAlerts } from "../hooks/useAlerts";
import type { AlertEvent, SeverityLevel } from "../lib/types";

const SEVERITY_STYLES: Record<
  string,
  { dot: string; border: string; badge: string; timeBg: string }
> = {
  info: {
    dot: "bg-scada-cyan",
    border: "border-l-scada-cyan",
    badge: "badge-cyan",
    timeBg: "bg-scada-cyan/10",
  },
  low: {
    dot: "bg-scada-cyan",
    border: "border-l-scada-cyan",
    badge: "badge-cyan",
    timeBg: "bg-scada-cyan/10",
  },
  medium: {
    dot: "bg-scada-amber",
    border: "border-l-scada-amber",
    badge: "badge-amber",
    timeBg: "bg-scada-amber/10",
  },
  warning: {
    dot: "bg-scada-amber",
    border: "border-l-scada-amber",
    badge: "badge-amber",
    timeBg: "bg-scada-amber/10",
  },
  high: {
    dot: "bg-scada-red",
    border: "border-l-scada-red",
    badge: "badge-red",
    timeBg: "bg-scada-red/10",
  },
  critical: {
    dot: "bg-scada-red animate-pulse",
    border: "border-l-scada-red",
    badge: "badge-red",
    timeBg: "bg-scada-red/10",
  },
};

function AlertRow({ alert }: { alert: AlertEvent }) {
  const sevKey = alert.severity || "info";
  const style = SEVERITY_STYLES[sevKey] || SEVERITY_STYLES.info;

  return (
    <div
      className={`border-l-2 ${style.border} bg-scada-panel/40 p-3 transition-colors hover:bg-scada-panel-header`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
          <span className="text-xs font-semibold font-mono text-scada-text">
            {alert.message}
          </span>
        </div>
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-mono font-medium ${style.timeBg} text-scada-muted`}
        >
          {new Date(alert.timestamp).toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
          })}
        </span>
      </div>
      <div className="mt-1.5 flex items-center justify-between pl-3.5">
        <span className="text-[10px] font-mono text-scada-muted">
          Chainage: {(alert.chainageM / 1000).toFixed(3)} km
        </span>
        <span
          className={`text-[10px] font-mono font-bold uppercase ${
            alert.severity === "critical"
              ? "text-scada-red"
              : alert.severity === "high"
              ? "text-scada-red"
              : "text-scada-amber"
          }`}
        >
          {alert.defectClass.replace("_", " ")}
        </span>
      </div>
    </div>
  );
}

export function AnomalyFeed() {
  const { alerts } = useAlerts();
  const [filter, setFilter] = useState<string>("all");

  const filtered =
    filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const highCount = alerts.filter((a) => a.severity === "high").length;

  return (
    <div className="scada-card flex h-full flex-col overflow-hidden border border-scada-border">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-scada-border bg-scada-panel-header px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-bold uppercase tracking-widest text-scada-muted font-mono">
            Anomaly Feed
          </h2>
          {criticalCount > 0 && (
            <span className="badge-red">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-scada-red" />
              {criticalCount} CRIT
            </span>
          )}
          {highCount > 0 && (
            <span className="badge-amber">{highCount} HIGH</span>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-scada-border bg-scada-panel px-4 py-2">
        {(["all", "critical", "high", "medium"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider transition ${
              filter === f
                ? "bg-scada-cyan/15 text-scada-cyan border border-scada-cyan/30"
                : "text-scada-muted hover:text-scada-text"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto max-h-[480px]">
        <div className="flex flex-col divide-y divide-scada-border/50">
          {filtered.map((alert) => (
            <AlertRow key={alert.id} alert={alert} />
          ))}
        </div>
        {filtered.length === 0 && (
          <div className="flex items-center justify-center py-12 text-xs font-mono text-scada-muted">
            No anomalies matching filter
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-scada-border bg-scada-panel px-4 py-2">
        <p className="text-[10px] font-mono text-scada-muted">
          {alerts.length} verified events in buffer
        </p>
      </div>
    </div>
  );
}
