// Map Legend component showing 5-tier severity and TQI track quality bands (tc.v1).

import React from "react";
import { SEVERITY_CONFIG, CanonicalSeverity } from "../../lib/severity";

export function MapLegend() {
  const severityKeys: CanonicalSeverity[] = ["critical", "high", "medium", "low", "ok"];

  return (
    <div className="rounded-control border border-scada-border bg-slate-950/90 p-3 font-mono text-[11px] text-scada-text shadow-2xl backdrop-blur max-w-xs select-none">
      <div className="font-bold text-white uppercase tracking-wider mb-2 border-b border-scada-border/60 pb-1">
        Corridor GIS Legend
      </div>

      {/* 1. Track Quality Index (TQI) Segments */}
      <div className="mb-2.5 space-y-1">
        <span className="text-[10px] text-scada-muted uppercase font-semibold">
          Track Quality Index (TQI)
        </span>
        <div className="grid grid-cols-3 gap-1.5 pt-0.5">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-4 rounded-sm bg-emerald-500 shrink-0" />
            <span className="text-[10px] text-slate-300">&gt; 85 OK</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-4 rounded-sm bg-amber-500 shrink-0" />
            <span className="text-[10px] text-slate-300">70-85 Warn</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-4 rounded-sm bg-red-500 shrink-0" />
            <span className="text-[10px] text-slate-300">&lt; 70 IAL</span>
          </div>
        </div>
      </div>

      {/* 2. Defect Anomaly Markers */}
      <div className="space-y-1">
        <span className="text-[10px] text-scada-muted uppercase font-semibold">
          Defect Severity Pin
        </span>
        <div className="grid grid-cols-2 gap-1.5 pt-0.5">
          {severityKeys.map((key) => {
            const meta = SEVERITY_CONFIG[key];
            return (
              <div key={key} className="flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full border border-white/80 shrink-0"
                  style={{ backgroundColor: meta.hex }}
                />
                <span className="text-[10px] text-slate-300">{meta.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
