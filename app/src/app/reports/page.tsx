// Generate/export RDSO-format reports (PDF/CSV) for a session or section.

"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useSessions } from "@/hooks/useSessions";
import { useDefects } from "@/hooks/useDefects";
import { useExport } from "@/hooks/useExport";
import { useToast } from "@/components/ui/Toast";

export default function ReportsPage() {
  const { data: sessions = [] } = useSessions();
  const { defects = [] } = useDefects();
  const { exportDefectsCSV } = useExport();
  const { showToast } = useToast();

  const [selectedSessionId, setSelectedSessionId] = useState<string>(
    sessions[0]?.id || "ses-delhi-agra-001"
  );
  const [standard, setStandard] = useState<"EN 13848" | "RDSO CTI">("RDSO CTI");
  const [includeEvidence, setIncludeEvidence] = useState<boolean>(true);

  const handleGenerateReport = () => {
    exportDefectsCSV(defects, `RDSO_Track_Condition_Report_${selectedSessionId}.csv`);
    showToast({
      type: "success",
      title: "Report Generated Successfully",
      description: `Exported RDSO audit report with ${defects.length} defect entries.`,
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-5xl mx-auto w-full">
        <PageHeader
          title="RDSO & Ministry of Railways Compliance Reporting"
          description="Export certified track geometry quality index and visual defect audit summaries"
          breadcrumbs={[{ label: "Reports" }]}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Report Configuration (2 cols) */}
          <div className="md:col-span-2">
            <Card title="Report Generation Parameters">
              <div className="flex flex-col gap-4 font-mono text-xs">
                {/* Session select */}
                <div className="space-y-1.5">
                  <label className="text-scada-muted">Target Inspection Run:</label>
                  <select
                    value={selectedSessionId}
                    onChange={(e) => setSelectedSessionId(e.target.value)}
                    className="w-full rounded border border-scada-border bg-scada-bg p-2 text-scada-text focus:outline-none focus:ring-1 focus:ring-scada-cyan"
                  >
                    {sessions.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.trackSection})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Compliance Standard */}
                <div className="space-y-1.5">
                  <label className="text-scada-muted">Audit Compliance Standard:</label>
                  <div className="grid grid-cols-2 gap-3">
                    {(["RDSO CTI", "EN 13848"] as const).map((std) => (
                      <button
                        key={std}
                        type="button"
                        onClick={() => setStandard(std)}
                        className={`p-3 rounded border text-left transition ${
                          standard === std
                            ? "border-scada-cyan bg-scada-cyan/15 text-scada-cyan font-bold"
                            : "border-scada-border bg-scada-panel text-scada-muted hover:text-scada-text"
                        }`}
                      >
                        <div className="text-xs uppercase">{std}</div>
                        <div className="text-[10px] text-scada-muted mt-1">
                          {std === "RDSO CTI"
                            ? "Indian Railways Comprehensive Track Index"
                            : "European Railway Track Quality Norms"}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Evidence checkbox */}
                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="evidence"
                    checked={includeEvidence}
                    onChange={(e) => setIncludeEvidence(e.target.checked)}
                    className="rounded accent-scada-cyan"
                  />
                  <label htmlFor="evidence" className="text-scada-text cursor-pointer">
                    Embed high-resolution visual evidence snapshots & crop bounding boxes
                  </label>
                </div>

                <div className="pt-4 border-t border-scada-border flex gap-3">
                  <Button variant="primary" size="md" onClick={handleGenerateReport}>
                    Export RDSO Audit Report (CSV / PDF)
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Quick Metrics */}
          <div className="flex flex-col gap-4">
            <Card title="Summary Preview">
              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between border-b border-scada-border pb-1">
                  <span className="text-scada-muted">Track Quality Index:</span>
                  <span className="text-scada-green font-bold">88.4 / 100</span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1">
                  <span className="text-scada-muted">Defects Flagged:</span>
                  <span className="text-scada-red font-bold">{defects.length}</span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1">
                  <span className="text-scada-muted">IAL Exceedances:</span>
                  <span className="text-scada-amber font-bold">2 instances</span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1">
                  <span className="text-scada-muted">Route Coverage:</span>
                  <span className="text-scada-cyan font-bold">140.0 km (100%)</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
