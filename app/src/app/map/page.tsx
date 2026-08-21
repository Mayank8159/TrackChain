// GIS Track Polyline & Geospatial Fault Map with Evidence Drawer integration (tc.v1).

"use client";

import React, { useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { TrackMap } from "@/components/map/TrackMap";
import { EvidenceDrawer } from "@/components/defects/EvidenceDrawer";
import { DataError } from "@/components/ui/DataError";
import { useModeStore } from "@/stores/mode-store";
import { useDefects } from "@/hooks/useDefects";
import { useToast } from "@/components/ui/Toast";
import { formatChainage } from "@/lib/format";
import type { DefectEvent } from "@/lib/types";

export default function MapPage() {
  const { mode } = useModeStore();
  const { defects = [], isError, refetch } = useDefects();
  const { showToast } = useToast();

  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(null);
  const [isMutating, setIsMutating] = useState<boolean>(false);

  const handleAcknowledge = (d: DefectEvent) => {
    setIsMutating(true);
    setTimeout(() => {
      setIsMutating(false);
      showToast({
        type: "success",
        title: "Defect Acknowledged",
        description: `Incident ${d.id} at ${formatChainage(d.chainageM)} acknowledged via GIS Map.`,
      });
    }, 200);
  };

  const handleReject = (d: DefectEvent) => {
    setIsMutating(true);
    setTimeout(() => {
      setIsMutating(false);
      showToast({
        type: "warning",
        title: "Defect Dismissed",
        description: `Incident ${d.id} flagged as false positive from geospatial view.`,
      });
    }, 200);
  };

  const handleAssign = (d: DefectEvent) => {
    showToast({
      type: "info",
      title: "Crew Dispatched",
      description: `Dispatched track maintenance team to GPS coordinates: ${d.latitude?.toFixed(4)}°N, ${d.longitude?.toFixed(4)}°E.`,
    });
  };

  const criticalCount = defects.filter((d) => d.severity === "critical").length;
  const highCount = defects.filter((d) => d.severity === "high").length;

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="GIS Track Polyline & Geospatial Fault Map"
        description="High-precision spatial chainage alignment with differential GNSS RTK positioning"
        breadcrumbs={[{ label: "Map" }]}
        actions={
          <div className="flex items-center gap-3">
            <span className="badge-cyan text-xs">
              GNSS FIX: RTK FLOAT (±0.05m)
            </span>
            <span className="badge-green text-xs">
              7 STATIONS ACTIVE
            </span>
          </div>
        }
      />

      {/* 2. Top Corridor KPI Analytics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Monitored Corridor
          </h4>
          <p className="text-2xl font-mono font-bold text-white mt-1">
            140.0 <span className="text-xs text-scada-muted">km</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            New Delhi (NDLS) → Agra Cantt (AGC)
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Spatial Anomaly Hotspots
          </h4>
          <p className="text-2xl font-mono font-bold text-amber-400 mt-1">
            {defects.length} <span className="text-xs text-scada-muted">locations</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Density: {(defects.length / 140).toFixed(3)} defects / km
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Critical Safety Hotspots
          </h4>
          <p className="text-2xl font-mono font-bold text-red-400 mt-1">
            {criticalCount} <span className="text-xs text-scada-muted">IAL zones</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Immediate Speed Restriction
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Corridor Track Quality (TQI)
          </h4>
          <p className="text-2xl font-mono font-bold text-emerald-400 mt-1">
            88.4 <span className="text-xs text-scada-muted">/ 100</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            RDSO Comprehensive Track Index
          </p>
        </div>
      </div>

      {/* 3. Interactive GIS Map Canvas */}
      <Card
        title="Live GNSS Spatial Track Map & Defect Overlay"
        badge={
          <span className="badge-cyan text-[10px]">
            INTERACTIVE GIS
          </span>
        }
      >
        {mode === "REAL" && isError ? (
          <DataError
            title="GIS Geospatial Telemetry Offline"
            message="Unable to acquire track corridor coordinates and live defect markers from the backend server."
            onRetry={() => refetch()}
          />
        ) : (
          <TrackMap
            defects={defects}
            currentChainageM={14200}
            onSelectDefect={(d) => setSelectedDefect(d)}
            selectedDefectId={selectedDefect?.id}
          />
        )}
      </Card>

      {/* 4. Slide-In Evidence Drawer */}
      <EvidenceDrawer
        defect={selectedDefect}
        isOpen={!!selectedDefect}
        onClose={() => setSelectedDefect(null)}
        onAcknowledge={handleAcknowledge}
        onReject={handleReject}
        onAssign={handleAssign}
        isMutating={isMutating}
      />
    </div>
  );
}
