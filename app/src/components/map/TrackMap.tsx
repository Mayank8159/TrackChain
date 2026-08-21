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
    <div className={`relative w-full h-[580px] overflow-hidden bg-slate-950 rounded-xl ${className || ""}`}>
      {/* Dynamic Leaflet Map Component wrapped with ErrorBoundary */}
      <ErrorBoundary fallbackTitle="GIS Mapping Engine Suspended">
        <DynamicTrackMapLeaflet
          defects={defects}
          currentChainageM={currentChainageM}
          onSelectDefect={onSelectDefect}
          selectedDefectId={selectedDefectId}
          className="h-full w-full"
        />
      </ErrorBoundary>

      {/* The Vignette Overlay (Pointer events none) */}
      <div
        className="leaflet-map-vignette absolute inset-0 z-10 pointer-events-none"
        style={{ boxShadow: "inset 0 0 100px 40px rgba(2, 6, 23, 0.9)" }}
      />

      {/* Floating Raw HUD (Top Left) */}
      <div className="absolute top-6 left-6 z-20 pointer-events-none">
        <div className="flex items-center gap-2 mb-1">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-cyan-400">
            Live GIS Corridor Telemetry
          </p>
        </div>
        <h2 className="text-2xl font-bold font-mono text-white drop-shadow-lg flex items-baseline gap-3">
          NDLS → AGC
          <span className="text-slate-400 text-xs font-mono font-normal">
            Active Faults: {defects.length}
          </span>
        </h2>
        <div className="railway-track w-64 mt-3 mb-1" />
      </div>

      {/* Floating Raw HUD (Bottom Left Coordinates) */}
      <div className="absolute bottom-6 left-6 z-20 pointer-events-none">
        <div className="bg-slate-950/80 border border-slate-800/80 px-3 py-1.5 rounded font-mono text-[11px] text-slate-400 backdrop-blur-md">
          <span className="text-cyan-400 font-bold">RTK GNSS:</span> Fix Quality 4 (±0.05m) · 12 SVs Locked
        </div>
      </div>

      {/* Bottom Right Floating Legend Overlay */}
      <div className="absolute bottom-6 right-6 z-20 pointer-events-auto">
        <MapLegend />
      </div>
    </div>
  );
}
