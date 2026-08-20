// Donut/bar chart of defect counts by severity.

"use client";

import React from "react";
import type { DefectEvent, SeverityLevel } from "../../lib/types";
import { SEVERITY_CONFIG } from "../../lib/constants";

interface SeverityDistributionProps {
  defects: DefectEvent[];
}

export function SeverityDistribution({ defects }: SeverityDistributionProps) {
  const counts: Record<SeverityLevel, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    normal: 0,
  };

  defects.forEach((d) => {
    if (counts[d.severity] !== undefined) {
      counts[d.severity]++;
    }
  });

  const total = defects.length || 1;

  return (
    <div className="flex flex-col gap-3 font-mono">
      <div className="flex items-center justify-between text-xs text-scada-muted">
        <span>Defect Severity Breakdown</span>
        <span className="text-scada-cyan font-bold">{defects.length} total events</span>
      </div>

      <div className="space-y-2">
        {(["critical", "high", "medium", "low"] as SeverityLevel[]).map((lvl) => {
          const count = counts[lvl];
          const pct = Math.round((count / total) * 100);
          const cfg = SEVERITY_CONFIG[lvl];

          return (
            <div key={lvl} className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="capitalize text-scada-muted">{cfg.label}</span>
                <span className="font-bold text-scada-text">
                  {count} <span className="text-scada-muted font-normal">({pct}%)</span>
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-scada-panel border border-scada-border">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: cfg.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
