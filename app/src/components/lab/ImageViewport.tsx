// Interactive Viewport with Pan/Zoom and Pixel-Perfect SVG Overlays (tc.v1).

"use client";

import React, { useState, useRef, useEffect } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, Sparkles, AlertCircle } from "lucide-react";
import type { InferenceResult } from "@/lib/types";

interface ImageViewportProps {
  imageSrc: string | null;
  inferenceResult: InferenceResult | null;
  isLoading: boolean;
  isSimulated?: boolean;
  onCoordinatesChange?: (coords: { x: number; y: number } | null) => void;
}

export function ImageViewport({
  imageSrc,
  inferenceResult,
  isLoading,
  isSimulated = false,
  onCoordinatesChange,
}: ImageViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);
  const [imageDims, setImageDims] = useState<{ width: number; height: number }>({
    width: 640,
    height: 480,
  });

  const handleZoomIn = () => setScale((s) => Math.min(s + 0.25, 4));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.25, 0.5));
  const handleResetZoom = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }

    // Track pixel coordinates relative to the natural image space
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      const relativeX = (e.clientX - rect.left) / rect.width;
      const relativeY = (e.clientY - rect.top) / rect.height;

      if (relativeX >= 0 && relativeX <= 1 && relativeY >= 0 && relativeY <= 1) {
        const pixelX = Math.round(relativeX * imageDims.width);
        const pixelY = Math.round(relativeY * imageDims.height);
        setCursorPos({ x: pixelX, y: pixelY });
        onCoordinatesChange?.({ x: pixelX, y: pixelY });
      } else {
        setCursorPos(null);
        onCoordinatesChange?.(null);
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 0.15 : -0.15;
    setScale((s) => Math.max(0.5, Math.min(s + zoomFactor, 4)));
  };

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.currentTarget;
    setImageDims({
      width: target.naturalWidth || 640,
      height: target.naturalHeight || 480,
    });
  };

  const hasResult = !!inferenceResult;
  const rails = inferenceResult?.rails || [];
  const sleepers = inferenceResult?.sleepers || [];
  const yoloBoxes = inferenceResult?.yolo_boxes || [];
  const yoloLoaded = inferenceResult?.yolo_weights_loaded ?? false;

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        setIsDragging(false);
        setCursorPos(null);
      }}
      onWheel={handleWheel}
      className="relative w-full h-[520px] rounded-xl border border-scada-border bg-slate-950 overflow-hidden select-none cursor-crosshair flex items-center justify-center"
      style={{
        backgroundImage: `radial-gradient(#1e293b 1px, transparent 1px)`,
        backgroundSize: "20px 20px",
      }}
    >
      {/* 1. Zoom / Pan Overlay Controls */}
      <div className="absolute top-3 right-3 z-30 flex items-center gap-1 bg-slate-900/90 border border-scada-border rounded-lg p-1 shadow-xl backdrop-blur-sm">
        <button
          onClick={handleZoomIn}
          title="Zoom In (+)"
          className="p-1.5 rounded text-scada-muted hover:text-white hover:bg-slate-800 transition"
        >
          <ZoomIn size={15} />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out (-)"
          className="p-1.5 rounded text-scada-muted hover:text-white hover:bg-slate-800 transition"
        >
          <ZoomOut size={15} />
        </button>
        <button
          onClick={handleResetZoom}
          title="Reset Zoom"
          className="p-1.5 rounded text-scada-muted hover:text-white hover:bg-slate-800 transition"
        >
          <RotateCcw size={15} />
        </button>
        <span className="text-[10px] font-mono font-bold text-cyan-400 px-2 border-l border-scada-border/60">
          {Math.round(scale * 100)}%
        </span>
      </div>

      {/* 2. Top-Left Status & Honesty Badges */}
      <div className="absolute top-3 left-3 z-30 flex flex-col gap-1.5 pointer-events-none">
        {hasResult && !yoloLoaded && (
          <div className="flex items-center gap-1.5 bg-amber-500/20 border border-amber-500/50 text-amber-300 px-2.5 py-1 text-[11px] font-mono rounded shadow-lg backdrop-blur-sm">
            <AlertCircle size={13} className="text-amber-400" />
            <span>⚠ YOLO Weights Not Loaded (Hough Line Overlay Active)</span>
          </div>
        )}

        {isSimulated && (
          <div className="flex items-center gap-1.5 bg-blue-500/20 border border-blue-500/50 text-blue-300 px-2.5 py-1 text-[11px] font-mono rounded shadow-lg backdrop-blur-sm">
            <Sparkles size={13} className="text-blue-400" />
            <span>[SIMULATED INFERENCE - DEMO MODE]</span>
          </div>
        )}
      </div>

      {/* 3. Central Image & SVG Projection Layer */}
      {imageSrc ? (
        <div
          className="relative transition-transform duration-75 ease-out origin-center"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          }}
        >
          {/* Base Track Image */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={imgRef}
            src={imageSrc}
            alt="Track Inspection Frame"
            onLoad={handleImageLoad}
            className="max-h-[460px] max-w-[620px] object-contain rounded-lg border border-slate-700 shadow-2xl pointer-events-none"
            draggable={false}
          />

          {/* SVG Vector Overlay Scaled Exactly to Image Dimensions */}
          {hasResult && (
            <svg
              viewBox={`0 0 ${imageDims.width} ${imageDims.height}`}
              preserveAspectRatio="xMidYMid meet"
              className="absolute inset-0 w-full h-full pointer-events-none"
            >
              {/* Rails (Hough Longitudinal Lines) */}
              {rails.map((line, idx) => (
                <g key={`rail-${idx}`}>
                  <line
                    x1={line.x1}
                    y1={line.y1}
                    x2={line.x2}
                    y2={line.y2}
                    stroke="#00F0FF"
                    strokeWidth="3"
                    strokeDasharray="6 3"
                    className="animate-pulse"
                  />
                  <text
                    x={(line.x1 + line.x2) / 2 + 6}
                    y={(line.y1 + line.y2) / 2}
                    fill="#00F0FF"
                    fontSize="10"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    Rail θ:{Math.round(line.theta_deg || 0)}°
                  </text>
                </g>
              ))}

              {/* Sleepers (Transverse Ties) */}
              {sleepers.map((line, idx) => (
                <line
                  key={`sleeper-${idx}`}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke="#10B981"
                  strokeWidth="2"
                  opacity="0.85"
                />
              ))}

              {/* YOLO Bounding Boxes (Rendered ONLY if weights loaded) */}
              {yoloLoaded &&
                yoloBoxes.map((box, idx) => {
                  const width = box.xmax - box.xmin;
                  const height = box.ymax - box.ymin;
                  return (
                    <g key={`box-${idx}`}>
                      <rect
                        x={box.xmin}
                        y={box.ymin}
                        width={width}
                        height={height}
                        fill="rgba(239, 68, 68, 0.15)"
                        stroke="#EF4444"
                        strokeWidth="2.5"
                        rx="2"
                      />
                      <rect
                        x={box.xmin}
                        y={Math.max(0, box.ymin - 18)}
                        width={Math.max(100, (box.class.length + 6) * 7)}
                        height="18"
                        fill="#EF4444"
                        rx="2"
                      />
                      <text
                        x={box.xmin + 4}
                        y={Math.max(12, box.ymin - 5)}
                        fill="#FFFFFF"
                        fontSize="10"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        {box.class} ({(box.confidence * 100).toFixed(0)}%)
                      </text>
                    </g>
                  );
                })}
            </svg>
          )}

          {/* Loading Indicator Spinner */}
          {isLoading && (
            <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-[2px] rounded-lg flex items-center justify-center">
              <div className="flex flex-col items-center gap-2 font-mono text-cyan-400 text-xs">
                <div className="h-8 w-8 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
                <span>Running Computer Vision Inference...</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 text-scada-muted font-mono text-xs">
          <Crosshair size={36} className="text-slate-600 animate-pulse" />
          <p>Select a sample track frame or drop an image below to initiate perception analysis</p>
        </div>
      )}

      {/* 4. Bottom-Right Crosshair Coordinates HUD */}
      {cursorPos && (
        <div className="absolute bottom-3 right-3 z-30 bg-slate-900/90 border border-scada-border px-2.5 py-1 rounded text-[10px] font-mono text-cyan-300 shadow-xl backdrop-blur-sm pointer-events-none">
          X: {cursorPos.x}px · Y: {cursorPos.y}px
        </div>
      )}
    </div>
  );
}
