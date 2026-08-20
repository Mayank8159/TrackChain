// Charts geometry features (twist, cross-level, versine) vs chainage.

"use client";

import React, { useMemo } from "react";
import type { TelemetryPoint } from "../../lib/types";

interface GeometryChartProps {
  data: TelemetryPoint[];
  height?: number;
}

export function GeometryChart({ data, height = 220 }: GeometryChartProps) {
  const chartWidth = 700;
  const padding = 15;
  const innerHeight = height - padding * 2;

  const pointsTwist = useMemo(() => {
    if (!data || data.length === 0) return "";
    return data
      .map((d, i) => {
        const x = (i / (data.length - 1 || 1)) * chartWidth;
        const val = d.twistMmPerM || 0;
        const y = height / 2 - (val / 6.0) * (innerHeight / 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data, height, innerHeight]);

  const pointsGauge = useMemo(() => {
    if (!data || data.length === 0) return "";
    return data
      .map((d, i) => {
        const x = (i / (data.length - 1 || 1)) * chartWidth;
        const val = (d.trackGaugeMm || 1435) - 1435;
        const y = height / 2 - (val / 20.0) * (innerHeight / 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data, height, innerHeight]);

  return (
    <div className="flex flex-col gap-2 font-mono">
      <div className="flex items-center justify-between text-xs text-scada-muted">
        <span>EN 13848 Track Geometry Superimposed Waveform</span>
        <div className="flex items-center gap-4 text-[10px]">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-scada-red" /> Twist (mm/m)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-scada-amber" /> Gauge Dev Δ (mm)
          </span>
        </div>
      </div>

      <div className="relative rounded border border-scada-border bg-scada-bg/80 p-2 overflow-hidden">
        <svg
          viewBox={`0 0 ${chartWidth} ${height}`}
          className="w-full h-auto overflow-visible"
          preserveAspectRatio="none"
        >
          {/* Nominal Zero Axis */}
          <line
            x1="0"
            y1={height / 2}
            x2={chartWidth}
            y2={height / 2}
            stroke="#334155"
            strokeWidth="1.5"
            strokeDasharray="4 2"
          />

          {/* Upper / Lower Alert Limit Lines */}
          <line
            x1="0"
            y1={height / 2 - (3.0 / 6.0) * (innerHeight / 2)}
            x2={chartWidth}
            y2={height / 2 - (3.0 / 6.0) * (innerHeight / 2)}
            stroke="#FFB300"
            strokeWidth="1"
            strokeDasharray="2 4"
            opacity="0.5"
          />
          <line
            x1="0"
            y1={height / 2 + (3.0 / 6.0) * (innerHeight / 2)}
            x2={chartWidth}
            y2={height / 2 + (3.0 / 6.0) * (innerHeight / 2)}
            stroke="#FFB300"
            strokeWidth="1"
            strokeDasharray="2 4"
            opacity="0.5"
          />

          {/* Gauge Waveform */}
          <polyline
            fill="none"
            stroke="#FFB300"
            strokeWidth="2"
            strokeLinecap="round"
            points={pointsGauge}
          />

          {/* Twist Waveform */}
          <polyline
            fill="none"
            stroke="#FF1744"
            strokeWidth="2"
            strokeLinecap="round"
            points={pointsTwist}
          />
        </svg>
      </div>
    </div>
  );
}
