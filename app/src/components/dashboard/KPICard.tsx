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
        // Holographic glass surface + sweep sheen on hover
        "glass-card holo-sheen relative flex flex-col justify-between p-4 transition-all",
        pulse && "shadow-[0_0_20px_rgba(239,68,68,0.20)] border-red-500/30",
        className
      )}
    >
      {/* Header: Title + Icon */}
      <div className="flex items-start justify-between gap-3">
        <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400">
          {title}
        </span>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-control border p-1.5 transition-all",
            meta
              ? `${meta.bgClass} ${meta.borderClass} ${meta.textClass}`
              : "bg-white/5 border-white/10 text-slate-300"
          )}
          style={meta ? { boxShadow: `0 0 10px ${meta.hex}30` } : undefined}
        >
          {icon}
        </div>
      </div>

      {/* Main Metric Value */}
      <div className="mt-3">
        <div className="text-3xl font-bold font-mono tracking-tight tabular-nums text-white">
          {value}
        </div>

        {/* Footer: Trend / Subtitle */}
        <div className="mt-1 flex items-center justify-between text-[11px] font-mono text-slate-500">
          {subtitle && <span>{subtitle}</span>}

          {trend !== undefined && (
            <div
              className={cn(
                "flex items-center gap-1 font-semibold ml-auto",
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
          )}
        </div>
      </div>
    </div>
  );
}

