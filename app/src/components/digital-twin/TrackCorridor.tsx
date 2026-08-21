"use client";

import React, { useRef, useLayoutEffect, useMemo } from "react";
import * as THREE from "three";
import type { Projected3DTrack } from "@/lib/track-3d-math";

export interface TrackLayers {
  rails: boolean;
  sleepers: boolean;
  heatmap: boolean;
  centerLine: boolean;
  ballast: boolean;
}

interface TrackCorridorProps {
  projectedTrack: Projected3DTrack;
  layers?: TrackLayers;
  currentChainageM?: number;
}

export function TrackCorridor({
  projectedTrack,
  layers = {
    rails: true,
    sleepers: true,
    heatmap: true,
    centerLine: false,
    ballast: true,
  },
  currentChainageM,
}: TrackCorridorProps) {
  const sleepersRef = useRef<THREE.InstancedMesh>(null);

  const {
    leftRailVertices,
    rightRailVertices,
    centerVertices,
    sleeperMatrices,
    vertexColors,
  } = projectedTrack;

  // Configure InstancedMesh for Sleepers
  useLayoutEffect(() => {
    if (!sleepersRef.current || sleeperMatrices.length === 0) return;

    for (let i = 0; i < sleeperMatrices.length; i++) {
      sleepersRef.current.setMatrixAt(i, sleeperMatrices[i]);
    }
    sleepersRef.current.instanceMatrix.needsUpdate = true;
  }, [sleeperMatrices]);

  // Build Left Rail Primitive Object
  const leftLine = useMemo(() => {
    if (leftRailVertices.length === 0) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(leftRailVertices, 3));
    if (layers.heatmap && vertexColors.length > 0) {
      geo.setAttribute("color", new THREE.BufferAttribute(vertexColors, 3));
    }
    const mat = new THREE.LineBasicMaterial({
      color: layers.heatmap ? undefined : 0x38bdf8,
      vertexColors: layers.heatmap,
      linewidth: 3,
    });
    return new THREE.Line(geo, mat);
  }, [leftRailVertices, vertexColors, layers.heatmap]);

  // Build Right Rail Primitive Object
  const rightLine = useMemo(() => {
    if (rightRailVertices.length === 0) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(rightRailVertices, 3));
    if (layers.heatmap && vertexColors.length > 0) {
      geo.setAttribute("color", new THREE.BufferAttribute(vertexColors, 3));
    }
    const mat = new THREE.LineBasicMaterial({
      color: layers.heatmap ? undefined : 0x38bdf8,
      vertexColors: layers.heatmap,
      linewidth: 3,
    });
    return new THREE.Line(geo, mat);
  }, [rightRailVertices, vertexColors, layers.heatmap]);

  // Build Centerline Primitive Object
  const centerLine = useMemo(() => {
    if (centerVertices.length === 0) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(centerVertices, 3));
    const mat = new THREE.LineBasicMaterial({
      color: 0x64748b,
      transparent: true,
      opacity: 0.6,
    });
    return new THREE.Line(geo, mat);
  }, [centerVertices]);

  // Memory Management: Dispose of dynamic Three.js line geometries on session transition
  React.useEffect(() => {
    return () => {
      if (leftLine) {
        leftLine.geometry.dispose();
        (leftLine.material as THREE.Material).dispose();
      }
      if (rightLine) {
        rightLine.geometry.dispose();
        (rightLine.material as THREE.Material).dispose();
      }
      if (centerLine) {
        centerLine.geometry.dispose();
        (centerLine.material as THREE.Material).dispose();
      }
    };
  }, [leftLine, rightLine, centerLine]);

  // Ballast Bed Dimensions
  const ballastLength = projectedTrack.lengthMeters || 100;
  const ballastCenterZ = (projectedTrack.minZ + projectedTrack.maxZ) / 2 || 50;

  return (
    <group>
      {/* 1. Ballast Subgrade Base */}
      {layers.ballast && (
        <mesh position={[0, -0.25, ballastCenterZ]} receiveShadow>
          <boxGeometry args={[4.2, 0.2, Math.max(10, ballastLength + 20)]} />
          <meshStandardMaterial
            color="#0b1329"
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>
      )}

      {/* 2. Instanced Sleepers (1,000+ in 1 single draw call) */}
      {layers.sleepers && sleeperMatrices.length > 0 && (
        <instancedMesh
          ref={sleepersRef}
          args={[undefined, undefined, sleeperMatrices.length]}
          castShadow
          receiveShadow
        >
          <boxGeometry args={[1, 0.16, 0.26]} />
          <meshStandardMaterial
            color="#1e293b"
            roughness={0.7}
            metalness={0.3}
          />
        </instancedMesh>
      )}

      {/* 3. Left Rail */}
      {layers.rails && leftLine && <primitive object={leftLine} />}

      {/* 4. Right Rail */}
      {layers.rails && rightLine && <primitive object={rightLine} />}

      {/* 5. Centerline Axis */}
      {layers.centerLine && centerLine && <primitive object={centerLine} />}

      {/* 6. Current Inspection Train Playhead Indicator */}
      {typeof currentChainageM === "number" && (
        <group position={[0, 0.2, currentChainageM]}>
          {/* Inspection Vehicle Marker Body */}
          <mesh castShadow position={[0, 0.35, 0]}>
            <boxGeometry args={[1.9, 0.6, 2.8]} />
            <meshPhysicalMaterial
              color="#06b6d4"
              emissive="#06b6d4"
              emissiveIntensity={0.6}
              transparent
              opacity={0.75}
              roughness={0.2}
              transmission={0.4}
            />
          </mesh>

          {/* Forward Scanner Ray Beam */}
          <mesh position={[0, -0.1, 2.5]} rotation={[Math.PI / 6, 0, 0]}>
            <coneGeometry args={[1.2, 3.5, 16, 1, true]} />
            <meshBasicMaterial
              color="#22d3ee"
              transparent
              opacity={0.2}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* Scanner Light Source */}
          <pointLight
            color="#22d3ee"
            intensity={2}
            distance={8}
            decay={2}
            position={[0, 0.8, 1]}
          />
        </group>
      )}
    </group>
  );
}
