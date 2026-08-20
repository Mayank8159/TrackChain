// Side drawer: evidence, model attribution, signals, actions.

"use client";

import React from "react";
import Link from "next/link";
import { SeverityBadge } from "./SeverityBadge";
import { Button } from "../ui/Button";
import { formatChainage, formatTimestamp, formatConfidence } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

interface DefectDetailDrawerProps {
  defect: DefectEvent | null;
  onClose: () => void;
  onAcknowledge?: (id: string) => void;
}

export function DefectDetailDrawer({
  defect,
  onClose,
  onAcknowledge,
}: DefectDetailDrawerProps) {
  if (!defect) return null;

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-scada-border bg-scada-panel p-5 font-mono text-xs shadow-xl">
      <div className="flex items-center justify-between border-b border-scada-border pb-3">
        <div>
          <h3 className="text-sm font-bold uppercase text-scada-text">
            {defect.id}
          </h3>
          <span className="text-[10px] text-scada-muted">
            Session: {defect.sessionId}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-scada-muted hover:text-scada-text text-sm"
        >
          ✕
        </button>
      </div>

      <div className="flex items-center gap-2">
        <SeverityBadge severity={defect.severity} />
        <span className="badge-cyan">{defect.streamSource.toUpperCase()} STREAM</span>
      </div>

      {/* Snapshot Preview */}
      <div className="relative aspect-video w-full rounded border border-scada-border bg-black/60 flex items-center justify-center scada-grid">
        <div className="flex flex-col items-center gap-1 text-center p-3">
          <span className="h-3 w-3 rounded-full bg-scada-red animate-ping" />
          <p className="font-bold text-scada-text uppercase text-xs">
            {defect.defectClass.replace("_", " ")}
          </p>
          <p className="text-[10px] text-scada-muted">
            Loc: {formatChainage(defect.chainageM)}
          </p>
        </div>
      </div>

      {/* Attributes */}
      <div className="space-y-2 rounded bg-scada-panel-header p-3 border border-scada-border text-[11px]">
        <div className="flex justify-between">
          <span className="text-scada-muted">Classification:</span>
          <span className="font-bold text-scada-text uppercase">
            {defect.defectClass.replace("_", " ")}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-scada-muted">Model Confidence:</span>
          <span className="font-bold text-scada-green">
            {formatConfidence(defect.confidence)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-scada-muted">Video Timestamp:</span>
          <span className="text-scada-cyan">{defect.videoTimestampSec || 0}s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-scada-muted">Detection Time:</span>
          <span className="text-scada-text">{formatTimestamp(defect.timestamp)}</span>
        </div>
      </div>

      {defect.description && (
        <p className="text-xs text-scada-muted leading-relaxed">
          {defect.description}
        </p>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col gap-2 pt-2 border-t border-scada-border">
        {defect.status === "open" && onAcknowledge && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => onAcknowledge(defect.id)}
          >
            Acknowledge Defect
          </Button>
        )}
        <Link href={`/video?seek=${defect.videoTimestampSec || 0}`}>
          <Button variant="secondary" size="sm" className="w-full">
            Play Synced Video Clip
          </Button>
        </Link>
        <Link href="/map">
          <Button variant="outline" size="sm" className="w-full">
            Inspect on GIS Track Map
          </Button>
        </Link>
      </div>
    </div>
  );
}
