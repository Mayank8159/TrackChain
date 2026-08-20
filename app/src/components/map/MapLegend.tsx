// Legend explaining marker colors and severity levels.

import React from "react";
import { SEVERITY_CONFIG } from "../../lib/constants";
import type { SeverityLevel } from "../../lib/types";

export function MapLegend() {
  const levels: SeverityLevel[] = ["critical", "high", "medium", "low", "normal"];

  return (
    <div className="rounded-lg border border-scada-border bg-scada-panel/95 p-3 text-xs font-mono backdrop-blur shadow-xl">
      <div className="font-bold text-[11px] uppercase tracking-wider text-scada-text mb-2 border-b border-scada-border pb-1">
        Map Symbology & Fault Tiers
      </div>
      <div className="flex flex-col gap-1.5">
        {levels.map((lvl) => {
          const cfg = SEVERITY_CONFIG[lvl];
          return (
            <div key={lvl} className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: cfg.color }}
              />
              <span className="text-[10px] text-scada-muted capitalize">
                {cfg.label} Defect
              </span>
            </div>
          );
        })}
        <div className="flex items-center gap-2 pt-1 border-t border-scada-border/60 mt-1">
          <span className="h-1.5 w-4 bg-scada-cyan rounded" />
          <span className="text-[10px] text-scada-muted">Track Corridor Polyline</span>
        </div>
      </div>
    </div>
  );
}
