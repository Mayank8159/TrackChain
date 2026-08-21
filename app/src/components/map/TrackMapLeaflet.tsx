// Dark Leaflet Basemap component with TQI Polylines, Station Pins, and Defect Markers (tc.v1).

"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Marker,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getSeverityMeta } from "../../lib/severity";
import { formatChainage, formatConfidence } from "../../lib/format";
import type { DefectEvent, Device } from "../../lib/types";
import { useCollabStore } from "../../stores/collab-store";
import { useDeviceStore } from "../../stores/device-store";
import type { Annotation } from "@trackchain/shared";

export interface TrackMapProps {
  defects?: DefectEvent[];
  currentChainageM?: number;
  onSelectDefect?: (defect: DefectEvent) => void;
  selectedDefectId?: string;
  className?: string;
}

// Station milestones along Delhi-Agra mainline corridor
interface StationCoord {
  name: string;
  code: string;
  km: number;
  lat: number;
  lng: number;
}

const STATIONS: StationCoord[] = [
  { name: "New Delhi", code: "NDLS", km: 0, lat: 28.6427, lng: 77.2195 },
  { name: "Hazrat Nizamuddin", code: "NZM", km: 7.2, lat: 28.5882, lng: 77.2534 },
  { name: "Faridabad", code: "FDB", km: 28.5, lat: 28.4089, lng: 77.3178 },
  { name: "Palwal", code: "PWL", km: 58.0, lat: 28.1436, lng: 77.3328 },
  { name: "Kosi Kalan", code: "KSV", km: 99.0, lat: 27.7942, lng: 77.4325 },
  { name: "Mathura Jn", code: "MTJ", km: 134.0, lat: 27.4924, lng: 77.6737 },
  { name: "Agra Cantt", code: "AGC", km: 140.0, lat: 27.1583, lng: 78.0081 },
];

// TQI Segments connecting station waypoints with Track Quality colors
const TQI_TRACK_SEGMENTS = [
  {
    name: "NDLS - NZM",
    coords: [
      [28.6427, 77.2195],
      [28.618, 77.235],
      [28.5882, 77.2534],
    ] as [number, number][],
    tqi: 92,
    color: "#10B981", // Green (>85)
  },
  {
    name: "NZM - FDB",
    coords: [
      [28.5882, 77.2534],
      [28.535, 77.284],
      [28.472, 77.305],
      [28.4089, 77.3178],
    ] as [number, number][],
    tqi: 88,
    color: "#10B981", // Green
  },
  {
    name: "FDB - PWL",
    coords: [
      [28.4089, 77.3178],
      [28.337, 77.329],
      [28.245, 77.331],
      [28.1436, 77.3328],
    ] as [number, number][],
    tqi: 76,
    color: "#F59E0B", // Amber (70-85)
  },
  {
    name: "PWL - KSV",
    coords: [
      [28.1436, 77.3328],
      [28.021, 77.352],
      [27.892, 77.391],
      [27.7942, 77.4325],
    ] as [number, number][],
    tqi: 89,
    color: "#10B981", // Green
  },
  {
    name: "KSV - MTJ",
    coords: [
      [27.7942, 77.4325],
      [27.682, 77.512],
      [27.575, 77.604],
      [27.4924, 77.6737],
    ] as [number, number][],
    tqi: 68,
    color: "#EF4444", // Red (<70)
  },
  {
    name: "MTJ - AGC",
    coords: [
      [27.4924, 77.6737],
      [27.385, 77.782],
      [27.242, 77.915],
      [27.1583, 78.0081],
    ] as [number, number][],
    tqi: 91,
    color: "#10B981", // Green
  },
];

// Helper to create custom HTML/SVG divIcon matching SeverityBadge colors
function createDefectIcon(defect: DefectEvent, isSelected: boolean) {
  const meta = getSeverityMeta(defect.severity);
  const isCritical = defect.severity === "critical";
  const size = isCritical ? 24 : defect.severity === "high" ? 20 : 16;

  const html = `
    <div style="position: relative; width: ${size}px; height: ${size}px; cursor: pointer;">
      ${
        isCritical
          ? `<div style="position: absolute; inset: -4px; border-radius: 9999px; background-color: ${meta.hex}; opacity: 0.4; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>`
          : ""
      }
      <div style="
        position: relative;
        width: 100%;
        height: 100%;
        border-radius: 9999px;
        background-color: ${meta.hex};
        border: 2px solid #FFFFFF;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.6), 0 0 10px ${meta.hex};
        display: flex;
        align-items: center;
        justify-content: center;
        transform: ${isSelected ? "scale(1.3)" : "scale(1)"};
        transition: transform 0.2s;
      ">
        <div style="width: 4px; height: 4px; border-radius: 9999px; background-color: #FFFFFF;"></div>
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "scada-defect-pin",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createAnnotationIcon(annotation: Annotation) {
  const colorClass = annotation.author.avatarColor || "bg-cyan-500";
  const html = `
    <div style="position: relative; width: 28px; height: 28px; cursor: pointer; display: flex; align-items: center; justify-content: center;">
      <div class="${colorClass}" style="
        position: absolute;
        inset: 0;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 2px solid white;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5);
      "></div>
      <div style="
        position: relative;
        z-index: 10;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: white;
      "></div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "scada-collab-pin",
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
}

function createNodeIcon(device: Device) {
  const isPending = device.status === "pending_approval";
  const html = `
    <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;">
      <span style="position: absolute; width: 32px; height: 32px; border-radius: 50%; background-color: rgba(6, 182, 212, 0.35);" class="${isPending ? 'animate-ping' : 'animate-pulse'}"></span>
      <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background-color: #020617; border: 2px solid #06B6D4; box-shadow: 0 0 12px rgba(6, 182, 212, 0.9);">
        <span style="font-size: 11px; line-height: 1;">📷</span>
      </div>
    </div>
  `;
  return L.divIcon({
    html,
    className: "scada-node-pin",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
}

function MapViewController({ bounds }: { bounds: L.LatLngBoundsExpression }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, bounds]);
  return null;
}

function MapAutoPanner({ targetCoords }: { targetCoords: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (targetCoords) {
      map.panTo(targetCoords, { animate: true, duration: 1.2 });
    }
  }, [map, targetCoords]);
  return null;
}

function MapClickHandler({
  isDropMode,
  onDropPin,
}: {
  isDropMode: boolean;
  onDropPin: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click: (e) => {
      if (isDropMode) {
        onDropPin(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

export function TrackMapLeaflet({
  defects = [],
  currentChainageM = 14200,
  onSelectDefect,
  selectedDefectId,
  className,
}: TrackMapProps) {
  // Corridor map bounds covering New Delhi to Agra
  const corridorBounds: L.LatLngBoundsExpression = [
    [28.7, 77.15],
    [27.1, 78.05],
  ];

  const collabStore = useCollabStore();
  const { discoveredDevices, latestDiscoveredNode } = useDeviceStore();
  const spatialAnnotations = collabStore.annotations.filter((a) => a.type === "SPATIAL" && a.coordinates);

  const [isDropMode, setIsDropMode] = useState(false);
  const [autoPanTarget, setAutoPanTarget] = useState<[number, number] | null>(null);

  // Auto-pan to newly discovered edge node location
  useEffect(() => {
    if (
      latestDiscoveredNode &&
      typeof latestDiscoveredNode.latitude === "number" &&
      typeof latestDiscoveredNode.longitude === "number"
    ) {
      setAutoPanTarget([latestDiscoveredNode.latitude, latestDiscoveredNode.longitude]);
    }
  }, [latestDiscoveredNode]);

  const activeDeviceNodes = useMemo(() => {
    const map = new Map<string, Device>();
    discoveredDevices.forEach((d) => {
      if (typeof d.latitude === "number" && typeof d.longitude === "number") {
        map.set(d.deviceId, d);
      }
    });
    return Array.from(map.values());
  }, [discoveredDevices]);

  const handleDropPin = (lat: number, lng: number) => {
    const text = window.prompt("Enter annotation text:", "Check this area.");
    if (text) {
      collabStore.addAnnotation({
        id: `ann-sp-${Date.now()}`,
        type: "SPATIAL",
        coordinates: [lat, lng],
        author: {
          id: "u-me",
          name: "You",
          role: "Operator",
          avatarColor: "bg-cyan-500",
          status: "online",
        },
        text,
        mentions: [],
        created_at: Date.now(),
      });
    }
    setIsDropMode(false);
  };

  return (
    <div className={`relative w-full h-[520px] rounded-lg overflow-hidden bg-[#050c1a] ${className || ""}`}>
      {/* Holographic vignette — blends map edges into the glass card */}
      <div className="leaflet-map-vignette pointer-events-none z-10" aria-hidden="true" />

      {/* Drop Pin UI Toggle */}
      <div className="absolute top-4 right-4 z-[400]">
        <button
          onClick={() => setIsDropMode(!isDropMode)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-control font-mono text-xs border transition-all shadow-xl backdrop-blur-md ${
            isDropMode
              ? "bg-cyan-500/20 border-cyan-400 text-cyan-300"
              : "bg-slate-900/80 border-slate-700 text-slate-300 hover:bg-slate-800"
          }`}
        >
          <span>📍</span>
          {isDropMode ? "CLICK MAP TO DROP" : "DROP ANNOTATION"}
        </button>
      </div>

      <MapContainer
        bounds={corridorBounds}
        zoom={9}
        scrollWheelZoom={false}
        style={{ width: "100%", height: "100%", background: "#050c1a", cursor: isDropMode ? "crosshair" : "grab" }}
        attributionControl={false}
      >
        <MapViewController bounds={corridorBounds} />
        <MapAutoPanner targetCoords={autoPanTarget} />
        <MapClickHandler isDropMode={isDropMode} onDropPin={handleDropPin} />

        {/* 1. Dark Basemap Tiles (CartoDB Dark Matter) */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={19}
          subdomains="abcd"
        />

        {/* 2. Multi-Segment TQI-Colored Track Polylines */}
        {TQI_TRACK_SEGMENTS.map((seg, idx) => (
          <React.Fragment key={idx}>
            {/* Outer track line casing */}
            <Polyline
              positions={seg.coords}
              pathOptions={{
                color: "#0F172A",
                weight: 8,
                opacity: 0.9,
                lineCap: "round",
                lineJoin: "round",
              }}
            />
            {/* Inner TQI colored core track */}
            <Polyline
              positions={seg.coords}
              pathOptions={{
                color: seg.color,
                weight: 4.5,
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round",
              }}
            >
              <Tooltip sticky className="scada-map-tooltip">
                <div className="font-mono text-xs p-1 bg-slate-900 text-white rounded border border-scada-border">
                  <div className="font-bold text-cyan-400">{seg.name}</div>
                  <div>TQI: <strong style={{ color: seg.color }}>{seg.tqi} / 100</strong></div>
                </div>
              </Tooltip>
            </Polyline>
          </React.Fragment>
        ))}

        {/* 3. Station Milestone Circle Pins */}
        {STATIONS.map((station) => (
          <CircleMarker
            key={station.code}
            center={[station.lat, station.lng]}
            radius={5}
            pathOptions={{
              fillColor: "#0F172A",
              fillOpacity: 1,
              color: "#38BDF8",
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} permanent={false}>
              <div className="font-mono text-[11px] bg-slate-950 p-1.5 text-white rounded border border-scada-border">
                <strong className="text-cyan-400">{station.code}</strong> — {station.name}
                <div className="text-[10px] text-scada-muted">Chainage: Km {station.km}.000</div>
              </div>
            </Tooltip>
          </CircleMarker>
        ))}

        {/* 4. Plotted Defect Anomaly Markers */}
        {defects.map((defect) => {
          const lat = defect.latitude || defect.coordinates?.lat || 28.592;
          const lng = defect.longitude || defect.coordinates?.lng || 77.248;
          const isSelected = selectedDefectId === defect.id;
          const icon = createDefectIcon(defect, isSelected);

          return (
            <Marker
              key={defect.id}
              position={[lat, lng]}
              icon={icon}
              eventHandlers={{
                click: () => onSelectDefect && onSelectDefect(defect),
              }}
            >
              <Tooltip direction="top" offset={[0, -12]}>
                <div className="font-mono text-xs p-2 bg-slate-950 text-white rounded-control border border-scada-border shadow-xl min-w-[160px]">
                  <div className="flex items-center justify-between border-b border-scada-border pb-1 mb-1">
                    <span className="font-bold text-white uppercase text-[11px]">
                      {defect.id}
                    </span>
                    <span
                      className="text-[9px] px-1.5 py-0.2 rounded font-bold uppercase"
                      style={{
                        backgroundColor: getSeverityMeta(defect.severity).hex + "25",
                        color: getSeverityMeta(defect.severity).hex,
                      }}
                    >
                      {defect.severity}
                    </span>
                  </div>
                  <div className="text-cyan-400 font-bold uppercase text-[11px]">
                    {(defect.defectClass || (defect as any).defect_class || "anomaly").replace(/_/g, " ")}
                  </div>
                  <div className="text-[10px] text-scada-muted mt-0.5">
                    Chainage: <strong className="text-white">{formatChainage(defect.chainageM ?? (defect as any).chainage_m ?? 0)}</strong>
                  </div>
                  <div className="text-[10px] text-emerald-400">
                    Confidence: {formatConfidence(defect.confidence)}
                  </div>
                  <div className="text-[9px] text-scada-accent mt-1 italic">
                    Click marker to inspect AI evidence →
                  </div>
                </div>
              </Tooltip>
            </Marker>
          );
        })}

        {/* 5. Spatial Annotations (War Room) */}
        {spatialAnnotations.map((ann) => {
          if (!ann.coordinates) return null;
          const icon = createAnnotationIcon(ann);
          return (
            <Marker key={ann.id} position={ann.coordinates} icon={icon} zIndexOffset={1000}>
              <Tooltip direction="top" offset={[0, -28]}>
                <div className="font-mono text-xs p-3 bg-slate-950/90 text-slate-200 rounded-control border border-slate-700 shadow-2xl backdrop-blur-md min-w-[200px]">
                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/10">
                    <div className={`w-4 h-4 rounded-full ${ann.author.avatarColor}`} />
                    <strong className="text-white">{ann.author.name}</strong>
                  </div>
                  <div className="text-[11px] leading-relaxed">"{ann.text}"</div>
                  <div className="text-[9px] text-slate-500 mt-2 text-right">
                    {new Date(ann.created_at).toLocaleTimeString()}
                  </div>
                </div>
              </Tooltip>
            </Marker>
          );
        })}

        {/* 6. Active & Auto-Discovered Edge Node Markers (Prompt 29) */}
        {activeDeviceNodes.map((device) => {
          const lat = device.latitude!;
          const lng = device.longitude!;
          const icon = createNodeIcon(device);

          return (
            <Marker
              key={`node-${device.deviceId}`}
              position={[lat, lng]}
              icon={icon}
              zIndexOffset={900}
            >
              <Tooltip direction="top" offset={[0, -16]}>
                <div className="font-mono text-xs p-2.5 bg-slate-950/95 text-white rounded-control border border-cyan-500/50 shadow-2xl backdrop-blur min-w-[200px]">
                  <div className="flex items-center justify-between border-b border-white/10 pb-1 mb-1.5">
                    <span className="font-bold text-cyan-300 text-[11px] flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                      {device.deviceId}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      {device.status.replace("_", " ")}
                    </span>
                  </div>
                  <div className="text-white font-bold text-[11px]">
                    {device.deviceName}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Hardware: <strong className="text-slate-200">{device.hardwareVersion}</strong>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    GPS: <span className="text-cyan-400">{lat.toFixed(4)}° N, {lng.toFixed(4)}° E</span>
                  </div>
                  <div className="text-[9px] text-emerald-400 mt-1">
                    Last Telemetry Ping: Just now (Live)
                  </div>
                </div>
              </Tooltip>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
