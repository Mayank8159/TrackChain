// AI Bounding Box Canvas/SVG Overlay displaying real-time ML inference boxes on video frames (tc.v1).

"use client";

import React from "react";
import { getSeverityMeta } from "../../lib/severity";
import { formatConfidence } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

export interface BoundingBoxOverlayProps {
  defects?: DefectEvent[];
  currentTimeSec?: number;
  toleranceSec?: number;
  alwaysShow?: boolean;
  selectedDefectId?: string;
  className?: string;
}

export function BoundingBoxOverlay({
  defects = [],
  currentTimeSec,
  toleranceSec = 2.0,
  alwaysShow = false,
  selectedDefectId,
  className,
}: BoundingBoxOverlayProps) {
  // Filter defects active at the current playhead timestamp (or show all if alwaysShow is set)
  const activeDefects = defects.filter((d) => {
    if (selectedDefectId && d.id === selectedDefectId) return true;
    if (alwaysShow) return true;
    if (currentTimeSec === undefined || d.videoTimestampSec === undefined) return false;
    return Math.abs(currentTimeSec - d.videoTimestampSec) <= toleranceSec;
  });

  if (activeDefects.length === 0) return null;

  return (
    <div className={`absolute inset-0 pointer-events-none z-10 overflow-hidden ${className || ""}`}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        {activeDefects.map((defect) => {
          const sig = defect.supportingSignals?.[0];
          // Default bounding box if none defined: [ymin, xmin, ymax, xmax] in %
          const bbox = sig?.bbox || [45, 35, 65, 65];
          const [ymin, xmin, ymax, xmax] = bbox;

          const x = xmin;
          const y = ymin;
          const width = xmax - xmin;
          const height = ymax - ymin;

          const meta = getSeverityMeta(defect.severity);
          const isCritical = defect.severity === "critical";

          return (
            <g key={defect.id} className="transition-all duration-200">
              {/* Pulse effect for critical bounding boxes */}
              {isCritical && (
                <rect
                  x={x - 1}
                  y={y - 1}
                  width={width + 2}
                  height={height + 2}
                  fill="none"
                  stroke={meta.hex}
                  strokeWidth="0.8"
                  strokeDasharray="2 2"
                  opacity="0.6"
                  className="animate-pulse"
                />
              )}

              {/* Main AI Bounding Box Rect */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={meta.hex}
                fillOpacity="0.12"
                stroke={meta.hex}
                strokeWidth="1.2"
                vectorEffect="non-scaling-stroke"
                rx="0.5"
              />

              {/* Corner Reticle Accents */}
              <line x1={x} y1={y} x2={x + width * 0.2} y2={y} stroke="#FFFFFF" strokeWidth="1.5" />
              <line x1={x} y1={y} x2={x} y2={y + height * 0.2} stroke="#FFFFFF" strokeWidth="1.5" />
              <line x1={x + width} y1={y} x2={x + width * 0.8} y2={y} stroke="#FFFFFF" strokeWidth="1.5" />
              <line x1={x + width} y1={y} x2={x + width} y2={y + height * 0.2} stroke="#FFFFFF" strokeWidth="1.5" />

              {/* Tag Label Box above bounding box */}
              <foreignObject
                x={Math.max(2, Math.min(x, 100 - 32))}
                y={Math.max(2, y - 8)}
                width="36"
                height="8"
                className="overflow-visible"
              >
                <div
                  style={{
                    backgroundColor: "#0F172A",
                    borderColor: meta.hex,
                    borderWidth: "1px",
                  }}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-mono font-bold shadow-md whitespace-nowrap"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.hex }}
                  />
                  <span className="text-white uppercase truncate">
                    {defect.defectClass.replace("_", " ")}
                  </span>
                  <span className="text-emerald-400">
                    {formatConfidence(defect.confidence)}
                  </span>
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
