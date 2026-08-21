// Hardware Health Telemetry Panel showing subsystem sensor diagnostics (tc.v1).

"use client";

import React, { useEffect } from "react";
import {
  X,
  Camera,
  Compass,
  Navigation,
  Cpu,
  Wifi,
  Zap,
  CheckCircle2,
  AlertTriangle,
  HardDrive,
  Activity,
} from "lucide-react";
import { Button } from "../ui/Button";
import type { Device } from "../../lib/types";

export interface DeviceHealthPanelProps {
  device: Device | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DeviceHealthPanel({
  device,
  isOpen,
  onClose,
}: DeviceHealthPanelProps) {
  // Close on ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !device) return null;

  const temp = device.cpuTempC || 44.5;
  const isTempCritical = temp > 80;
  const isTempWarning = temp > 65;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-in Sheet Panel */}
      <div className="relative z-10 w-full max-w-2xl bg-slate-900 border-l border-scada-border shadow-2xl flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200">
        {/* 1. Header */}
        <div className="p-4 border-b border-scada-border flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <span
              className={`h-3 w-3 rounded-full ${
                device.status === "recording" || device.status === "online"
                  ? "bg-emerald-400 animate-pulse"
                  : device.status === "error"
                  ? "bg-red-400"
                  : "bg-amber-400"
              }`}
            />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-mono font-bold text-white text-base">
                  {device.deviceName}
                </h3>
                <span className="badge-cyan text-[10px]">{device.deviceId}</span>
              </div>
              <p className="text-[11px] font-mono text-scada-muted">
                {device.hardwareVersion} · FW: {device.firmwareVersion}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-control text-scada-muted hover:text-white hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. Scrollable Body: 2x3 Diagnostics Grid */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
          {/* Subsystems 2x3 Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* 1. Optics & Vision Subsystem */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-cyan-400">
                  <Camera size={15} />
                  <span>Optical Sensor Pipeline</span>
                </div>
                <span className="badge-green text-[9px]">ACTIVE</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-scada-muted">Camera Model:</span>
                  <span className="text-white">{device.cameraModel || "Sony IMX477 12.3MP HQ"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Acquisition Rate:</span>
                  <span className="text-emerald-400 font-bold">59.8 FPS @ 1080p</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Lens Heating:</span>
                  <span className="text-cyan-400">ON (De-icing 24W)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Shutter Exposure:</span>
                  <span className="text-white">1/2000s (Anti-blur)</span>
                </div>
              </div>
            </div>

            {/* 2. Inertial Navigation & IMU */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-emerald-400">
                  <Compass size={15} />
                  <span>IMU & Inertial Profiler</span>
                </div>
                <span className="badge-green text-[9px]">CALIBRATED</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-scada-muted">MEMS Sensor:</span>
                  <span className="text-white">{device.imuModel || "TDK ICM-42688-P"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Sampling Frequency:</span>
                  <span className="text-emerald-400 font-bold">1000 Hz</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Gyro Drift Variance:</span>
                  <span className="text-white">±0.02 °/s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Accel Dynamic Range:</span>
                  <span className="text-white">±16g Triaxial</span>
                </div>
              </div>
            </div>

            {/* 3. Positioning & RTK GNSS */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-cyan-400">
                  <Navigation size={15} />
                  <span>GNSS RTK Positioning</span>
                </div>
                <span className="badge-cyan text-[9px]">RTK FIXED</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-scada-muted">Receiver Unit:</span>
                  <span className="text-white">{device.gnssModel || "u-blox ZED-F9P"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Position Fix:</span>
                  <span className="text-cyan-400 font-bold">RTK Fixed (±0.03m)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Constellation Lock:</span>
                  <span className="text-emerald-400">26 Satellites (GPS/GAL)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Differential Age:</span>
                  <span className="text-white">0.8s (NTRIP Stream)</span>
                </div>
              </div>
            </div>

            {/* 4. Edge Compute & SoC Health */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-amber-400">
                  <Cpu size={15} />
                  <span>Compute & Thermal SoC</span>
                </div>
                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold ${
                    isTempCritical ? "badge-red" : isTempWarning ? "badge-amber" : "badge-green"
                  }`}
                >
                  {temp.toFixed(1)}°C
                </span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-scada-muted">CPU Temperature:</span>
                  <span
                    className={`font-bold ${
                      isTempCritical
                        ? "text-red-400"
                        : isTempWarning
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {temp.toFixed(1)}°C {isTempCritical && "(CRITICAL OVERHEAT)"}
                  </span>
                </div>
                {/* Temp Gauge bar */}
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      isTempCritical ? "bg-red-500" : isTempWarning ? "bg-amber-500" : "bg-emerald-500"
                    }`}
                    style={{ width: `${Math.min((temp / 90) * 100, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between pt-1">
                  <span className="text-scada-muted">RAM Utilization:</span>
                  <span className="text-white">3.2 / 8.0 GB (40%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">NVMe Storage:</span>
                  <span className="text-white">28.4 / 64.0 GB (44%)</span>
                </div>
              </div>
            </div>

            {/* 5. Cellular & Telemetry Link */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-emerald-400">
                  <Wifi size={15} />
                  <span>5G Telemetry Backhaul</span>
                </div>
                <span className="badge-green text-[9px]">EXCELLENT</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-scada-muted">Modem Link:</span>
                  <span className="text-white">Quectel RM520N 5G SA</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Signal Strength:</span>
                  <span className="text-emerald-400 font-bold">-68 dBm (RSRP)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">SSE Uplink Latency:</span>
                  <span className="text-cyan-400">18 ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Packet Loss:</span>
                  <span className="text-emerald-400">0.01%</span>
                </div>
              </div>
            </div>

            {/* 6. Power Supply & Bus Voltage */}
            <div className="scada-card p-3.5 border border-scada-border space-y-2">
              <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
                <div className="flex items-center gap-2 font-bold text-cyan-400">
                  <Zap size={15} />
                  <span>Power & Voltage Rails</span>
                </div>
                <span className="badge-green text-[9px]">NOMINAL</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-scada-muted">Input Bus Voltage:</span>
                  <span className="text-emerald-400 font-bold">
                    {(device.batteryVoltageV || 12.4).toFixed(1)}V DC
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Total Power Draw:</span>
                  <span className="text-white">18.4 W</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">5V Logic Rail:</span>
                  <span className="text-emerald-400">5.08V (Stable)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-scada-muted">Supercapacitor Backup:</span>
                  <span className="text-white">100% (Safe Shutdown Ready)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Footer */}
        <div className="p-4 border-t border-scada-border bg-slate-950 flex items-center justify-end">
          <Button variant="outline" size="md" onClick={onClose} className="text-xs">
            Close Diagnostics
          </Button>
        </div>
      </div>
    </div>
  );
}
