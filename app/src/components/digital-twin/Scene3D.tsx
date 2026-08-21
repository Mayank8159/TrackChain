"use client";

import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Grid } from "@react-three/drei";
import { TrackCorridor, TrackLayers } from "./TrackCorridor";
import { DefectVolume } from "./DefectVolume";
import { CameraController, CameraMode } from "./CameraController";
import type { Projected3DTrack } from "@/lib/track-3d-math";
import type { DefectEvent } from "@/lib/types";

interface Scene3DProps {
  projectedTrack: Projected3DTrack;
  defects?: DefectEvent[];
  selectedDefectId?: string;
  onSelectDefect?: (defect: DefectEvent) => void;
  onSeekChainage?: (chainageM: number) => void;
  currentChainageM: number;
  cameraMode: CameraMode;
  layers: TrackLayers;
}

export function Scene3D({
  projectedTrack,
  defects = [],
  selectedDefectId,
  onSelectDefect,
  onSeekChainage,
  currentChainageM,
  cameraMode,
  layers,
}: Scene3DProps) {
  return (
    <div className="relative w-full h-full bg-[#020617] overflow-hidden select-none">
      {/* Background Holographic Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyan-900/15 via-slate-950/80 to-[#020617] pointer-events-none" />

      <Canvas
        shadows
        camera={{ position: [0, 5, -14], fov: 45, near: 0.1, far: 500 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: "100%", height: "100%" }}
      >
        <Suspense fallback={null}>
          {/* Depth Fog to fade distant corridor into the deep void */}
          <fog attach="fog" args={["#020617", 25, 180]} />

          {/* Holographic Lighting */}
          <ambientLight intensity={0.35} />
          <directionalLight
            position={[20, 30, 15]}
            intensity={1.2}
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
            shadow-camera-near={0.5}
            shadow-camera-far={100}
          />
          <directionalLight
            position={[-15, 10, -20]}
            intensity={0.5}
            color="#06b6d4"
          />

          {/* Cyber SCADA Ground Grid */}
          <Grid
            position={[0, -0.28, (projectedTrack.minZ + projectedTrack.maxZ) / 2 || 50]}
            args={[150, Math.max(150, projectedTrack.lengthMeters + 40)]}
            cellSize={2}
            cellThickness={0.6}
            cellColor="#0891b2"
            sectionSize={10}
            sectionThickness={1.2}
            sectionColor="#06b6d4"
            fadeDistance={150}
            fadeStrength={1.5}
          />

          {/* Procedural Track Corridor (Instanced Sleepers + Rails) */}
          <TrackCorridor
            projectedTrack={projectedTrack}
            layers={layers}
            currentChainageM={currentChainageM}
          />

          {/* 3D Glass Defect Bounding Volumes */}
          {defects.map((defect) => (
            <DefectVolume
              key={defect.id}
              defect={defect}
              isSelected={selectedDefectId === defect.id}
              onSelect={onSelectDefect}
              onSeek={onSeekChainage}
            />
          ))}

          {/* Camera Controller with smooth interpolation */}
          <CameraController
            mode={cameraMode}
            currentChainageM={currentChainageM}
            minZ={projectedTrack.minZ}
            maxZ={projectedTrack.maxZ}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
