// GIS view: GNSS track polyline with severity-colored defect markers.

"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { Card } from "@/components/ui/Card";
import { TrackMap } from "@/components/map/TrackMap";
import { StatBadge } from "@/components/ui/StatBadge";
import type { DefectEvent } from "@/lib/types";

const MOCK_MAP_DEFECTS: DefectEvent[] = [
  {
    id: "DEF-001",
    sessionId: "SES-20260821-01",
    timestamp: "2026-08-21T00:15:32Z",
    chainageM: 3420,
    defectClass: "crack",
    severity: "critical",
    confidence: 0.94,
    streamSource: "vision",
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
    status: "open",
    coordinates: { lat: 28.452, lng: 77.319 },
  },
];

export default function MapPage() {
  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(
    null
  );

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-scada-text uppercase">
              GIS Track Polyline & Geospatial Fault Map
            </h1>
            <p className="text-xs font-mono text-scada-muted">
              Spatial chainage alignment with GNSS differential positioning
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="badge-cyan">GNSS Fix: RTK FLOAT (±0.05m)</span>
            <span className="badge-green">5 Track Sections Active</span>
          </div>
        </div>

        {/* Map Canvas */}
        <Card title="Live GNSS Corridor Map">
          <TrackMap
            defects={MOCK_MAP_DEFECTS}
            currentChainageM={14200}
            onSelectDefect={(d) => setSelectedDefect(d)}
          />
        </Card>

        {/* Corridor Analytics Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="scada-card p-4 border border-scada-border">
            <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
              Corridor Length
            </h4>
            <p className="text-2xl font-mono font-bold text-scada-cyan mt-1">
              25.000 <span className="text-xs text-scada-muted">km</span>
            </p>
            <p className="text-[10px] font-mono text-scada-muted mt-2">
              Route: New Delhi (NDLS) → Ballabgarh (BVH)
            </p>
          </div>

          <div className="scada-card p-4 border border-scada-border">
            <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
              Flagged Anomalies
            </h4>
            <p className="text-2xl font-mono font-bold text-scada-amber mt-1">
              5 <span className="text-xs text-scada-muted">hotspots</span>
            </p>
            <p className="text-[10px] font-mono text-scada-muted mt-2">
              Density: 0.20 defects / km
            </p>
          </div>

          <div className="scada-card p-4 border border-scada-border">
            <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
              Track Quality Index (TQI)
            </h4>
            <p className="text-2xl font-mono font-bold text-scada-green mt-1">
              88.4 <span className="text-xs text-scada-muted">/ 100</span>
            </p>
            <p className="text-[10px] font-mono text-scada-muted mt-2">
              Standard: RDSO Comprehensive Track Index
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
