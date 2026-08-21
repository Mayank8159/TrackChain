// Reusable high-density SCADA KPI Metric Card for Operational Dashboard (tc.v1).

import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { getSeverityMeta } from "../../lib/severity";
import { cn } from "../../lib/utils";

export interface KPICardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  trend?: number; // e.g. +4.2 or -1.5
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
        "scada-card relative flex flex-col justify-between p-4 border border-scada-border bg-slate-900/90 transition-all hover:border-slate-600",
        pulse && "border-red-500/50 shadow-lg shadow-red-500/10 animate-pulse",
        className
      )}
    >
      {/* Header: Title + Icon */}
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-scada-muted">
          {title}
        </span>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-control border p-1.5",
            meta
              ? `${meta.bgClass} ${meta.borderClass} ${meta.textClass}`
              : "bg-slate-800/80 border-slate-700 text-scada-text"
          )}
        >
          {icon}
        </div>
      </div>

      {/* Main Metric Value */}
      <div className="mt-3">
        <div className="text-3xl font-bold font-mono tracking-tight text-white">
          {value}
        </div>

        {/* Footer: Trend / Subtitle */}
        <div className="mt-1 flex items-center justify-between text-[11px] font-mono text-scada-muted">
          {subtitle && <span>{subtitle}</span>}

          {trend !== undefined && (
            <div
              className={cn(
                "flex items-center gap-1 font-semibold ml-auto",
                trend > 0
                  ? "text-red-400" // In defect tracking, positive trend often means more defects
                  : "text-emerald-400"
              )}
            >
              {trend > 0 ? (
                <TrendingUp size={13} className="shrink-0" />
              ) : (
                <TrendingDown size={13} className="shrink-0" />
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
