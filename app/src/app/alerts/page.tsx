// Real-Time Live Safety Alert Center with SSE ingestion, audio cues, and triage actions (tc.v1).

"use client";

import React, { useState } from "react";
import {
  Volume2,
  VolumeX,
  Radio,
  Filter,
  CheckCircle2,
  ShieldCheck,
  History,
  AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AlertCard } from "@/components/alerts/AlertCard";
import { useAlerts } from "@/hooks/useAlerts";
import { useToast } from "@/components/ui/Toast";
import type { AlertEvent } from "@/lib/types";

export default function AlertsPage() {
  const {
    alerts,
    acknowledgeAlert,
    escalateAlert,
    muteClass,
    snoozedClasses,
    soundEnabled,
    toggleSound,
  } = useAlerts();

  const { showToast } = useToast();
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const filteredAlerts = alerts.filter((a) => {
    if (severityFilter !== "all" && a.severity !== severityFilter) return false;
    return true;
  });

  const activeAlerts = filteredAlerts.filter((a) => !a.acknowledged);
  const acknowledgedHistory = filteredAlerts.filter((a) => a.acknowledged);

  const handleAcknowledge = (alert: AlertEvent) => {
    acknowledgeAlert(alert.id);
    showToast({
      type: "success",
      title: "Alert Acknowledged",
      description: `Dispatched operator clearance for ${alert.defectClass.toUpperCase()} at ${(
        alert.chainageM / 1000
      ).toFixed(3)} km.`,
    });
  };

  const handleEscalate = (alert: AlertEvent) => {
    escalateAlert(alert.id);
    showToast({
      type: "warning",
      title: "Incident Escalated",
      description: `Dispatched priority SMS & PagerDuty webhook to Permanent Way Supervisor for ${alert.defectClass.toUpperCase()}.`,
    });
  };

  const handleMute = (defectClass: string) => {
    muteClass(defectClass);
    showToast({
      type: "info",
      title: "Alarms Snoozed",
      description: `Snoozed incoming real-time audio alarms for ${defectClass.replace(
        "_",
        " "
      )} for 1 hour.`,
    });
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header with SSE Connection Status and Audio Toggle */}
      <PageHeader
        title="Live Safety Alert Center"
        description="Immediate Action Limit (IAL) dispatch board with real-time SSE ingestion and audio triage"
        breadcrumbs={[{ label: "Alerts" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Live SSE Link Indicator */}
            <div className="flex items-center gap-1.5 rounded-control bg-slate-900 border border-scada-border px-3 py-1.5 font-mono text-xs text-scada-muted">
              <Radio size={13} className="text-emerald-400 animate-pulse" />
              <span>STREAM:</span>
              <strong className="text-emerald-400">LIVE SSE</strong>
            </div>

            {/* Audio Alert Toggle */}
            <Button
              variant={soundEnabled ? "primary" : "secondary"}
              size="md"
              onClick={toggleSound}
              className="text-xs font-mono font-bold"
              title={soundEnabled ? "Mute audio alarms" : "Enable browser audio alarms"}
            >
              {soundEnabled ? (
                <>
                  <Volume2 size={14} className="mr-1.5 text-white animate-pulse" />
                  Sound: ON
                </>
              ) : (
                <>
                  <VolumeX size={14} className="mr-1.5 text-slate-400" />
                  Sound: OFF
                </>
              )}
            </Button>
          </div>
        }
      />

      {/* 2. Top Severity Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-control border border-scada-border font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-scada-muted">Severity Filter:</span>
          {(["all", "critical", "high", "medium"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 rounded text-xs uppercase transition ${
                severityFilter === sev
                  ? "bg-scada-accent/20 text-scada-accent border border-scada-accent font-bold"
                  : "bg-slate-800 text-scada-muted border border-scada-border hover:text-white"
              }`}
            >
              {sev} (
              {sev === "all"
                ? alerts.length
                : alerts.filter((a) => a.severity === sev).length}
              )
            </button>
          ))}
        </div>

        {snoozedClasses.length > 0 && (
          <span className="text-[11px] text-amber-400 font-semibold">
            Snoozed Alarm Classes: {snoozedClasses.join(", ")}
          </span>
        )}
      </div>

      {/* 3. Section 1: Active / Unacknowledged Alerts */}
      <Card
        title={`Pending Safety Incidents (${activeAlerts.length})`}
        badge={
          activeAlerts.length > 0 ? (
            <span className="badge-red animate-pulse text-[10px]">
              {activeAlerts.length} ACTION REQUIRED
            </span>
          ) : (
            <span className="badge-green text-[10px]">ALL CLEAR</span>
          )
        }
      >
        <div
          className="space-y-4"
          role="region"
          aria-live="polite"
          aria-label="Active safety alerts"
        >
          {activeAlerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center font-mono">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-3">
                <ShieldCheck size={26} />
              </div>
              <p className="text-sm font-bold text-white uppercase">
                Track Corridor is Clear
              </p>
              <p className="text-xs text-scada-muted mt-1 max-w-md">
                Zero unacknowledged Immediate Action Limit (IAL) defects active across Northern Railway NDLS-AGC mainline.
              </p>
            </div>
          ) : (
            activeAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledge}
                onEscalate={handleEscalate}
                onMute={handleMute}
              />
            ))
          )}
        </div>
      </Card>

      {/* 4. Section 2: Acknowledged Incident History */}
      <Card
        title={`Acknowledged Incident History (${acknowledgedHistory.length})`}
        badge={
          <span className="badge-cyan text-[10px]">
            CLEARED LOG
          </span>
        }
        actions={<History size={16} className="text-scada-muted" />}
      >
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {acknowledgedHistory.length === 0 ? (
            <div className="py-8 text-center font-mono text-xs text-scada-muted">
              No historical acknowledged incidents in current session.
            </div>
          ) : (
            acknowledgedHistory.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
              />
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
