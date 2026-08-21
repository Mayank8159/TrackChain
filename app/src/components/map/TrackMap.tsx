// GIS Track Corridor Map: Dynamic client loader with dark basemap and legend overlay (tc.v1).

"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { MapLegend } from "./MapLegend";
import { Card } from "../ui/Card";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import type { DefectEvent } from "../../lib/types";

// Dynamically import Leaflet map with SSR disabled to prevent window is not defined errors
const DynamicTrackMapLeaflet = dynamic(
  () => import("./TrackMapLeaflet").then((mod) => mod.TrackMapLeaflet),
  {
    ssr: false,
    loading: () => (
      <div className="h-[520px] w-full rounded-lg bg-slate-950 flex flex-col items-center justify-center font-mono text-xs text-scada-muted border border-scada-border">
        <span className="h-3 w-3 rounded-full bg-cyan-400 animate-ping mb-3" />
        <span>Loading CartoDB Dark Matter GIS Basemap & Waypoint Polylines...</span>
      </div>
    ),
  }
);

export interface TrackMapProps {
  defects?: DefectEvent[];
  currentChainageM?: number;
  onSelectDefect?: (defect: DefectEvent) => void;
  selectedDefectId?: string;
  className?: string;
}

export function TrackMap({
  defects = [],
  currentChainageM = 14200,
  onSelectDefect,
  selectedDefectId,
  className,
}: TrackMapProps) {
  return (
    <div className={`relative w-full overflow-hidden rounded-lg border border-scada-border bg-slate-950 ${className || ""}`}>
      {/* Top Left HUD Status Badge */}
      <div className="absolute top-3 left-3 z-[400] flex flex-wrap items-center gap-2 bg-slate-950/90 px-3 py-1.5 rounded-control border border-scada-border backdrop-blur font-mono text-xs shadow-xl">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-bold text-white uppercase">
          NDLS-AGC Mainline Corridor
        </span>
        <span className="text-scada-muted">|</span>
        <span className="text-cyan-400">
          RTK GNSS Fix (±0.05m)
        </span>
      </div>

      {/* Dynamic Leaflet Map Component wrapped with ErrorBoundary */}
      <ErrorBoundary fallbackTitle="GIS Mapping Engine Suspended">
        <DynamicTrackMapLeaflet
          defects={defects}
          currentChainageM={currentChainageM}
          onSelectDefect={onSelectDefect}
          selectedDefectId={selectedDefectId}
        />
      </ErrorBoundary>

      {/* Bottom Right Floating Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-[400] pointer-events-auto">
        <MapLegend />
      </div>
    </div>
  );
}
