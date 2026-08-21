// Signature Route Line Diagram visualizing track corridor health, TQI segments, and defects (tc.v1).

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Card } from "../ui/Card";
import { SeverityBadge } from "../ui/SeverityBadge";
import { getSeverityMeta } from "../../lib/severity";
import { formatChainage } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

interface RouteLineDiagramProps {
  defects?: DefectEvent[];
  totalKm?: number;
  corridorName?: string;
  className?: string;
}

interface StationMilestone {
  code: string;
  name: string;
  km: number;
}

const STATIONS: StationMilestone[] = [
  { code: "NDLS", name: "New Delhi", km: 0 },
  { code: "NZM", name: "H. Nizamuddin", km: 7.2 },
  { code: "FDB", name: "Faridabad", km: 28.5 },
  { code: "PWL", name: "Palwal", km: 58.0 },
  { code: "KSV", name: "Kosi Kalan", km: 99.0 },
  { code: "MTJ", name: "Mathura Jn", km: 134.0 },
  { code: "AGC", name: "Agra Cantt", km: 140.0 },
];

const TQI_SEGMENTS = [
  { startKm: 0, endKm: 42, tqi: 92, status: "ok", color: "#10B981" },
  { startKm: 42, endKm: 78, tqi: 76, status: "medium", color: "#F59E0B" },
  { startKm: 78, endKm: 112, tqi: 89, status: "ok", color: "#10B981" },
  { startKm: 112, endKm: 126, tqi: 68, status: "high", color: "#F97316" },
  { startKm: 126, endKm: 140, tqi: 91, status: "ok", color: "#10B981" },
];

export function RouteLineDiagram({
  defects = [],
  totalKm = 140,
  corridorName = "Northern Railway — Delhi-Agra Mainline (Down Track)",
  className,
}: RouteLineDiagramProps) {
  const [hoveredDefect, setHoveredDefect] = useState<DefectEvent | null>(null);

  // SVG viewBox coordinates
  const svgWidth = 1000;
  const svgHeight = 180;
  const paddingX = 50;
  const trackY = 85;
  const trackWidth = svgWidth - paddingX * 2;

  const kmToX = (km: number) => paddingX + (km / totalKm) * trackWidth;

  return (
    <Card
      title={`Route Line Diagram: ${corridorName}`}
      badge={
        <span className="badge-cyan text-[10px]">
          {totalKm} KM MONITORED
        </span>
      }
      actions={
        <div className="flex items-center gap-3 text-[10px] font-mono text-scada-muted">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>TQI &gt; 85</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span>TQI 70-85</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-orange-500" />
            <span>TQI &lt; 70</span>
          </div>
        </div>
      }
      className={className}
    >
      <div className="relative w-full overflow-x-auto">
        <div className="min-w-[850px] py-2">
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-auto select-none overflow-visible"
          >
            {/* Background Grid Lines */}
            <line
              x1={paddingX}
              y1={trackY}
              x2={paddingX + trackWidth}
              y2={trackY}
              stroke="#334155"
              strokeWidth="10"
              strokeLinecap="round"
            />

            {/* 1. Colored TQI Track Segments */}
            {TQI_SEGMENTS.map((seg, i) => {
              const x1 = kmToX(seg.startKm);
              const x2 = kmToX(seg.endKm);
              return (
                <g key={i}>
                  <line
                    x1={x1}
                    y1={trackY}
                    x2={x2}
                    y2={trackY}
                    stroke={seg.color}
                    strokeWidth="6"
                    strokeLinecap="butt"
                    className="transition-all hover:stroke-width-[8]"
                  />
                  {/* Segment TQI label */}
                  <text
                    x={(x1 + x2) / 2}
                    y={trackY + 22}
                    fill="#94A3B8"
                    fontSize="9"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    TQI {seg.tqi}
                  </text>
                </g>
              );
            })}

            {/* 2. Station Milestones & KM Ticks */}
            {STATIONS.map((station) => {
              const x = kmToX(station.km);
              return (
                <g key={station.code} transform={`translate(${x}, 0)`}>
                  {/* Vertical milestone tick */}
                  <line
                    x1="0"
                    y1={trackY - 14}
                    x2="0"
                    y2={trackY + 14}
                    stroke="#475569"
                    strokeWidth="1.5"
                  />
                  {/* Milestone station circle */}
                  <circle
                    cx="0"
                    cy={trackY}
                    r="4.5"
                    fill="#0F172A"
                    stroke="#3B82F6"
                    strokeWidth="2"
                  />
                  {/* Station Code & Name */}
                  <text
                    x="0"
                    y={trackY - 22}
                    fill="#F1F5F9"
                    fontSize="11"
                    fontFamily="monospace"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {station.code}
                  </text>
                  <text
                    x="0"
                    y={trackY - 34}
                    fill="#64748B"
                    fontSize="8"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {station.name}
                  </text>
                  {/* KM marker */}
                  <text
                    x="0"
                    y={trackY + 38}
                    fill="#94A3B8"
                    fontSize="9"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    Km {station.km}
                  </text>
                </g>
              );
            })}

            {/* 3. Defect Anomaly Markers */}
            {defects.map((defect) => {
              const km = defect.chainageM / 1000;
              const x = kmToX(km);
              const meta = getSeverityMeta(defect.severity);
              const isCritical = defect.severity === "critical";
              const isHovered = hoveredDefect?.id === defect.id;

              return (
                <g
                  key={defect.id}
                  transform={`translate(${x}, ${trackY})`}
                  className="cursor-pointer group"
                  onMouseEnter={() => setHoveredDefect(defect)}
                  onMouseLeave={() => setHoveredDefect(null)}
                >
                  {/* Pulse ring for critical defects */}
                  {isCritical && (
                    <circle
                      cx="0"
                      cy="0"
                      r="12"
                      fill={meta.hex}
                      fillOpacity="0.3"
                      className="animate-ping"
                    />
                  )}

                  {/* Outer glow circle */}
                  <circle
                    cx="0"
                    cy="0"
                    r={isHovered ? "9" : "7"}
                    fill={meta.hex}
                    fillOpacity={isHovered ? "0.9" : "0.75"}
                    stroke="#0F172A"
                    strokeWidth="2"
                    className="transition-all"
                  />

                  {/* Center core pin */}
                  <circle cx="0" cy="0" r="2.5" fill="#FFFFFF" />

                  {/* Defect Tag on hover */}
                  <g
                    transform={`translate(0, ${isCritical ? -28 : 28})`}
                    className={isHovered ? "opacity-100" : "opacity-0 group-hover:opacity-100 transition-opacity"}
                  >
                    <rect
                      x="-45"
                      y="-12"
                      width="90"
                      height="24"
                      rx="4"
                      fill="#1E293B"
                      stroke={meta.hex}
                      strokeWidth="1"
                    />
                    <text
                      x="0"
                      y="3"
                      fill="#F1F5F9"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {defect.id} (Km {km.toFixed(1)})
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Dynamic Detail Card when Defect is Hovered */}
        {hoveredDefect && (
          <div className="mt-3 flex items-center justify-between rounded-control border border-scada-border bg-slate-950/80 p-3 font-mono text-xs backdrop-blur">
            <div className="flex items-center gap-3">
              <SeverityBadge severity={hoveredDefect.severity} size="sm" />
              <span className="font-bold text-white uppercase">
                {(hoveredDefect.defectClass || (hoveredDefect as any).defect_class || "anomaly").replace(/_/g, " ")}
              </span>
              <span className="text-scada-muted">
                Chainage: <strong className="text-cyan-400">{formatChainage(hoveredDefect.chainageM ?? (hoveredDefect as any).chainage_m ?? 0)}</strong>
              </span>
              <span className="text-scada-muted">
                Confidence: <strong className="text-emerald-400">{(hoveredDefect.confidence * 100).toFixed(1)}%</strong>
              </span>
            </div>

            <Link
              href={`/video?seek=${hoveredDefect.videoTimestampSec || 0}`}
              className="text-scada-accent hover:underline flex items-center gap-1 font-bold uppercase text-[11px]"
            >
              Inspect Frame Footage →
            </Link>
          </div>
        )}
      </div>
    </Card>
  );
}
