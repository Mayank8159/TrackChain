// RDSO Reports & Engineering Data Export workspace (tc.v1).

"use client";

import React, { useState } from "react";
import {
  FileText,
  Download,
  Database,
  Calendar,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles,
  Lock,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { DataError } from "@/components/ui/DataError";
import { useModeStore } from "@/stores/mode-store";
import { useSessions } from "@/hooks/useSessions";
import { useExport } from "@/hooks/useExport";
import { useToast } from "@/components/ui/Toast";

export default function ReportsPage() {
  const { mode } = useModeStore();
  const { data: sessions = [], isError, refetch } = useSessions();
  const { isExporting, exportError, downloadSessionReport } = useExport();
  const { showToast } = useToast();

  const [selectedSessionId, setSelectedSessionId] = useState<string>(
    sessions[0]?.id || "ses-delhi-agra-001"
  );
  const [exportFormat, setExportFormat] = useState<"csv" | "parquet">("csv");
  const [fromDate, setFromDate] = useState<string>("2026-08-01");
  const [toDate, setToDate] = useState<string>("2026-08-21");

  const handleGenerateExport = async () => {
    try {
      const result = await downloadSessionReport(selectedSessionId, exportFormat, {
        from: fromDate,
        to: toDate,
      });

      showToast({
        type: "success",
        title: "Report Exported Successfully",
        description: `Downloaded ${result?.filename || "dataset"} (${exportFormat.toUpperCase()} format).`,
      });
    } catch (err: any) {
      showToast({
        type: "error",
        title: "Export Failed",
        description: err?.message || "Could not compile report dataset.",
      });
    }
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="RDSO Reports & Engineering Data Export"
        description="Standardized telemetry datasets, defect logs, and cryptographic audit trails for railway compliance"
        breadcrumbs={[{ label: "Reports" }]}
        actions={
          <div className="flex items-center gap-2">
            <span className="badge-cyan text-xs">
              RDSO TMD FORMAT v2.4
            </span>
            <span className="badge-green text-xs">
              EN 13848-1 COMPLIANT
            </span>
          </div>
        }
      />

      {/* REAL Mode Backend Offline Error */}
      {mode === "REAL" && isError && (
        <DataError
          title="Engineering Export Service Offline"
          message="Failed to fetch inspection records and schema metrics from the backend. Switch to DEMO mode to test report exports with deterministic data."
          onRetry={() => refetch()}
        />
      )}

      {/* 2. Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Export Configuration Form (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <Card
            title="Export Parameter Configuration"
            badge={
              <span className="badge-cyan text-[10px]">
                STEP 1 & 2
              </span>
            }
          >
            <div className="space-y-5 font-mono text-xs">
              {/* Session Selector */}
              <div className="space-y-1.5">
                <label className="text-scada-muted uppercase font-bold text-[11px] flex items-center justify-between">
                  <span>Target Inspection Run</span>
                  <span className="text-cyan-400">
                    {sessions.length} sessions available
                  </span>
                </label>

                <Select
                  value={selectedSessionId}
                  onChange={(e) => setSelectedSessionId(e.target.value)}
                  disabled={isExporting}
                >
                  {sessions.map((s: any) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id}) — {s.totalDistanceKm}km [{s.defectsCount} defects]
                    </option>
                  ))}
                  <option value="all">Export All Sessions (Consolidated Corridor)</option>
                </Select>
              </div>

              {/* Date Range Selectors */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-scada-muted uppercase font-bold text-[11px] flex items-center gap-1.5">
                    <Calendar size={13} className="text-cyan-400" />
                    <span>From Date (UTC)</span>
                  </label>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    disabled={isExporting}
                    className="w-full rounded-control border border-scada-border bg-slate-900 px-3 py-2 text-xs font-mono text-scada-text focus:border-scada-accent focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-scada-muted uppercase font-bold text-[11px] flex items-center gap-1.5">
                    <Calendar size={13} className="text-cyan-400" />
                    <span>To Date (UTC)</span>
                  </label>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    disabled={isExporting}
                    className="w-full rounded-control border border-scada-border bg-slate-900 px-3 py-2 text-xs font-mono text-scada-text focus:border-scada-accent focus:outline-none"
                  />
                </div>
              </div>

              {/* Export Format Selection */}
              <div className="space-y-2">
                <label className="text-scada-muted uppercase font-bold text-[11px]">
                  Output Format Standard
                </label>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* CSV Option */}
                  <div
                    onClick={() => !isExporting && setExportFormat("csv")}
                    className={`p-3.5 rounded-lg border cursor-pointer transition flex flex-col justify-between ${
                      exportFormat === "csv"
                        ? "bg-slate-800/90 border-cyan-400 shadow-md ring-1 ring-cyan-400/30"
                        : "bg-slate-900/60 border-scada-border hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <FileText size={16} className="text-emerald-400" />
                        <span className="font-bold text-white text-xs">
                          CSV (Spreadsheet)
                        </span>
                      </div>
                      <span className={`h-3 w-3 rounded-full border ${exportFormat === "csv" ? "bg-cyan-400 border-cyan-400" : "border-slate-500"}`} />
                    </div>
                    <p className="text-[10px] text-scada-muted leading-tight">
                      Official RDSO Track Machine Directorate tabular format for Excel & civil audit teams.
                    </p>
                  </div>

                  {/* Parquet Option */}
                  <div
                    onClick={() => !isExporting && setExportFormat("parquet")}
                    className={`p-3.5 rounded-lg border cursor-pointer transition flex flex-col justify-between ${
                      exportFormat === "parquet"
                        ? "bg-slate-800/90 border-cyan-400 shadow-md ring-1 ring-cyan-400/30"
                        : "bg-slate-900/60 border-scada-border hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Database size={16} className="text-cyan-400" />
                        <span className="font-bold text-white text-xs">
                          Apache Parquet
                        </span>
                      </div>
                      <span className={`h-3 w-3 rounded-full border ${exportFormat === "parquet" ? "bg-cyan-400 border-cyan-400" : "border-slate-500"}`} />
                    </div>
                    <p className="text-[10px] text-scada-muted leading-tight">
                      Columnar compressed binary format for high-speed Big Data analytics, PySpark & DuckDB.
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Message Banner */}
              {exportError && (
                <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 p-2.5 rounded-control">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{exportError}</span>
                </div>
              )}

              {/* Action Button */}
              <div className="pt-2">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleGenerateExport}
                  disabled={isExporting}
                  className="w-full font-mono font-bold text-xs"
                >
                  <Download size={15} className={`mr-2 ${isExporting ? "animate-spin" : ""}`} />
                  {isExporting ? "Compiling & Streaming Report..." : "Generate & Export Report"}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column: Schema & RDSO Compliance Card (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <Card
            title="Export Schema & Compliance"
            badge={
              <span className="badge-green text-[10px]">
                RDSO VERIFIED
              </span>
            }
          >
            <div className="space-y-4 font-mono text-xs">
              {/* Compliance Standard Badge */}
              <div className="bg-slate-900/90 p-3 rounded-lg border border-scada-border space-y-1">
                <span className="text-[10px] text-scada-muted uppercase font-bold">
                  Official Standard
                </span>
                <p className="text-white font-bold text-xs">
                  RDSO Track Machine Directorate (TMD) Format v2.4
                </p>
                <p className="text-[10px] text-scada-muted">
                  Indian Railways Permanent Way Engineering Manual (IRPWM)
                </p>
              </div>

              {/* Exported Schema Column Previews */}
              <div className="space-y-2">
                <span className="text-[10px] text-scada-muted uppercase font-bold">
                  Exported Telemetry Data Columns
                </span>

                <div className="bg-slate-950 p-2.5 rounded-lg border border-scada-border/80 space-y-1 text-[11px]">
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">timestamp_utc</span>
                    <span className="text-scada-muted">ISO 8601 UTC</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">chainage_m</span>
                    <span className="text-scada-muted">Meters Float64</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">twist_mm</span>
                    <span className="text-scada-muted">mm/m over 3m</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">gauge_mm</span>
                    <span className="text-scada-muted">mm deviation</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">cant_mm</span>
                    <span className="text-scada-muted">Crosslevel mm</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-cyan-400">vibration_rms</span>
                    <span className="text-scada-muted">Triaxial g RMS</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-cyan-400">speed_kmh</span>
                    <span className="text-scada-muted">Vehicle speed</span>
                  </div>
                </div>
              </div>

              {/* Defect Log Fields */}
              <div className="space-y-2">
                <span className="text-[10px] text-scada-muted uppercase font-bold">
                  Exported Defect Registry Columns
                </span>

                <div className="bg-slate-950 p-2.5 rounded-lg border border-scada-border/80 space-y-1 text-[11px]">
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-emerald-400">defect_id</span>
                    <span className="text-scada-muted">UUID String</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-emerald-400">defect_class</span>
                    <span className="text-scada-muted">Standard Class</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-emerald-400">severity</span>
                    <span className="text-scada-muted">5-Tier Scale</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-emerald-400">confidence_score</span>
                    <span className="text-scada-muted">0.0 - 1.0</span>
                  </div>
                  <div className="flex justify-between border-b border-scada-border/40 pb-1">
                    <span className="text-emerald-400">source_model</span>
                    <span className="text-scada-muted">YOLOv8 / EN13848</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-emerald-400">lat, lon</span>
                    <span className="text-scada-muted">WGS84 EPSG:4326</span>
                  </div>
                </div>
              </div>

              {/* Cryptographic Hash Audit Trail Disclaimer */}
              <div className="flex items-start gap-2 bg-slate-900/60 p-2.5 rounded-lg border border-scada-border text-[10px] text-scada-muted">
                <Lock size={14} className="text-cyan-400 shrink-0 mt-0.5" />
                <p>
                  Data exported via TrackChain is cryptographically hashed with SHA-256 at the edge node. Any post-export tampering will invalidate the audit trail.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
