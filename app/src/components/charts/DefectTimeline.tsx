// Defect counts per km section and severity distribution.

"use client";

import React from "react";
import type { DefectEvent } from "../../lib/types";

interface DefectTimelineProps {
  defects: DefectEvent[];
  maxChainageKm?: number;
}

export function DefectTimeline({
  defects,
  maxChainageKm = 25,
}: DefectTimelineProps) {
  // Group defects into 1 km buckets
  const buckets = Array.from({ length: maxChainageKm }, (_, i) => ({
    km: i + 1,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  }));

  defects.forEach((d) => {
    const kmIndex = Math.min(
      Math.floor(d.chainageM / 1000),
      maxChainageKm - 1
    );
    if (kmIndex >= 0 && kmIndex < maxChainageKm) {
      if (d.severity === "critical") buckets[kmIndex].critical++;
      else if (d.severity === "high") buckets[kmIndex].high++;
      else if (d.severity === "medium") buckets[kmIndex].medium++;
      else buckets[kmIndex].low++;
    }
  });

  const maxCount = Math.max(
    ...buckets.map((b) => b.critical + b.high + b.medium + b.low),
    5
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs font-mono text-scada-muted">
        <span>Defect Density by Chainage (km 1 to {maxChainageKm})</span>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-scada-red" /> Crit</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-scada-amber" /> High</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-scada-cyan" /> Low</span>
        </div>
      </div>

      <div className="flex items-end gap-1 h-28 rounded border border-scada-border bg-scada-bg/60 p-2">
        {buckets.map((b) => {
          const total = b.critical + b.high + b.medium + b.low;
          const critPct = (b.critical / maxCount) * 100;
          const highPct = (b.high / maxCount) * 100;
          const lowPct = ((b.medium + b.low) / maxCount) * 100;

          return (
            <div
              key={b.km}
              className="group relative flex flex-1 flex-col justify-end h-full cursor-pointer hover:bg-scada-panel/80 rounded-t"
            >
              {total > 0 && (
                <div className="w-full flex flex-col justify-end rounded-t overflow-hidden">
                  {b.critical > 0 && (
                    <div
                      style={{ height: `${critPct}%` }}
                      className="w-full bg-scada-red min-h-[4px]"
                    />
                  )}
                  {b.high > 0 && (
                    <div
                      style={{ height: `${highPct}%` }}
                      className="w-full bg-scada-amber min-h-[3px]"
                    />
                  )}
                  {(b.medium > 0 || b.low > 0) && (
                    <div
                      style={{ height: `${lowPct}%` }}
                      className="w-full bg-scada-cyan min-h-[2px]"
                    />
                  )}
                </div>
              )}
              <span className="mt-1 text-[9px] font-mono text-center text-scada-muted group-hover:text-scada-cyan">
                {b.km}k
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
