// High-frequency telemetry waveform chart with limit lines and synchronized playhead (tc.v1).

"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceDot,
  CartesianGrid,
} from "recharts";
import { getSeverityMeta } from "../../lib/severity";
import { formatChainage } from "../../lib/format";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import type { TelemetryPoint, DefectEvent } from "../../lib/types";

export interface TelemetryChartProps {
  data: TelemetryPoint[];
  metricKey?:
    | "vibrationRms"
    | "speedKmh"
    | "trackGaugeMm"
    | "cantMm"
    | "twistMmPerM"
    | "verticalAcceleration"
    | "lateralAcceleration";
  metricLabel?: string;
  unit?: string;
  color?: string;
  currentChainageM?: number;
  safetyThreshold?: number;
  thresholdLabel?: string;
  defects?: DefectEvent[];
  height?: number;
  onSeekChainage?: (chainageM: number) => void;
  className?: string;
}

const METRIC_CONFIGS: Record<
  string,
  { label: string; unit: string; color: string; threshold?: number }
> = {
  vibrationRms: {
    label: "Vertical Vibration RMS",
    unit: "g",
    color: "#38BDF8",
    threshold: 2.2,
  },
  speedKmh: {
    label: "Vehicle Speed",
    unit: "km/h",
    color: "#10B981",
    threshold: 130,
  },
  trackGaugeMm: {
    label: "Track Gauge (Nominal 1435mm)",
    unit: "mm",
    color: "#F59E0B",
    threshold: 1445,
  },
  twistMmPerM: {
    label: "Track Twist",
    unit: "mm/m",
    color: "#F97316",
    threshold: 3.5,
  },
  cantMm: {
    label: "Cant (Superelevation)",
    unit: "mm",
    color: "#A855F7",
    threshold: 80,
  },
  verticalAcceleration: {
    label: "Vertical Acceleration",
    unit: "m/s²",
    color: "#38BDF8",
    threshold: 4.5,
  },
  lateralAcceleration: {
    label: "Lateral Acceleration",
    unit: "m/s²",
    color: "#EC4899",
    threshold: 3.0,
  },
};

function CustomTooltip({ active, payload, unit }: any) {
  if (active && payload && payload.length) {
    const pt = payload[0].payload as TelemetryPoint;
    const value = payload[0].value;
    return (
      <div className="rounded-control border border-scada-border bg-slate-950/95 p-2 font-mono text-[11px] shadow-lg">
        <div className="text-cyan-400 font-bold">
          {formatChainage(pt.chainageM)}
        </div>
        <div className="text-white">
          Value: <strong>{typeof value === "number" ? value.toFixed(2) : value} {unit}</strong>
        </div>
        <div className="text-[10px] text-scada-muted">
          Speed: {pt.speedKmh?.toFixed(1) || 0} km/h
        </div>
      </div>
    );
  }
  return null;
}

export function TelemetryChart({
  data = [],
  metricKey = "vibrationRms",
  metricLabel,
  unit,
  color,
  currentChainageM,
  safetyThreshold,
  thresholdLabel = "IAL Safety Limit",
  defects = [],
  height = 180,
  onSeekChainage,
  className,
}: TelemetryChartProps) {
  const cfg = METRIC_CONFIGS[metricKey] || {
    label: metricKey,
    unit: "",
    color: "#38BDF8",
    threshold: undefined,
  };

  const activeLabel = metricLabel || cfg.label;
  const activeUnit = unit || cfg.unit;
  const activeColor = color || cfg.color;
  const activeThreshold = safetyThreshold !== undefined ? safetyThreshold : cfg.threshold;

  // Protect Recharts SVG DOM against 10k point overload by downsampling to max 500 visual points
  const displayData = React.useMemo(() => {
    if (!data || data.length <= 500) return data || [];
    const step = Math.ceil(data.length / 500);
    const sampled: TelemetryPoint[] = [];
    for (let i = 0; i < data.length; i += step) {
      sampled.push(data[i]);
    }
    if (data.length > 0 && sampled[sampled.length - 1] !== data[data.length - 1]) {
      sampled.push(data[data.length - 1]);
    }
    return sampled;
  }, [data]);

  const handleChartClick = (e: any) => {
    if (e && e.activePayload && e.activePayload.length > 0) {
      const pt = e.activePayload[0].payload as TelemetryPoint;
      if (pt && pt.chainageM !== undefined && onSeekChainage) {
        onSeekChainage(pt.chainageM);
      }
    }
  };

  return (
    <ErrorBoundary fallbackTitle="Waveform Telemetry Offline">
      <div className={className}>
        <div className="flex items-center justify-between mb-2 px-1 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: activeColor }}
            />
            <span className="font-semibold text-white">{activeLabel}</span>
            {activeUnit && (
              <span className="text-scada-muted">({activeUnit})</span>
            )}
          </div>

          {activeThreshold !== undefined && (
            <div className="flex items-center gap-1.5 text-[11px] text-red-400">
              <span className="h-1.5 w-3 border-t border-dashed border-red-400" />
              <span>
                {thresholdLabel}: {activeThreshold} {activeUnit}
              </span>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-scada-border bg-slate-950 p-2 relative">
          <ResponsiveContainer width="100%" height={height}>
            <LineChart
              data={displayData}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              onClick={handleChartClick}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#1E293B"
                vertical={false}
              />
              <XAxis
                dataKey="chainageM"
                stroke="#64748B"
                fontSize={10}
                tickFormatter={(val) => formatChainage(val)}
                fontFamily="monospace"
              />
              <YAxis
                stroke="#64748B"
                fontSize={10}
                fontFamily="monospace"
                domain={["auto", "auto"]}
              />
              <Tooltip content={<CustomTooltip unit={activeUnit} />} />

              {/* Threshold reference line */}
              {activeThreshold !== undefined && (
                <ReferenceLine
                  y={activeThreshold}
                  stroke="#EF4444"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
              )}

              {/* Live Playhead Line */}
              {currentChainageM !== undefined && (
                <ReferenceLine
                  x={currentChainageM}
                  stroke="#00F0FF"
                  strokeWidth={2}
                  label={{
                    value: "PLAYHEAD",
                    position: "insideTopRight",
                    fill: "#00F0FF",
                    fontSize: 9,
                    fontFamily: "monospace",
                  }}
                />
              )}

              {/* Plotted Defects on this chart */}
              {defects.map((d) => {
                const meta = getSeverityMeta(d.severity);
                return (
                  <ReferenceDot
                    key={d.id}
                    x={d.chainageM}
                    y={activeThreshold || 2.0}
                    r={5}
                    fill={meta.hex}
                    stroke="#0F172A"
                    strokeWidth={1.5}
                  />
                );
              })}

              <Line
                type="monotone"
                dataKey={metricKey}
                stroke={activeColor}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </ErrorBoundary>
  );
}
