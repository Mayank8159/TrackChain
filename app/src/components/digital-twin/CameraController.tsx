"use client";

import React, { useRef, useEffect } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

export type CameraMode = "orbit" | "follow" | "topdown";

interface CameraControllerProps {
  mode: CameraMode;
  currentChainageM: number;
  minZ?: number;
  maxZ?: number;
}

export function CameraController({
  mode,
  currentChainageM,
  minZ = 0,
  maxZ = 1000,
}: CameraControllerProps) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const targetRef = useRef(new THREE.Vector3(0, 0, currentChainageM));

  // Reset controls target when switching to orbit mode
  useEffect(() => {
    if (mode === "orbit" && controlsRef.current) {
      controlsRef.current.target.set(0, 0.5, currentChainageM);
      controlsRef.current.update();
    }
  }, [mode, currentChainageM]);

  useFrame((state) => {
    const targetZ = currentChainageM;

    if (mode === "follow") {
      // Smoothly interpolate camera position behind and slightly above the playhead
      state.camera.position.x = THREE.MathUtils.lerp(state.camera.position.x, 0, 0.08);
      state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, 4.2, 0.08);
      state.camera.position.z = THREE.MathUtils.lerp(
        state.camera.position.z,
        targetZ - 12,
        0.08
      );

      // Look ahead along the corridor
      targetRef.current.x = THREE.MathUtils.lerp(targetRef.current.x, 0, 0.08);
      targetRef.current.y = THREE.MathUtils.lerp(targetRef.current.y, 0.4, 0.08);
      targetRef.current.z = THREE.MathUtils.lerp(
        targetRef.current.z,
        targetZ + 18,
        0.08
      );

      state.camera.lookAt(targetRef.current);
    } else if (mode === "topdown") {
      state.camera.position.x = THREE.MathUtils.lerp(state.camera.position.x, 0, 0.08);
      state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, 35, 0.08);
      state.camera.position.z = THREE.MathUtils.lerp(
        state.camera.position.z,
        targetZ,
        0.08
      );

      state.camera.lookAt(0, 0, targetZ);
    }
  });

  return mode === "orbit" ? (
    <OrbitControls
      ref={controlsRef}
      enableDamping
      dampingFactor={0.08}
      maxPolarAngle={Math.PI / 2 - 0.02} // Prevent camera going below ground
      minDistance={2}
      maxDistance={120}
    />
  ) : null;
}
