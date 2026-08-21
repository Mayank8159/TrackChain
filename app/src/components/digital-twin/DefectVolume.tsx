"use client";

import React, { useState } from "react";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import type { DefectEvent, SeverityLevel } from "@/lib/types";
import { getSeverityMeta } from "@/lib/severity";
import { formatChainage, formatConfidence } from "@/lib/format";

interface DefectVolumeProps {
  defect: DefectEvent;
  isSelected?: boolean;
  onSelect?: (defect: DefectEvent) => void;
  onSeek?: (chainageM: number) => void;
}

export function DefectVolume({
  defect,
  isSelected = false,
  onSelect,
  onSeek,
}: DefectVolumeProps) {
  const [hovered, setHovered] = useState(false);

  const chainageM = (defect as any).chainageM ?? (defect as any).chainage_m ?? 0;
  const severity = (defect.severity || "medium") as SeverityLevel;
  const meta = getSeverityMeta(severity);
  const colorHex = meta.hex || "#f59e0b";

  const handleClick = (e: any) => {
    e.stopPropagation();
    onSelect?.(defect);
    onSeek?.(chainageM);
  };

  return (
    <group position={[0, 0.4, chainageM]}>
      {/* 3D Glass Defect Bounding Volume */}
      <mesh
        castShadow
        onClick={handleClick}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <boxGeometry args={[2.0, 0.65, 1.4]} />
        <meshPhysicalMaterial
          color={colorHex}
          emissive={colorHex}
          emissiveIntensity={isSelected ? 1.2 : hovered ? 0.9 : 0.45}
          transparent
          opacity={isSelected ? 0.65 : hovered ? 0.5 : 0.28}
          roughness={0.15}
          metalness={0.1}
          transmission={0.5}
          clearcoat={1}
        />
      </mesh>

      {/* Wireframe Outline Highlight */}
      <mesh>
        <boxGeometry args={[2.02, 0.67, 1.42]} />
        <meshBasicMaterial
          color={colorHex}
          wireframe
          transparent
          opacity={isSelected ? 0.9 : hovered ? 0.7 : 0.3}
        />
      </mesh>

      {/* Pulsing Base Ring when Selected */}
      {isSelected && (
        <mesh position={[0, -0.32, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1.2, 1.4, 32]} />
          <meshBasicMaterial
            color={colorHex}
            transparent
            opacity={0.8}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* 3D Point Light for Volume Glow */}
      <pointLight
        color={colorHex}
        intensity={isSelected ? 1.5 : hovered ? 1.0 : 0.3}
        distance={4}
        decay={2}
      />

      {/* Holographic HTML Label Overlay (Hover or Selected) */}
      {(hovered || isSelected) && (
        <Html
          position={[0, 1.0, 0]}
          center
          distanceFactor={18}
          style={{ pointerEvents: "none" }}
        >
          <div className="flex flex-col gap-1 p-2.5 rounded-control border border-white/20 bg-slate-950/90 text-white shadow-2xl backdrop-blur-md font-mono text-[11px] min-w-[190px]">
            <div className="flex items-center justify-between border-b border-white/10 pb-1">
              <span className="font-bold uppercase text-white">
                {defect.id}
              </span>
              <span
                className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                style={{
                  backgroundColor: colorHex + "30",
                  color: colorHex,
                  border: `1px solid ${colorHex}50`,
                }}
              >
                {defect.severity}
              </span>
            </div>
            <div className="text-cyan-400 font-bold text-xs uppercase">
              {defect.defectClass?.replace(/_/g, " ")}
            </div>
            <div className="text-[10px] text-slate-400">
              Chainage:{" "}
              <strong className="text-white">
                {formatChainage(chainageM)}
              </strong>
            </div>
            <div className="text-[10px] text-emerald-400">
              Confidence: {formatConfidence(defect.confidence)}
            </div>
            <div className="text-[9px] text-cyan-300/80 italic mt-0.5">
              Click to sync 2D video & waveforms →
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
