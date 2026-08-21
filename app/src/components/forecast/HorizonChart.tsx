// Degradation Horizon Chart — Recharts ComposedChart showing historical actuals,
// probabilistic forecast, conformal confidence bands, and RDSO breach markers (tc.oracle.v1).

"use client";

import React, { useMemo } from "react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceDot,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { ForecastPoint } from "../../lib/types";
import type { RDSOLimit } from "../../lib/rdso-thresholds";
import { findBreachDay } from "../../lib/mock-provider";

// ─── Date Formatting ─────────────────────────────────────────────────────────

function formatDay(timestamp: number): string {
  const d = new Date(timestamp);
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
}

function formatFullDate(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

// ─── Custom Glass Tooltip ─────────────────────────────────────────────────────

function GlassTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  const actualItem = payload.find((p: any) => p.dataKey === "tqi_actual");
  const predItem = payload.find((p: any) => p.dataKey === "tqi_predicted");
  const value = actualItem?.value ?? predItem?.value;
  const isHistorical = !!actualItem?.value;

  return (
    <div className="holo-chart-tooltip min-w-[180px]">
      <div className="text-[10px] text-slate-500 mb-1">{label}</div>
      <div className="flex items-center gap-2">
        <span
          className="h-2 w-2 rounded-full shrink-0"
          style={{ backgroundColor: isHistorical ? "#06B6D4" : "#F59E0B" }}
        />
        <span className="text-slate-300 font-mono text-xs">
          TQI: <span className="font-bold text-white">{value != null ? Number(value).toFixed(1) : "—"}</span>
        </span>
      </div>
      {!isHistorical && (
        <div className="text-[10px] text-amber-400/70 mt-0.5 font-mono">
          Forecast ± Conformal Band
        </div>
      )}
    </div>
  );
}

// ─── Legend Renderer ──────────────────────────────────────────────────────────

function HoloLegend() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-4 text-[10px] font-mono text-slate-400 mt-2">
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-5 bg-cyan-400 inline-block rounded" />
        Historical Actual
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="h-0.5 w-5 inline-block rounded"
          style={{ background: "#F59E0B", borderBottom: "2px dashed #F59E0B" }}
        />
        TQI Forecast
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-5 inline-block rounded" style={{ background: "rgba(245,158,11,0.15)" }} />
        80% CI Band
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-5 inline-block rounded" style={{ background: "rgba(245,158,11,0.06)" }} />
        95% CI Band
      </span>
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface HorizonChartProps {
  forecast: ForecastPoint[];
  rdsoLimit: RDSOLimit;
  interventionDay?: number | null; // green line from What-If simulator
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function HorizonChart({
  forecast,
  rdsoLimit,
  interventionDay,
  className,
}: HorizonChartProps) {
  // Build flat chart data — each point has all keys (some undefined = no render)
  const chartData = useMemo(() => {
    return forecast.map((p) => ({
      label: formatDay(p.timestamp),
      timestamp: p.timestamp,
      day: p.day,
      tqi_actual: p.tqi_actual != null ? +p.tqi_actual.toFixed(2) : undefined,
      tqi_predicted: p.tqi_predicted != null ? +p.tqi_predicted.toFixed(2) : undefined,
      upper_95: p.upper_bound_95 != null ? +p.upper_bound_95.toFixed(2) : undefined,
      lower_95: p.lower_bound_95 != null ? +p.lower_bound_95.toFixed(2) : undefined,
      upper_80: p.upper_bound_80 != null ? +p.upper_bound_80.toFixed(2) : undefined,
      lower_80: p.lower_bound_80 != null ? +p.lower_bound_80.toFixed(2) : undefined,
    }));
  }, [forecast]);

  // Find the PREDICTED breach point for the glowing ReferenceDot
  const breachDay = useMemo(
    () => findBreachDay(forecast, rdsoLimit.tqi_critical),
    [forecast, rdsoLimit.tqi_critical]
  );

  const breachPoint = useMemo(() => {
    if (breachDay === null) return null;
    return chartData.find((p) => p.day === breachDay) ?? null;
  }, [chartData, breachDay]);

  // The "today" separator line
  const todayLabel = chartData.find((p) => p.day === 0)?.label ?? "";

  // Tick filter: show every ~15th day label
  const tickIndices = new Set(
    chartData
      .filter((p) => p.day !== undefined && (p.day === -90 || p.day === 0 || p.day % 15 === 0))
      .map((p) => p.label)
  );

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart
          data={chartData}
          margin={{ top: 16, right: 24, left: -8, bottom: 8 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(148,163,184,0.08)"
            vertical={false}
          />

          <XAxis
            dataKey="label"
            tick={{ fill: "#94A3B8", fontFamily: "JetBrains Mono, monospace", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(148,163,184,0.12)" }}
            interval="preserveStartEnd"
            tickFormatter={(v) => (tickIndices.has(v) ? v : "")}
          />

          <YAxis
            domain={[40, 100]}
            tick={{ fill: "#94A3B8", fontFamily: "JetBrains Mono, monospace", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={40}
            tickCount={7}
            label={{
              value: "TQI",
              angle: -90,
              position: "insideLeft",
              offset: 12,
              style: { fill: "#64748B", fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
            }}
          />

          <Tooltip content={<GlassTooltip />} />

          {/* ── 95% Confidence Band ── */}
          <Area
            dataKey="upper_95"
            stroke="none"
            fill="rgba(245,158,11,0.05)"
            connectNulls
            legendType="none"
          />
          <Area
            dataKey="lower_95"
            stroke="none"
            fill="rgba(245,158,11,0.05)"
            connectNulls
            legendType="none"
            fillOpacity={0}
          />

          {/* ── 80% Confidence Band ── */}
          <Area
            dataKey="upper_80"
            stroke="rgba(245,158,11,0.15)"
            strokeWidth={0.5}
            fill="rgba(245,158,11,0.14)"
            connectNulls
            legendType="none"
          />
          <Area
            dataKey="lower_80"
            stroke="rgba(245,158,11,0.15)"
            strokeWidth={0.5}
            fill="rgba(245,158,11,0.14)"
            connectNulls
            legendType="none"
            fillOpacity={0}
          />

          {/* ── Historical Actual Line ── */}
          <Line
            type="monotone"
            dataKey="tqi_actual"
            stroke="#06B6D4"
            strokeWidth={2}
            dot={false}
            connectNulls
            legendType="none"
          />

          {/* ── Forecast Prediction Line ── */}
          <Line
            type="monotone"
            dataKey="tqi_predicted"
            stroke="#F59E0B"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            connectNulls
            legendType="none"
          />

          {/* ── RDSO Critical Limit ── */}
          <ReferenceLine
            y={rdsoLimit.tqi_critical}
            stroke="#EF4444"
            strokeDasharray="4 3"
            strokeWidth={1.5}
            label={{
              value: `RDSO Limit (${rdsoLimit.tqi_critical})`,
              position: "right",
              style: {
                fill: "#EF4444",
                fontSize: 9,
                fontFamily: "JetBrains Mono, monospace",
              },
            }}
          />

          {/* ── RDSO Warning Level ── */}
          <ReferenceLine
            y={rdsoLimit.tqi_warning}
            stroke="#F97316"
            strokeDasharray="3 4"
            strokeWidth={1}
            label={{
              value: `Warning (${rdsoLimit.tqi_warning})`,
              position: "right",
              style: {
                fill: "#F97316",
                fontSize: 9,
                fontFamily: "JetBrains Mono, monospace",
              },
            }}
          />

          {/* ── "Today" Divider ── */}
          <ReferenceLine
            x={todayLabel}
            stroke="rgba(148,163,184,0.3)"
            strokeDasharray="2 4"
            strokeWidth={1.5}
            label={{
              value: "TODAY",
              position: "top",
              style: {
                fill: "#94A3B8",
                fontSize: 9,
                fontFamily: "JetBrains Mono, monospace",
              },
            }}
          />

          {/* ── Simulated Maintenance Line ── */}
          {interventionDay !== null && interventionDay !== undefined && (() => {
            const iv = chartData.find((p) => p.day === interventionDay);
            if (!iv) return null;
            return (
              <ReferenceLine
                x={iv.label}
                stroke="#10B981"
                strokeWidth={2}
                strokeDasharray="5 3"
                label={{
                  value: "🔧 Maintenance",
                  position: "top",
                  style: {
                    fill: "#10B981",
                    fontSize: 9,
                    fontFamily: "JetBrains Mono, monospace",
                  },
                }}
              />
            );
          })()}

          {/* ── Predicted Breach Marker ── */}
          {breachPoint && (
            <ReferenceDot
              x={breachPoint.label}
              y={breachPoint.tqi_predicted ?? rdsoLimit.tqi_critical}
              r={6}
              fill="#EF4444"
              stroke="#FCA5A5"
              strokeWidth={2}
              label={{
                value: `⚠ Breach: ${breachPoint.label}`,
                position: "top",
                style: {
                  fill: "#EF4444",
                  fontSize: 10,
                  fontFamily: "JetBrains Mono, monospace",
                  fontWeight: "bold",
                },
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      <HoloLegend />
    </div>
  );
}
