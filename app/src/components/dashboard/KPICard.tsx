// Holographic SCADA KPI Metric Card — glass surface + holo-sheen sweep (tc.holo.v1).

import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { getSeverityMeta } from "../../lib/severity";
import { cn } from "../../lib/utils";

export interface KPICardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  trend?: number;
  trendLabel?: string;
  severity?: string;
  pulse?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  icon,
  subtitle,
  trend,
  trendLabel = "vs last run",
  severity,
  pulse = false,
  className,
}: KPICardProps) {
  const meta = severity ? getSeverityMeta(severity) : null;

  return (
    <div
      className={cn(
        "relative pl-4 border-l-2 border-cyan-500/40 py-2.5 group overflow-hidden transition-all hover:border-cyan-400",
        pulse && "border-red-500/80 shadow-[0_0_25px_rgba(239,68,68,0.25)]",
        className
      )}
    >
      {/* Ghost Number Background */}
      <span className="ghost-number select-none pointer-events-none">{value}</span>

      {/* Actual Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-[11px] font-mono uppercase tracking-widest text-slate-400 font-bold">
            {title}
          </span>
          <div
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-control border p-1 transition-all",
              meta
                ? `${meta.bgClass} ${meta.borderClass} ${meta.textClass}`
                : "bg-white/5 border-white/10 text-slate-300"
            )}
            style={meta ? { boxShadow: `0 0 10px ${meta.hex}30` } : undefined}
          >
            {icon}
          </div>
        </div>

        <div className="flex items-baseline gap-2">
          <h3 className="text-3xl font-bold font-mono tracking-tight tabular-nums text-white">
            {value}
          </h3>
          {subtitle && <span className="text-xs font-mono font-medium text-slate-400">{subtitle}</span>}
        </div>

        {trend !== undefined && (
          <div className="mt-1.5 flex items-center gap-1 font-mono text-[11px]">
            <div
              className={cn(
                "flex items-center gap-1 font-semibold",
                trend > 0 ? "text-red-400" : "text-emerald-400"
              )}
            >
              {trend > 0 ? (
                <TrendingUp size={13} strokeWidth={1.5} className="shrink-0" />
              ) : (
                <TrendingDown size={13} strokeWidth={1.5} className="shrink-0" />
              )}
              <span>
                {trend > 0 ? `+${trend}%` : `${trend}%`} {trendLabel}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

