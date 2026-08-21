// Live Alerts Feed with instant acknowledgment and relative timestamp display (tc.v1).

"use client";

import React from "react";
import Link from "next/link";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { SeverityBadge } from "../ui/SeverityBadge";
import { useAlerts } from "../../hooks/useAlerts";
import { useToast } from "../ui/Toast";
import { formatChainage } from "../../lib/format";
import type { AlertEvent } from "../../lib/types";

function getRelativeTime(timestamp: string): string {
  try {
    const elapsedSec = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (elapsedSec < 30) return "Just now";
    if (elapsedSec < 60) return `${elapsedSec}s ago`;
    const mins = Math.floor(elapsedSec / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ago`;
  } catch {
    return "Recent";
  }
}

export function LiveAlertsFeed() {
  const { alerts, acknowledgeAlert } = useAlerts();
  const { showToast } = useToast();

  const activeAlerts = alerts.filter((a) => !a.acknowledged);

  const handleAcknowledge = (alert: AlertEvent) => {
    acknowledgeAlert(alert.id);
    showToast({
      type: "success",
      title: "Alert Acknowledged",
      description: `Dispatched acknowledgement for ${alert.defectClass.toUpperCase()} at Km ${(alert.chainageM / 1000).toFixed(3)}.`,
    });
  };

  return (
    <Card
      title="Live Safety Alerts Stream"
      badge={
        activeAlerts.length > 0 ? (
          <span className="badge-red animate-pulse text-[10px]">
            {activeAlerts.length} ACTIVE
          </span>
        ) : (
          <span className="badge-green text-[10px]">ALL CLEAR</span>
        )
      }
      actions={
        <Link
          href="/alerts"
          className="text-[11px] font-mono text-scada-accent hover:underline font-semibold"
        >
          View Alert Center →
        </Link>
      }
      className="h-full flex flex-col justify-between"
    >
      <div
        className="flex-1 overflow-y-auto max-h-80 divide-y divide-scada-border/60"
        role="region"
        aria-live="polite"
        aria-label="Live track safety alerts"
      >
        {activeAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center font-mono">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-2">
              <ShieldCheck size={20} />
            </div>
            <p className="text-xs font-bold text-scada-text">
              Track is Clear — No Active Alarms
            </p>
            <p className="text-[11px] text-scada-muted mt-0.5">
              All detected track geometry & vision defects have been acknowledged.
            </p>
          </div>
        ) : (
          activeAlerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-center justify-between gap-3 py-3 px-1 transition-colors hover:bg-slate-800/30"
            >
              <div className="flex items-start gap-3 min-w-0">
                <SeverityBadge severity={alert.severity} size="sm" />
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white uppercase truncate">
                      {alert.defectClass.replace("_", " ")}
                    </span>
                    <span className="text-[11px] font-mono text-cyan-400">
                      {formatChainage(alert.chainageM)}
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-scada-muted truncate mt-0.5">
                    {alert.message}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span className="text-[10px] font-mono text-slate-500">
                  {getRelativeTime(alert.timestamp)}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleAcknowledge(alert)}
                  className="text-scada-accent hover:bg-scada-accent/15 text-[10px]"
                >
                  <CheckCircle2 size={13} className="mr-1" />
                  Ack
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-scada-border flex items-center justify-between text-[10px] font-mono text-scada-muted">
        <span>Protocol: RDSO Emergency Speed Protocol</span>
        <span>SSE Stream: /api/alerts/stream</span>
      </div>
    </Card>
  );
}
