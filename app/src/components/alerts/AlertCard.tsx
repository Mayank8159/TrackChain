// Operational Alert Card with severity left-border, triage actions, and deep video seeking (tc.v1).

"use client";

import React from "react";
import Link from "next/link";
import {
  CheckCircle2,
  AlertTriangle,
  Siren,
  BellOff,
  Send,
  Video,
  Clock,
  MapPin,
  Cpu,
} from "lucide-react";
import { Button } from "../ui/Button";
import { SeverityBadge } from "../ui/SeverityBadge";
import { getSeverityMeta } from "../../lib/severity";
import { formatChainage, formatTimestamp } from "../../lib/format";
import { cn } from "../../lib/utils";
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

export interface AlertCardProps {
  alert: AlertEvent;
  onAcknowledge?: (alert: AlertEvent) => void;
  onEscalate?: (alert: AlertEvent) => void;
  onMute?: (defectClass: string) => void;
  className?: string;
}

export function AlertCard({
  alert,
  onAcknowledge,
  onEscalate,
  onMute,
  className,
}: AlertCardProps) {
  const meta = getSeverityMeta(alert.severity);
  const isCritical = alert.severity === "critical";
  const isAck = alert.acknowledged;

  return (
    <div
      className={cn(
        "relative rounded-lg border bg-slate-900/90 p-4 transition-all duration-200 shadow-md",
        isAck
          ? "border-scada-border/70 opacity-75"
          : isCritical
          ? "border-red-500/60 shadow-lg shadow-red-500/10"
          : "border-amber-500/40",
        className
      )}
      style={{
        borderLeftWidth: "4px",
        borderLeftColor: meta.hex,
      }}
    >
      {/* 1. Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-scada-border/60 pb-2.5">
        <div className="flex items-center gap-3">
          <SeverityBadge severity={alert.severity} size="sm" />
          <h3 className="font-mono font-bold text-white text-sm uppercase tracking-wide">
            {(alert.defectClass || (alert as any).defect_class || "anomaly").replace(/_/g, " ")}
          </h3>
          <span className="text-xs font-mono font-bold text-cyan-400">
            {formatChainage(alert.chainageM ?? (alert as any).chainage_m ?? 0)}
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px] text-scada-muted">
          <Clock size={12} />
          <span>{getRelativeTime(alert.timestamp)}</span>
          <span>({formatTimestamp(alert.timestamp)})</span>
        </div>
      </div>

      {/* 2. Message Body */}
      <div className="mt-2.5">
        <p className="text-xs font-mono text-slate-200 leading-relaxed">
          {alert.message}
        </p>

        {/* Operational Context Sub-line */}
        <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-[10px] text-scada-muted bg-slate-950/60 p-2 rounded border border-scada-border/40">
          <div className="flex items-center gap-1">
            <MapPin size={11} className="text-cyan-400" />
            <span>Corridor: NDLS-AGC (Down Main)</span>
          </div>
          <div className="flex items-center gap-1">
            <Cpu size={11} className="text-emerald-400" />
            <span>Acquisition Node: DEV-EDGE-01</span>
          </div>
          <div>
            <span>Defect Ref: </span>
            <strong className="text-white">{alert.defectId}</strong>
          </div>
        </div>
      </div>

      {/* 3. Action Footer */}
      <div className="mt-3 pt-2.5 border-t border-scada-border/60 flex flex-wrap items-center justify-between gap-3">
        {/* Deep link to video evidence */}
        <Link
          href={`/sessions/ses-delhi-agra-001?seek=${(
            Math.max(0, Math.min(1, alert.chainageM / 25000)) * 60
          ).toFixed(1)}`}
        >
          <Button variant="outline" size="sm" className="text-[11px]">
            <Video size={13} className="mr-1.5 text-cyan-400" />
            View in Session ▶
          </Button>
        </Link>

        {/* Triage Action Buttons */}
        <div className="flex items-center gap-2 ml-auto">
          {!isAck ? (
            <>
              {/* Mute 1h button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onMute && onMute(alert.defectClass)}
                className="text-[11px] text-scada-muted hover:text-white"
                title="Snooze alerts of this class for 1 hour"
              >
                <BellOff size={13} className="mr-1" />
                Mute 1h
              </Button>

              {/* Escalate button */}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onEscalate && onEscalate(alert)}
                className="text-[11px] text-amber-400 hover:text-amber-300"
                title="Dispatch SMS / Webhook to Section Supervisor"
              >
                <Send size={13} className="mr-1" />
                Escalate
              </Button>

              {/* Acknowledge button */}
              <Button
                variant="primary"
                size="sm"
                onClick={() => onAcknowledge && onAcknowledge(alert)}
                className="text-[11px]"
              >
                <CheckCircle2 size={13} className="mr-1" />
                Acknowledge
              </Button>
            </>
          ) : (
            <div className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-control border border-emerald-500/30">
              <CheckCircle2 size={13} />
              <span>Acknowledged by {alert.acknowledgedBy || "Operator"}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
