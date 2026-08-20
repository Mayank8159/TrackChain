// Time-series chart for speed, vibration RMS, roll/pitch vs chainage.

"use client";

import React, { useMemo } from "react";
import type { TelemetryPoint } from "../../lib/types";

interface TelemetryChartProps {
  data: TelemetryPoint[];
  metricKey?: "vibrationRms" | "speedKmh" | "trackGaugeMm" | "cantMm" | "twistMmPerM";
  height?: number;
}

export function TelemetryChart({
  data,
  metricKey = "vibrationRms",
  height = 180,
}: TelemetryChartProps) {
  const metricConfig = {
    vibrationRms: { label: "Vibration RMS", unit: "g", color: "#00F0FF", warn: 1.5, crit: 2.5 },
    speedKmh: { label: "Speed", unit: "km/h", color: "#00E676", warn: 120, crit: 140 },
    trackGaugeMm: { label: "Track Gauge", unit: "mm", color: "#FFB300", warn: 1445, crit: 1450 },
    cantMm: { label: "Cant / Superelevation", unit: "mm", color: "#818CF8", warn: 100, crit: 140 },
    twistMmPerM: { label: "Track Twist", unit: "mm/m", color: "#FF1744", warn: 3.0, crit: 5.0 },
  }[metricKey];

  const points = useMemo(() => {
    if (!data || data.length === 0) return "";
    const values = data.map((d) => Number(d[metricKey] || 0));
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 1;
    const padding = 10;
    const chartHeight = height - padding * 2;
    const width = 600;

    return data
      .map((d, index) => {
        const x = (index / (data.length - 1 || 1)) * width;
        const val = Number(d[metricKey] || 0);
        const y = height - padding - ((val - minVal) / range) * chartHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data, metricKey, height]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs font-mono text-scada-muted">
        <span>{metricConfig.label} ({metricConfig.unit})</span>
        <span className="text-scada-cyan">
          Live ({data.length} pts)
        </span>
      </div>

      <div className="relative w-full rounded border border-scada-border bg-scada-bg/60 p-2 overflow-hidden">
        {data.length > 0 ? (
          <svg
            viewBox={`0 0 600 ${height}`}
            className="w-full h-auto overflow-visible"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id={`grad-${metricKey}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={metricConfig.color} stopOpacity="0.4" />
                <stop offset="100%" stopColor={metricConfig.color} stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid lines */}
            <line x1="0" y1={height / 4} x2="600" y2={height / 4} stroke="#1E293B" strokeDasharray="3 3" />
            <line x1="0" y1={height / 2} x2="600" y2={height / 2} stroke="#1E293B" strokeDasharray="3 3" />
            <line x1="0" y1={(height * 3) / 4} x2="600" y2={(height * 3) / 4} stroke="#1E293B" strokeDasharray="3 3" />

            {/* Polyline */}
            <polyline
              fill="none"
              stroke={metricConfig.color}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          </svg>
        ) : (
          <div className="flex h-32 items-center justify-center text-xs font-mono text-scada-muted">
            Awaiting telemetry data stream...
          </div>
        )}
      </div>
    </div>
  );
}
