// Edge Computing & Hardware Fleet Monitoring workspace (tc.v1).

"use client";

import React, { useState } from "react";
import {
  Cpu,
  PlusCircle,
  MoreVertical,
  RotateCw,
  Power,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  Activity,
  HardDrive,
  Wifi,
  Zap,
  Camera,
  Compass,
  Navigation,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DeviceHealthPanel } from "@/components/devices/DeviceHealthPanel";
import { RegisterDeviceDialog } from "@/components/devices/RegisterDeviceDialog";
import { useDevices } from "@/hooks/useDevices";
import { useToast } from "@/components/ui/Toast";
import type { Device } from "@/lib/types";

export default function DevicesPage() {
  const { data: initialDevices = [] } = useDevices();
  const [devicesList, setDevicesList] = useState<Device[]>(initialDevices);
  const { showToast } = useToast();

  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [deviceActionsState, setDeviceActionsState] = useState<Record<string, string>>({});

  // Sync if query data loads
  React.useEffect(() => {
    if (initialDevices.length > 0 && devicesList.length === 0) {
      setDevicesList(initialDevices);
    }
  }, [initialDevices, devicesList.length]);

  const devices = devicesList.length > 0 ? devicesList : initialDevices;

  const handleRegisterDevice = (newDevice: Device) => {
    setDevicesList((prev) => [...prev, newDevice]);
    showToast({
      type: "success",
      title: "Edge Node Registered",
      description: `Device ${newDevice.deviceId} (${newDevice.deviceName}) added to fleet registry.`,
    });
  };

  const handleRestartService = (device: Device) => {
    setActiveMenuId(null);
    setDeviceActionsState((prev) => ({ ...prev, [device.deviceId]: "Restarting Pipeline..." }));
    showToast({
      type: "info",
      title: "Service Restart Dispatched",
      description: `Soft-restarting ML ingestion daemon on ${device.deviceId}...`,
    });

    setTimeout(() => {
      setDeviceActionsState((prev) => {
        const next = { ...prev };
        delete next[device.deviceId];
        return next;
      });
      showToast({
        type: "success",
        title: "Service Online",
        description: `ML ingestion daemon active on ${device.deviceId}.`,
      });
    }, 2500);
  };

  const handleRebootNode = (device: Device) => {
    setActiveMenuId(null);
    setDeviceActionsState((prev) => ({ ...prev, [device.deviceId]: "Rebooting Hardware..." }));
    showToast({
      type: "warning",
      title: "System Reboot Initiated",
      description: `Sending SIGTERM & systemctl reboot to ${device.deviceId}...`,
    });

    setTimeout(() => {
      setDeviceActionsState((prev) => {
        const next = { ...prev };
        delete next[device.deviceId];
        return next;
      });
      showToast({
        type: "success",
        title: "Node Reconnected",
        description: `${device.deviceId} finished reboot cycle and re-established RTK lock.`,
      });
    }, 3500);
  };

  const handleOTAUpdate = (device: Device) => {
    setActiveMenuId(null);
    setDeviceActionsState((prev) => ({ ...prev, [device.deviceId]: "Flashing Firmware v2.5.0..." }));
    showToast({
      type: "info",
      title: "OTA Update Dispatched",
      description: `Pushing signed A/B partition firmware package to ${device.deviceId}...`,
    });

    setTimeout(() => {
      setDeviceActionsState((prev) => {
        const next = { ...prev };
        delete next[device.deviceId];
        return next;
      });
      setDevicesList((prev) =>
        prev.map((d) =>
          d.deviceId === device.deviceId ? { ...d, firmwareVersion: "v2.5.0-prod" } : d
        )
      );
      showToast({
        type: "success",
        title: "Firmware Updated",
        description: `${device.deviceId} is now running firmware v2.5.0-prod.`,
      });
    }, 3500);
  };

  const totalNodes = devices.length;
  const onlineNodes = devices.filter((d) => d.status === "online" || d.status === "recording").length;
  const avgTemp = (
    devices.reduce((acc, d) => acc + (d.cpuTempC || 44), 0) / (devices.length || 1)
  ).toFixed(1);

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="Edge Computing & Hardware Fleet Monitoring"
        description="Real-time telemetry, thermal profiling, and remote command orchestration for vehicle-mounted edge nodes"
        breadcrumbs={[{ label: "Devices" }]}
        actions={
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsRegisterOpen(true)}
            className="text-xs font-mono font-bold"
          >
            <PlusCircle size={14} className="mr-1.5" />
            Register New Device
          </Button>
        }
      />

      {/* 2. Fleet Overview KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-bold uppercase text-scada-muted">
            Fleet Hardware Nodes
          </h4>
          <p className="text-2xl font-bold text-white mt-1">
            {totalNodes} <span className="text-xs text-scada-muted">deployed</span>
          </p>
          <p className="text-[10px] text-scada-muted mt-1">
            Northern Railway Carriages
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-bold uppercase text-scada-muted">
            Operational Fleet Health
          </h4>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            {((onlineNodes / (totalNodes || 1)) * 100).toFixed(0)}% <span className="text-xs text-scada-muted">online</span>
          </p>
          <p className="text-[10px] text-scada-muted mt-1">
            {onlineNodes} of {totalNodes} reporting telemetry
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-bold uppercase text-scada-muted">
            Average CPU Temperature
          </h4>
          <p className="text-2xl font-bold text-cyan-400 mt-1">
            {avgTemp}°C <span className="text-xs text-scada-muted">nominal</span>
          </p>
          <p className="text-[10px] text-scada-muted mt-1">
            Threshold: &lt; 75.0°C Safe
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-bold uppercase text-scada-muted">
            Vision Inference Stream
          </h4>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            59.8 <span className="text-xs text-scada-muted">FPS / Node</span>
          </p>
          <p className="text-[10px] text-scada-muted mt-1">
            Zero Dropped Sensor Frames
          </p>
        </div>
      </div>

      {/* 3. Device Fleet Grid (1 col mobile, 2 col tablet, 3 col desktop) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map((device) => {
          const actionState = deviceActionsState[device.deviceId];
          const temp = device.cpuTempC || 44.5;
          const isTempCritical = temp > 80;
          const isTempWarning = temp > 65;

          return (
            <div
              key={device.deviceId}
              className="relative rounded-xl border border-scada-border bg-slate-900 shadow-xl overflow-hidden flex flex-col justify-between"
            >
              {/* Card Top Section */}
              <div className="p-4 space-y-3 font-mono">
                {/* Header */}
                <div className="flex items-start justify-between gap-2 border-b border-scada-border/60 pb-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          actionState
                            ? "bg-amber-400 animate-spin"
                            : device.status === "recording" || device.status === "online"
                            ? "bg-emerald-400 animate-pulse"
                            : "bg-red-400"
                        }`}
                      />
                      <h3 className="font-bold text-white text-sm">
                        {device.deviceName}
                      </h3>
                    </div>
                    <span className="badge-cyan text-[10px]">{device.deviceId}</span>
                  </div>

                  {/* Options Menu Button */}
                  <div className="relative">
                    <button
                      onClick={() =>
                        setActiveMenuId(activeMenuId === device.deviceId ? null : device.deviceId)
                      }
                      className="p-1 rounded text-scada-muted hover:text-white hover:bg-slate-800 transition"
                    >
                      <MoreVertical size={16} />
                    </button>

                    {/* Dropdown Menu */}
                    {activeMenuId === device.deviceId && (
                      <div className="absolute right-0 top-7 z-30 w-48 rounded-lg border border-scada-border bg-slate-950 p-1.5 shadow-2xl space-y-1 text-xs">
                        <button
                          onClick={() => handleRestartService(device)}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-slate-800 text-slate-200 hover:text-white transition text-left"
                        >
                          <RotateCw size={13} className="text-cyan-400" />
                          Restart Daemon
                        </button>
                        <button
                          onClick={() => handleRebootNode(device)}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-red-950/40 text-red-400 hover:text-red-300 transition text-left"
                        >
                          <Power size={13} />
                          Reboot Hardware
                        </button>
                        <button
                          onClick={() => handleOTAUpdate(device)}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded hover:bg-slate-800 text-emerald-400 hover:text-emerald-300 transition text-left"
                        >
                          <UploadCloud size={13} />
                          Trigger OTA Update
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Simulated In-Flight State Banner */}
                {actionState && (
                  <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 text-amber-400 p-2 rounded text-xs">
                    <RotateCw size={14} className="animate-spin shrink-0" />
                    <span>{actionState}</span>
                  </div>
                )}

                {/* Hardware Architecture Spec */}
                <div className="text-[11px] text-scada-muted">
                  <span className="text-slate-400">Architecture: </span>
                  <span className="text-white">{device.hardwareVersion}</span>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-2.5 rounded-lg border border-scada-border/60 text-[11px]">
                  <div>
                    <span className="text-scada-muted">Firmware:</span>{" "}
                    <span className="text-cyan-400 font-bold">{device.firmwareVersion}</span>
                  </div>
                  <div>
                    <span className="text-scada-muted">Uptime:</span>{" "}
                    <span className="text-white">14d 06h</span>
                  </div>
                  <div>
                    <span className="text-scada-muted">CPU Temp:</span>{" "}
                    <span
                      className={`font-bold ${
                        isTempCritical
                          ? "text-red-400"
                          : isTempWarning
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {temp.toFixed(1)}°C
                    </span>
                  </div>
                  <div>
                    <span className="text-scada-muted">Bus Power:</span>{" "}
                    <span className="text-emerald-400 font-bold">
                      {(device.batteryVoltageV || 12.4).toFixed(1)}V DC
                    </span>
                  </div>
                </div>

                {/* Sensor Subsystem Badges */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="badge-green text-[9px] flex items-center gap-1">
                    <Camera size={10} /> Optics 60FPS
                  </span>
                  <span className="badge-green text-[9px] flex items-center gap-1">
                    <Compass size={10} /> IMU 1kHz
                  </span>
                  <span className="badge-cyan text-[9px] flex items-center gap-1">
                    <Navigation size={10} /> RTK Fixed
                  </span>
                </div>
              </div>

              {/* Card Footer */}
              <div className="p-3 border-t border-scada-border/60 bg-slate-950/80 flex items-center justify-between">
                <span className="text-[10px] font-mono text-scada-muted">
                  Heartbeat: 4s ago
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedDevice(device)}
                  className="text-[11px]"
                >
                  <Activity size={12} className="mr-1 text-cyan-400" />
                  View Diagnostics
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. Slide-In Hardware Diagnostics Panel */}
      <DeviceHealthPanel
        device={selectedDevice}
        isOpen={!!selectedDevice}
        onClose={() => setSelectedDevice(null)}
      />

      {/* 5. Device Registration Modal */}
      <RegisterDeviceDialog
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onRegister={handleRegisterDevice}
      />
    </div>
  );
}
