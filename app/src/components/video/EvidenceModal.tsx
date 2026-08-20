// Fullscreen defect evidence image with metadata overlay.

"use client";

import React from "react";
import { Modal } from "../ui/Modal";
import { SeverityBadge } from "../defects/SeverityBadge";
import { formatChainage, formatTimestamp, formatConfidence } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

interface EvidenceModalProps {
  defect: DefectEvent | null;
  isOpen: boolean;
  onClose: () => void;
}

export function EvidenceModal({
  defect,
  isOpen,
  onClose,
}: EvidenceModalProps) {
  if (!defect) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Defect Evidence: ${defect.id}`}>
      <div className="flex flex-col gap-4 font-mono text-xs">
        {/* Evidence Snapshot Frame */}
        <div className="relative aspect-video w-full rounded border border-scada-border bg-black/90 flex items-center justify-center overflow-hidden scada-grid">
          {defect.imageUrl ? (
            <img
              src={defect.imageUrl}
              alt={defect.defectClass}
              className="h-full w-full object-contain"
            />
          ) : (
            <div className="flex flex-col items-center gap-2 text-center p-6">
              <span className="h-4 w-4 rounded-full bg-scada-red animate-ping" />
              <p className="font-bold text-scada-text uppercase text-sm">
                {defect.defectClass.replace("_", " ")}
              </p>
              <p className="text-[10px] text-scada-muted">
                Frame Capture at {formatChainage(defect.chainageM)}
              </p>
            </div>
          )}

          {/* HUD Overlay */}
          <div className="absolute top-2 left-2 z-10 flex gap-2">
            <SeverityBadge severity={defect.severity} />
            <span className="badge-cyan">{defect.streamSource.toUpperCase()} STREAM</span>
          </div>
        </div>

        {/* Diagnostic Metadata Grid */}
        <div className="grid grid-cols-2 gap-3 bg-scada-panel-header p-3 rounded border border-scada-border text-[11px]">
          <div>
            <span className="text-scada-muted">Chainage:</span>{" "}
            <strong className="text-scada-cyan">{formatChainage(defect.chainageM)}</strong>
          </div>
          <div>
            <span className="text-scada-muted">Confidence:</span>{" "}
            <strong className="text-scada-green">{formatConfidence(defect.confidence)}</strong>
          </div>
          <div>
            <span className="text-scada-muted">Captured At:</span>{" "}
            <span className="text-scada-text">{formatTimestamp(defect.timestamp)}</span>
          </div>
          <div>
            <span className="text-scada-muted">Status:</span>{" "}
            <span className="text-scada-amber uppercase">{defect.status}</span>
          </div>
        </div>

        {defect.description && (
          <p className="text-scada-muted leading-relaxed border-t border-scada-border pt-2">
            {defect.description}
          </p>
        )}
      </div>
    </Modal>
  );
}
