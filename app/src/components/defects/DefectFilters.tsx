// Filter bar: class, severity, date range, session, chainage window.

"use client";

import React from "react";
import { DEFECT_CLASSES } from "../../lib/constants";
import type { FilterState } from "../../lib/types";

interface DefectFiltersProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onReset: () => void;
}

export function DefectFilters({
  filters,
  onChange,
  onReset,
}: DefectFiltersProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-scada-border bg-scada-panel p-3.5 font-mono text-xs">
      <div className="flex flex-wrap items-center gap-3">
        {/* Severity filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-scada-muted">Severity:</span>
          <select
            value={filters.severity || "all"}
            onChange={(e) =>
              onChange({
                ...filters,
                severity: e.target.value === "all" ? undefined : e.target.value,
              })
            }
            className="rounded border border-scada-border bg-scada-bg px-2.5 py-1 text-xs text-scada-text focus:outline-none focus:ring-1 focus:ring-scada-cyan"
          >
            <option value="all">All Tiers</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Defect Class */}
        <div className="flex items-center gap-1.5">
          <span className="text-scada-muted">Class:</span>
          <select
            value={filters.defectClass || "all"}
            onChange={(e) =>
              onChange({
                ...filters,
                defectClass: e.target.value === "all" ? undefined : e.target.value,
              })
            }
            className="rounded border border-scada-border bg-scada-bg px-2.5 py-1 text-xs text-scada-text focus:outline-none focus:ring-1 focus:ring-scada-cyan"
          >
            <option value="all">All Classes</option>
            {DEFECT_CLASSES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Stream Source */}
        <div className="flex items-center gap-1.5">
          <span className="text-scada-muted">Stream:</span>
          <select
            value={filters.streamSource || "all"}
            onChange={(e) =>
              onChange({
                ...filters,
                streamSource: e.target.value === "all" ? undefined : e.target.value,
              })
            }
            className="rounded border border-scada-border bg-scada-bg px-2.5 py-1 text-xs text-scada-text focus:outline-none focus:ring-1 focus:ring-scada-cyan"
          >
            <option value="all">All Streams</option>
            <option value="vision">Vision Only</option>
            <option value="geometry">Geometry Physics</option>
            <option value="fused">Rule Fused</option>
          </select>
        </div>
      </div>

      <button
        onClick={onReset}
        className="text-[11px] text-scada-muted hover:text-scada-cyan underline transition"
      >
        Clear Filters
      </button>
    </div>
  );
}
