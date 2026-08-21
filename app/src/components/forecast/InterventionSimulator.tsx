// What-If Intervention Simulator — interactive slider that recalculates
// the TQI degradation curve after a simulated tamping/restoration event (tc.oracle.v1).

"use client";

import React, { useMemo } from "react";
import { Wrench, TrendingUp, CalendarClock } from "lucide-react";
import type { ForecastPoint } from "../../lib/types";
import { findBreachDay } from "../../lib/mock-provider";
import { cn } from "../../lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

/** TQI points gained immediately after tamping/restoration. */
const TAMPING_RECOVERY_TQI = 25;

/** Band narrowing factor right after intervention (simulates fresh inspection certainty). */
const POST_INTERVENTION_CERTAINTY = 0.3;

// ─── Logic ────────────────────────────────────────────────────────────────────

/**
 * Clone the forecast and inject a maintenance event at interventionDay.
 * For all days > interventionDay: shift tqi_predicted up by recovery, narrow bands initially.
 */
export function applyIntervention(
  forecast: ForecastPoint[],
  interventionDay: number
): ForecastPoint[] {
  return forecast.map((p) => {
    if ((p.day ?? 0) <= interventionDay || p.tqi_predicted === undefined) {
      return p; // Historical or pre-intervention — unchanged
    }

    const daysAfterEvent = (p.day ?? 0) - interventionDay;
    const recoveryCurve = TAMPING_RECOVERY_TQI * Math.exp(-daysAfterEvent / 120);
    const newPredicted = Math.min(100, (p.tqi_predicted ?? 0) + recoveryCurve);

    // Bands re-narrow after intervention, then widen again with epistemic uncertainty
    const tightenFactor = POST_INTERVENTION_CERTAINTY + (1 - POST_INTERVENTION_CERTAINTY) *
      Math.min(1, daysAfterEvent / 45);

    const sigma = 1.4 * Math.sqrt(daysAfterEvent + 1) * tightenFactor;

    return {
      ...p,
      tqi_predicted: Math.round(newPredicted * 100) / 100,
      upper_bound_95: Math.min(100, newPredicted + 1.96 * sigma),
      lower_bound_95: Math.max(20, newPredicted - 1.96 * sigma),
      upper_bound_80: Math.min(100, newPredicted + 1.28 * sigma),
      lower_bound_80: Math.max(20, newPredicted - 1.28 * sigma),
    };
  });
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface InterventionSimulatorProps {
  baseForecast: ForecastPoint[];
  thresholdTqi: number;
  interventionDay: number;          // currently selected slider day (1–85)
  onInterventionChange: (day: number) => void;
  isActive: boolean;                // when false, show "activate" prompt
  onToggle: () => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function InterventionSimulator({
  baseForecast,
  thresholdTqi,
  interventionDay,
  onInterventionChange,
  isActive,
  onToggle,
  className,
}: InterventionSimulatorProps) {
  // Original breach day (no intervention)
  const originalBreachDay = useMemo(
    () => findBreachDay(baseForecast, thresholdTqi),
    [baseForecast, thresholdTqi]
  );

  // Breach day after intervention
  const simulatedForecast = useMemo(
    () => isActive ? applyIntervention(baseForecast, interventionDay) : baseForecast,
    [baseForecast, interventionDay, isActive]
  );

  const newBreachDay = useMemo(
    () => isActive ? findBreachDay(simulatedForecast, thresholdTqi) : originalBreachDay,
    [simulatedForecast, thresholdTqi, isActive, originalBreachDay]
  );

  const daysGained =
    originalBreachDay !== null && newBreachDay !== null
      ? newBreachDay - originalBreachDay
      : originalBreachDay !== null && newBreachDay === null
      ? 90 - originalBreachDay
      : null;

  const interventionDateLabel = useMemo(() => {
    const pt = baseForecast.find((p) => p.day === interventionDay);
    if (!pt) return `Day +${interventionDay}`;
    return new Date(pt.timestamp).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
    });
  }, [baseForecast, interventionDay]);

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench
            size={14}
            strokeWidth={1.5}
            className={isActive ? "text-emerald-400" : "text-slate-500"}
          />
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300">
            What-If Simulator
          </span>
        </div>
        <button
          onClick={onToggle}
          className={cn(
            "px-2.5 py-1 rounded-control text-[10px] font-mono font-bold uppercase tracking-wider transition-all border",
            isActive
              ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/40 hover:bg-emerald-500/25"
              : "bg-white/5 text-slate-500 border-white/10 hover:border-cyan-500/40 hover:text-slate-300"
          )}
        >
          {isActive ? "✓ Active" : "Activate"}
        </button>
      </div>

      {!isActive ? (
        <div className="text-[11px] font-mono text-slate-500 bg-white/[0.02] rounded-control px-3 py-3 border border-white/[0.05]">
          Enable the simulator to drag a maintenance event on the chart and
          observe how a tamping/restoration shifts the breach prediction.
        </div>
      ) : (
        <>
          {/* Slider */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
              <span>Day +1</span>
              <span className="text-cyan-400 font-bold">
                Dispatch: {interventionDateLabel} (Day +{interventionDay})
              </span>
              <span>Day +85</span>
            </div>
            <input
              type="range"
              min={1}
              max={85}
              step={1}
              value={interventionDay}
              onChange={(e) => onInterventionChange(Number(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer
                bg-gradient-to-r from-emerald-500/40 to-slate-700
                [&::-webkit-slider-thumb]:appearance-none
                [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:w-4
                [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-emerald-400
                [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(52,211,153,0.6)]
                [&::-webkit-slider-thumb]:border
                [&::-webkit-slider-thumb]:border-emerald-300/50
                [&::-webkit-slider-thumb]:cursor-grab"
              aria-label="Intervention day selector"
            />
          </div>

          {/* Result Cards */}
          <div className="grid grid-cols-2 gap-3">
            {/* Original breach */}
            <div className="flex flex-col gap-1 rounded-control bg-red-500/[0.06] border border-red-500/20 px-3 py-2.5">
              <span className="text-[9px] font-mono uppercase tracking-widest text-red-400/70">
                Without Maintenance
              </span>
              <span className="text-sm font-mono font-bold text-red-400">
                {originalBreachDay !== null ? `Day +${originalBreachDay}` : "No breach"}
              </span>
            </div>

            {/* New breach */}
            <div className="flex flex-col gap-1 rounded-control bg-emerald-500/[0.06] border border-emerald-500/20 px-3 py-2.5">
              <span className="text-[9px] font-mono uppercase tracking-widest text-emerald-400/70">
                After Maintenance
              </span>
              <span className="text-sm font-mono font-bold text-emerald-400">
                {newBreachDay !== null ? `Day +${newBreachDay}` : "No breach ✓"}
              </span>
            </div>
          </div>

          {/* Delta Badge */}
          {daysGained !== null && daysGained > 0 && (
            <div className="flex items-center gap-2 rounded-control bg-cyan-500/[0.08] border border-cyan-500/25 px-3 py-2">
              <TrendingUp size={13} strokeWidth={1.5} className="text-cyan-400 shrink-0" />
              <span className="text-xs font-mono text-cyan-300 font-bold">
                +{daysGained} Days to Failure
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                through simulated tamping at {interventionDateLabel}
              </span>
            </div>
          )}
          {daysGained !== null && daysGained <= 0 && (
            <div className="flex items-center gap-2 rounded-control bg-amber-500/[0.08] border border-amber-500/25 px-3 py-2">
              <CalendarClock size={13} strokeWidth={1.5} className="text-amber-400 shrink-0" />
              <span className="text-xs font-mono text-amber-300">
                Intervention too late — schedule earlier for meaningful TQI recovery.
              </span>
            </div>
          )}
          {newBreachDay === null && originalBreachDay !== null && (
            <div className="flex items-center gap-2 rounded-control bg-emerald-500/[0.08] border border-emerald-500/25 px-3 py-2">
              <TrendingUp size={13} strokeWidth={1.5} className="text-emerald-400 shrink-0" />
              <span className="text-xs font-mono text-emerald-300 font-bold">
                Breach eliminated within 90-day window 🎯
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
