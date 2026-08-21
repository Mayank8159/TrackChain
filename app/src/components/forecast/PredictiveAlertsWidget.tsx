// PredictiveAlertsWidget — Dashboard panel showing top 3 at-risk segments with breach countdowns.
// Pulls from the Oracle MOCK_TRACK_SEGMENTS and RDSO thresholds (tc.oracle.v1).

"use client";

import React from "react";
import Link from "next/link";
import { BrainCircuit, AlertTriangle, ArrowRight, ShieldCheck } from "lucide-react";
import { Card } from "../ui/Card";
import { MOCK_TRACK_SEGMENTS, findBreachDay } from "../../lib/mock-provider";
import { RDSO_LIMITS } from "../../lib/rdso-thresholds";

export function PredictiveAlertsWidget() {
  // Compute breach days and sort by urgency
  const ranked = MOCK_TRACK_SEGMENTS
    .map((seg) => {
      const limit = RDSO_LIMITS[seg.trackClass];
      const breachDay = findBreachDay(seg.forecast, limit.tqi_critical);
      const survival30 = seg.survivalProbs.find((s) => s.horizon_days === 30)?.probability ?? 1;
      return { seg, limit, breachDay, survival30 };
    })
    .sort((a, b) => {
      // Sort: imminent first (smaller breachDay), then null (no breach) last
      if (a.breachDay === null && b.breachDay === null) return 0;
      if (a.breachDay === null) return 1;
      if (b.breachDay === null) return -1;
      return a.breachDay - b.breachDay;
    })
    .slice(0, 3);

  return (
    <Card
      title="Predictive Intelligence"
      badge={
        <span className="badge-violet text-[9px] font-mono font-bold uppercase tracking-wider">
          Oracle Engine
        </span>
      }
      actions={
        <Link
          href="/forecast"
          className="flex items-center gap-1 text-[10px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          Full Forecast <ArrowRight size={11} strokeWidth={1.5} />
        </Link>
      }
    >
      <div className="flex flex-col gap-2">
        {ranked.map(({ seg, breachDay, survival30 }) => {
          const isImminent = breachDay !== null && breachDay <= 14;
          const isCaution = breachDay !== null && breachDay <= 45 && breachDay > 14;
          const isSafe = breachDay === null || breachDay > 45;

          const statusColor = isImminent
            ? "border-red-500/30 bg-red-500/[0.05]"
            : isCaution
            ? "border-amber-500/30 bg-amber-500/[0.05]"
            : "border-white/[0.05] bg-white/[0.02]";

          const Icon = isImminent ? AlertTriangle : isCaution ? AlertTriangle : ShieldCheck;
          const iconClass = isImminent
            ? "text-red-400"
            : isCaution
            ? "text-amber-400"
            : "text-emerald-400";

          const breachLabel = breachDay !== null
            ? `Breach in ${breachDay} day${breachDay !== 1 ? "s" : ""}`
            : "No breach predicted";

          const probLabel = `${Math.round(survival30 * 100)}% 30-day survival`;

          return (
            <Link
              href="/forecast"
              key={seg.id}
              className={`flex items-center justify-between gap-3 px-3 py-3 rounded-control border transition-all hover:border-cyan-500/25 ${statusColor}`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon size={14} strokeWidth={1.5} className={`${iconClass} shrink-0`} />
                <div className="min-w-0">
                  <div className="text-xs font-mono font-bold text-slate-200 truncate">
                    {seg.label}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">
                    TQI {seg.currentTqi.toFixed(1)} · {seg.trackClass.replace("_", " ")}
                  </div>
                </div>
              </div>

              <div className="text-right shrink-0">
                <div
                  className={`text-xs font-mono font-bold ${
                    isImminent
                      ? "text-red-400"
                      : isCaution
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {breachLabel}
                </div>
                <div className="text-[10px] font-mono text-slate-500">{probLabel}</div>
              </div>
            </Link>
          );
        })}

        {/* Footer link */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.04]">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
            <BrainCircuit size={11} strokeWidth={1.5} className="text-violet-400" />
            Conformal prediction intervals · RDSO C-7012
          </div>
          <Link
            href="/forecast"
            className="flex items-center gap-1 text-[10px] font-mono text-violet-400 hover:text-violet-300 transition-colors"
          >
            Open Oracle <ArrowRight size={11} strokeWidth={1.5} />
          </Link>
        </div>
      </div>
    </Card>
  );
}
