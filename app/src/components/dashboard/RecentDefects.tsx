// Recent Defects feed displaying top 5 identified anomalies (tc.v1).

"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, AlertTriangle } from "lucide-react";
import { Card } from "../ui/Card";
import { SeverityBadge } from "../ui/SeverityBadge";
import { useDefects } from "../../hooks/useDefects";
import { formatChainage } from "../../lib/format";

export function RecentDefects() {
  const { defects = [] } = useDefects();
  const recentDefects = defects.slice(0, 5);

  return (
    <Card
      title="Recent Flagged Track Defects"
      badge={
        <span className="badge-cyan text-[10px]">
          {defects.length} TOTAL IN LOG
        </span>
      }
      actions={
        <Link
          href="/defects"
          className="text-[11px] font-mono text-scada-accent hover:underline font-semibold flex items-center gap-1"
        >
          <span>View Defect Registry</span>
          <ArrowRight size={13} />
        </Link>
      }
      className="h-full flex flex-col justify-between"
    >
      <div className="flex-1 overflow-y-auto max-h-80 divide-y divide-scada-border/60">
        {recentDefects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center font-mono">
            <AlertTriangle size={20} className="text-scada-muted mb-2" />
            <p className="text-xs font-bold text-scada-text">
              No Defect Records Found
            </p>
            <p className="text-[11px] text-scada-muted mt-0.5">
              Run an inspection mission to record track telemetry.
            </p>
          </div>
        ) : (
          recentDefects.map((defect) => (
            <div
              key={defect.id}
              className="flex items-center justify-between gap-3 py-3 px-1 transition-colors hover:bg-slate-800/30"
            >
              <div className="flex items-center gap-3 min-w-0">
                <SeverityBadge severity={defect.severity} size="sm" />
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white uppercase truncate">
                      {defect.defectClass.replace("_", " ")}
                    </span>
                    <span className="text-[11px] font-mono text-cyan-400">
                      {formatChainage(defect.chainageM)}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-scada-muted truncate mt-0.5">
                    Source: <span className="uppercase text-slate-400">{defect.streamSource}</span> · Model Confidence:{" "}
                    <span className="text-emerald-400 font-bold">
                      {(defect.confidence * 100).toFixed(0)}%
                    </span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Link
                  href={`/sessions/${defect.sessionId || "ses-delhi-agra-001"}?seek=${defect.videoTimestampSec || 0}`}
                  className="rounded-control bg-slate-800 px-2.5 py-1 text-[10px] font-mono text-scada-text hover:bg-slate-700 hover:text-white border border-scada-border transition-colors"
                >
                  Footage ▶
                </Link>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-scada-border flex items-center justify-between text-[10px] font-mono text-scada-muted">
        <span>Standards: RDSO / EN 13848-1 Track Geometry</span>
        <Link href="/defects" className="text-scada-accent hover:underline">
          All {defects.length} Records →
        </Link>
      </div>
    </Card>
  );
}
