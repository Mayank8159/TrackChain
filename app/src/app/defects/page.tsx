// Defects table + filters; links each defect to evidence image and video offset.

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Card } from "@/components/ui/Card";
import { StatBadge } from "@/components/ui/StatBadge";
import { DefectTimeline } from "@/components/charts/DefectTimeline";
import type { DefectEvent, SeverityLevel, DefectClass } from "@/lib/types";

const INITIAL_DEFECTS: DefectEvent[] = [
  {
    id: "DEF-001",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:15:32Z",
    chainageM: 3420,
    defectClass: "crack",
    severity: "critical",
    confidence: 0.94,
    streamSource: "vision",
    videoTimestampSec: 142.5,
    description: "Transverse rail head crack on right rail running surface",
    status: "open",
    coordinates: { lat: 28.592, lng: 77.248 },
  },
  {
    id: "DEF-002",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:18:10Z",
    chainageM: 7850,
    defectClass: "gauge_widening",
    severity: "high",
    confidence: 0.89,
    streamSource: "geometry",
    videoTimestampSec: 320.0,
    description: "Track gauge measured at 1448mm (+13mm above standard 1435mm)",
    status: "open",
    coordinates: { lat: 28.561, lng: 77.265 },
  },
  {
    id: "DEF-003",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:22:45Z",
    chainageM: 12100,
    defectClass: "missing_fastener",
    severity: "medium",
    confidence: 0.96,
    streamSource: "vision",
    videoTimestampSec: 495.2,
    description: "Missing Pandrol clip fastener on sleeper #482",
    status: "acknowledged",
    coordinates: { lat: 28.528, lng: 77.289 },
  },
  {
    id: "DEF-004",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:26:12Z",
    chainageM: 16400,
    defectClass: "spalling",
    severity: "high",
    confidence: 0.88,
    streamSource: "fused",
    videoTimestampSec: 670.8,
    description: "Surface spalling with localized high-frequency vertical acceleration",
    status: "open",
    coordinates: { lat: 28.495, lng: 77.302 },
  },
  {
    id: "DEF-005",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:31:05Z",
    chainageM: 21950,
    defectClass: "twist_exceedance",
    severity: "critical",
    confidence: 0.92,
    streamSource: "geometry",
    videoTimestampSec: 890.4,
    description: "EN 13848-1 track twist rate exceeded: 4.2mm/m over 3m base",
    status: "open",
    coordinates: { lat: 28.452, lng: 77.319 },
  },
];

export default function DefectsPage() {
  const [defects] = useState<DefectEvent[]>(INITIAL_DEFECTS);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(
    INITIAL_DEFECTS[0]
  );

  const filteredDefects = defects.filter((d) => {
    if (severityFilter !== "all" && d.severity !== severityFilter) return false;
    if (sourceFilter !== "all" && d.streamSource !== sourceFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        {/* Page Title & KPI Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-scada-text uppercase">
              Track Defect Intelligence Registry
            </h1>
            <p className="text-xs font-mono text-scada-muted">
              Section: Northern Railway Zone — NDLS to PWL (Down Main Line)
            </p>
          </div>

          <div className="flex items-center gap-3">
            <StatBadge severity="critical">
              {defects.filter((d) => d.severity === "critical").length} CRITICAL
            </StatBadge>
            <StatBadge severity="high">
              {defects.filter((d) => d.severity === "high").length} HIGH
            </StatBadge>
            <StatBadge severity="medium">
              {defects.filter((d) => d.severity === "medium").length} MEDIUM
            </StatBadge>
          </div>
        </div>

        {/* Timeline Chart */}
        <Card title="Defect Distribution along Track Chainage">
          <DefectTimeline defects={defects} maxChainageKm={25} />
        </Card>

        {/* Filters & Main Split */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Defect Table (2 cols) */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-scada-panel p-3 rounded-lg border border-scada-border">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-scada-muted">Severity:</span>
                {(["all", "critical", "high", "medium"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setSeverityFilter(s)}
                    className={`px-2.5 py-1 rounded text-[10px] font-mono uppercase transition ${
                      severityFilter === s
                        ? "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan/40"
                        : "text-scada-muted hover:text-scada-text"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-scada-muted">Source:</span>
                {(["all", "vision", "geometry", "fused"] as const).map((src) => (
                  <button
                    key={src}
                    onClick={() => setSourceFilter(src)}
                    className={`px-2.5 py-1 rounded text-[10px] font-mono uppercase transition ${
                      sourceFilter === src
                        ? "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan/40"
                        : "text-scada-muted hover:text-scada-text"
                    }`}
                  >
                    {src}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-hidden rounded-lg border border-scada-border bg-scada-panel">
              <table className="w-full text-left text-xs font-mono">
                <thead className="border-b border-scada-border bg-scada-panel-header text-scada-muted uppercase text-[10px]">
                  <tr>
                    <th className="p-3">ID / Time</th>
                    <th className="p-3">Chainage</th>
                    <th className="p-3">Defect Class</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-scada-border/60">
                  {filteredDefects.map((d) => (
                    <tr
                      key={d.id}
                      onClick={() => setSelectedDefect(d)}
                      className={`cursor-pointer transition-colors ${
                        selectedDefect?.id === d.id
                          ? "bg-scada-cyan/10 border-l-2 border-scada-cyan"
                          : "hover:bg-scada-panel-header/50"
                      }`}
                    >
                      <td className="p-3">
                        <div className="font-bold text-scada-text">{d.id}</div>
                        <div className="text-[10px] text-scada-muted">
                          {new Date(d.timestamp).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="p-3 font-semibold text-scada-cyan">
                        {(d.chainageM / 1000).toFixed(3)} km
                      </td>
                      <td className="p-3 uppercase text-scada-text">
                        {d.defectClass.replace("_", " ")}
                      </td>
                      <td className="p-3">
                        <StatBadge severity={d.severity}>
                          {d.severity}
                        </StatBadge>
                      </td>
                      <td className="p-3 text-scada-text">
                        {(d.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="p-3">
                        <Link
                          href={`/video?seek=${d.videoTimestampSec || 0}`}
                          className="text-[10px] text-scada-cyan hover:underline"
                        >
                          View Video →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Defect Detail & Evidence Panel */}
          <div className="flex flex-col gap-4">
            <Card title="Defect Evidence & Diagnostics">
              {selectedDefect ? (
                <div className="flex flex-col gap-4 text-xs font-mono">
                  <div className="flex items-center justify-between border-b border-scada-border pb-2">
                    <span className="text-sm font-bold text-scada-text">
                      {selectedDefect.id}
                    </span>
                    <StatBadge severity={selectedDefect.severity}>
                      {selectedDefect.severity.toUpperCase()}
                    </StatBadge>
                  </div>

                  {/* Simulated defect visual snapshot */}
                  <div className="relative aspect-video w-full rounded border border-scada-border bg-black/60 flex items-center justify-center overflow-hidden">
                    <div className="absolute inset-0 scada-grid opacity-40" />
                    <div className="relative z-10 flex flex-col items-center gap-1 text-center p-4">
                      <span className="h-3 w-3 rounded-full bg-scada-red animate-ping" />
                      <span className="text-xs font-bold text-scada-text uppercase">
                        {selectedDefect.defectClass.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-scada-muted">
                        Frame Capture at Chainage {(selectedDefect.chainageM / 1000).toFixed(3)} km
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 bg-scada-panel-header p-3 rounded border border-scada-border">
                    <div className="flex justify-between">
                      <span className="text-scada-muted">Source Stream:</span>
                      <span className="text-scada-cyan uppercase">{selectedDefect.streamSource}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-muted">Video Offset:</span>
                      <span className="text-scada-text">{selectedDefect.videoTimestampSec}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-muted">Model Confidence:</span>
                      <span className="text-scada-green">{(selectedDefect.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-scada-muted">GPS Coords:</span>
                      <span className="text-scada-text">
                        {selectedDefect.coordinates?.lat.toFixed(3)}°N, {selectedDefect.coordinates?.lng.toFixed(3)}°E
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-scada-muted leading-relaxed">
                    {selectedDefect.description}
                  </p>

                  <div className="flex gap-2 mt-2">
                    <Link
                      href={`/video?seek=${selectedDefect.videoTimestampSec || 0}`}
                      className="flex-1 text-center py-2 rounded bg-scada-cyan/20 border border-scada-cyan text-scada-cyan hover:bg-scada-cyan/30 transition text-xs font-bold uppercase"
                    >
                      Play Synced Video
                    </Link>
                    <Link
                      href="/map"
                      className="flex-1 text-center py-2 rounded bg-scada-panel border border-scada-border hover:border-scada-border-bright text-scada-text transition text-xs font-bold uppercase"
                    >
                      Locate on Map
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-xs font-mono text-scada-muted">
                  Select a defect to inspect evidence
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
