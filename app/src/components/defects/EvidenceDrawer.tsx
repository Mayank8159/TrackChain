// Slide-in Evidence Drawer for human-in-the-loop defect verification and feedback (tc.v1).

"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import {
  X,
  CheckCircle2,
  XCircle,
  Users,
  Cpu,
  Activity,
  Gauge,
  Zap,
  Crosshair,
  FileCheck,
  Video,
} from "lucide-react";
import { Button } from "../ui/Button";
import { SeverityBadge } from "../ui/SeverityBadge";
import { BoundingBoxOverlay } from "../video/BoundingBoxOverlay";
import { formatChainage, formatTimestamp, formatConfidence } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

export interface EvidenceDrawerProps {
  defect: DefectEvent | null;
  isOpen: boolean;
  onClose: () => void;
  onAcknowledge?: (defect: DefectEvent) => void;
  onReject?: (defect: DefectEvent) => void;
  onAssign?: (defect: DefectEvent) => void;
  isMutating?: boolean;
}

export function EvidenceDrawer({
  defect,
  isOpen,
  onClose,
  onAcknowledge,
  onReject,
  onAssign,
  isMutating = false,
}: EvidenceDrawerProps) {
  // ESC key dismissal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !defect) return null;

  const isAcknowledged = defect.status === "acknowledged";
  const isDismissed = defect.status === "false_positive";

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-in Sheet Container */}
      <div className="relative z-10 w-full max-w-2xl bg-slate-900 border-l border-scada-border shadow-2xl flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200">
        {/* 1. Header */}
        <div className="p-4 border-b border-scada-border flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <SeverityBadge severity={defect.severity} />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-white text-base">
                  {defect.id}
                </h3>
                <span className="text-xs font-mono text-cyan-400 font-bold">
                  {formatChainage(defect.chainageM)}
                </span>
              </div>
              <p className="text-[11px] font-mono text-scada-muted uppercase">
                {defect.defectClass.replaceAll("_", " ")} · {defect.streamSource} STREAM
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-control text-scada-muted hover:text-white hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
          {/* Status Alert Banner */}
          {isAcknowledged && (
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-2.5 rounded-control">
              <CheckCircle2 size={16} className="shrink-0" />
              <span>
                Verified & Acknowledged by {defect.acknowledgedBy || "Chief Track Inspector"} at{" "}
                {defect.acknowledgedAt ? formatTimestamp(defect.acknowledgedAt) : "Recently"}
              </span>
            </div>
          )}

          {isDismissed && (
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 p-2.5 rounded-control">
              <XCircle size={16} className="shrink-0" />
              <span>Marked as False Positive / Dismissed from Active Defect Register</span>
            </div>
          )}

          {/* Visual Evidence Snapshot Frame with Bounding Box Overlay */}
          <div className="space-y-1.5">
            <span className="text-[11px] font-bold uppercase text-scada-muted">
              AI Optical Visual Evidence & Bounding Box
            </span>

            <div className="relative aspect-video w-full rounded-lg border border-scada-border bg-black overflow-hidden flex items-center justify-center scada-grid">
              {/* Synthetic Camera Perspective */}
              <svg viewBox="0 0 600 340" className="w-full h-full opacity-60">
                <line x1="160" y1="340" x2="260" y2="120" stroke="#38BDF8" strokeWidth="4" />
                <line x1="440" y1="340" x2="340" y2="120" stroke="#38BDF8" strokeWidth="4" />
                {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => {
                  const y = 120 + ratio * 220;
                  const x1 = 260 - ratio * 100;
                  const x2 = 340 + ratio * 100;
                  return (
                    <line
                      key={i}
                      x1={x1}
                      y1={y}
                      x2={x2}
                      y2={y}
                      stroke="#475569"
                      strokeWidth="7"
                    />
                  );
                })}
              </svg>

              {/* Real-time Bounding Box Overlay */}
              <BoundingBoxOverlay defects={[defect]} alwaysShow={true} />

              {/* HUD Header Tag */}
              <div className="absolute top-2 left-2 z-20 flex gap-2">
                <span className="badge-cyan text-[9px]">
                  STREAM: {defect.streamSource.toUpperCase()}
                </span>
                <span className="badge-red text-[9px]">
                  CONF: {formatConfidence(defect.confidence)}
                </span>
              </div>
            </div>
          </div>

          {/* ML Metadata Card */}
          <div className="scada-card p-3 border border-scada-border space-y-2">
            <div className="flex items-center gap-2 text-scada-muted font-bold">
              <Cpu size={14} className="text-cyan-400" />
              <span className="uppercase text-[11px]">Neural Inference Diagnostics</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-scada-muted">Detection Model:</span>{" "}
                <strong className="text-white">{defect.sourceModel || "YOLOv8-Rail-Head-v2"}</strong>
              </div>
              <div>
                <span className="text-scada-muted">Model Version:</span>{" "}
                <strong className="text-cyan-400">{defect.modelVersion || "2.4.1 (ONNX)"}</strong>
              </div>
              <div>
                <span className="text-scada-muted">Calibrated Score:</span>{" "}
                <strong className="text-emerald-400">{formatConfidence(defect.confidence)}</strong>
              </div>
              <div>
                <span className="text-scada-muted">Inference Latency:</span>{" "}
                <strong className="text-white">14.8 ms (ARM64 Edge)</strong>
              </div>
            </div>
          </div>

          {/* Telemetry Physics Context Card */}
          <div className="scada-card p-3 border border-scada-border space-y-2">
            <div className="flex items-center gap-2 text-scada-muted font-bold">
              <Activity size={14} className="text-emerald-400" />
              <span className="uppercase text-[11px]">Telemetry & Track Geometry Context</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-scada-muted">GPS Coordinates:</span>{" "}
                <span className="text-white">
                  {defect.latitude?.toFixed(4) || "28.5920"}°N, {defect.longitude?.toFixed(4) || "77.2480"}°E
                </span>
              </div>
              <div>
                <span className="text-scada-muted">Track Gauge:</span>{" "}
                <span className="text-amber-400 font-bold">1448.0 mm (+13mm)</span>
              </div>
              <div>
                <span className="text-scada-muted">Vibration RMS:</span>{" "}
                <span className="text-red-400 font-bold">2.85 g (Threshold: 2.2g)</span>
              </div>
              <div>
                <span className="text-scada-muted">Track Twist:</span>{" "}
                <span className="text-amber-400 font-bold">4.2 mm/m</span>
              </div>
            </div>

            <p className="text-[11px] text-scada-muted pt-1 border-t border-scada-border/60">
              {defect.description}
            </p>
          </div>
        </div>

        {/* 3. Sticky Action Footer */}
        <div className="p-4 border-t border-scada-border bg-slate-950 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Link
              href={`/sessions/${defect.sessionId || "ses-delhi-agra-001"}?seek=${defect.videoTimestampSec || 0}`}
            >
              <Button variant="outline" size="md" className="text-xs">
                <Video size={14} className="mr-1.5 text-cyan-400" />
                View in Session ▶
              </Button>
            </Link>

            <Button
              variant="danger"
              size="md"
              onClick={() => onReject && onReject(defect)}
              disabled={isMutating || isDismissed}
              className="text-xs"
            >
              <XCircle size={14} className="mr-1.5" />
              Reject (False Positive)
            </Button>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <Button
              variant="outline"
              size="md"
              onClick={() => onAssign && onAssign(defect)}
              disabled={isMutating}
              className="text-xs"
            >
              <Users size={14} className="mr-1.5" />
              Assign Crew
            </Button>

            <Button
              variant="primary"
              size="md"
              onClick={() => onAcknowledge && onAcknowledge(defect)}
              disabled={isMutating || isAcknowledged}
              className="text-xs"
            >
              <CheckCircle2 size={14} className="mr-1.5" />
              {isAcknowledged ? "Acknowledged" : "Acknowledge"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
