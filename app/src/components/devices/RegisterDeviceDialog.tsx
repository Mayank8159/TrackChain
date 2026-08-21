// Secure Device Registration Dialog with "Show Once" API Key generation (tc.v1).

"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  PlusCircle,
  Key,
  Copy,
  Check,
  AlertTriangle,
  Cpu,
  ShieldCheck,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import type { Device } from "../../lib/types";

export interface RegisterDeviceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onRegister: (device: Device) => void;
}

export function RegisterDeviceDialog({
  isOpen,
  onClose,
  onRegister,
}: RegisterDeviceDialogProps) {
  const [deviceName, setDeviceName] = useState("");
  const [hardwareType, setHardwareType] = useState("Raspberry Pi 5 (8GB) + Sony IMX477");
  const [serialNumber, setSerialNumber] = useState("SN-TC-2026-" + Math.floor(1000 + Math.random() * 9000));
  const [generatedApiKey, setGeneratedApiKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleResetAndClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceName.trim()) return;

    // Generate random 48-char cryptographic API Key
    const randomHex = Array.from(crypto.getRandomValues(new Uint8Array(24)))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    const apiKey = `tc_live_sec_${randomHex}`;

    const newDevice: Device = {
      deviceId: `DEV-EDGE-0${Math.floor(4 + Math.random() * 6)}`,
      deviceName: deviceName.trim(),
      hardwareVersion: hardwareType,
      firmwareVersion: "v1.2.0-prod",
      cameraModel: hardwareType.includes("Jetson") ? "Basler Ace 2 5MP Global Shutter" : "Sony IMX477 12.3MP HQ Camera",
      imuModel: "TDK InvenSense ICM-42688-P",
      gnssModel: "u-blox ZED-F9P RTK GNSS",
      status: "online",
      batteryVoltageV: 12.5,
      cpuTempC: 43.2,
      lastSeenAt: new Date().toISOString(),
    };

    onRegister(newDevice);
    setGeneratedApiKey(apiKey);
  };

  const handleCopy = () => {
    if (generatedApiKey) {
      navigator.clipboard.writeText(generatedApiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleResetAndClose = () => {
    setDeviceName("");
    setGeneratedApiKey(null);
    setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        onClick={handleResetAndClose}
      />

      {/* Modal Card */}
      <div className="relative z-10 w-full max-w-lg rounded-xl border border-scada-border bg-slate-900 shadow-2xl p-6 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-scada-border/60 pb-3 mb-4">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <PlusCircle size={17} className="text-cyan-400" />
            <span>Register Edge Computing Node</span>
          </div>
          <button
            onClick={handleResetAndClose}
            className="text-scada-muted hover:text-white transition"
          >
            <X size={18} />
          </button>
        </div>

        {!generatedApiKey ? (
          /* Step 1: Registration Form */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-scada-muted uppercase font-bold text-[11px]">
                Device Name / Identifier
              </label>
              <Input
                placeholder="e.g. Bogie Scanner 04 (Right Rail)"
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-scada-muted uppercase font-bold text-[11px]">
                Hardware Platform Architecture
              </label>
              <Select
                value={hardwareType}
                onChange={(e) => setHardwareType(e.target.value)}
              >
                <option value="Raspberry Pi 5 (8GB) + Sony IMX477">
                  Raspberry Pi 5 (8GB) + Sony IMX477 (Bogie Scanner)
                </option>
                <option value="NVIDIA Jetson Orin Nano (8GB) + Basler">
                  NVIDIA Jetson Orin Nano (8GB) + Basler (Vision AI Node)
                </option>
                <option value="Raspberry Pi 5 (4GB) + ADIS16488">
                  Raspberry Pi 5 (4GB) + ADIS16488 (Geometry Profiler)
                </option>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-scada-muted uppercase font-bold text-[11px]">
                Hardware Serial Number (MAC / UUID)
              </label>
              <Input
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                required
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-scada-border/60">
              <Button variant="outline" size="md" type="button" onClick={handleResetAndClose}>
                Cancel
              </Button>
              <Button variant="primary" size="md" type="submit" disabled={!deviceName.trim()}>
                Generate Cryptographic API Key
              </Button>
            </div>
          </form>
        ) : (
          /* Step 2: "Show Once" API Key Generation Result */
          <div className="space-y-4 animate-in fade-in duration-200">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm bg-emerald-500/10 p-2.5 rounded border border-emerald-500/30">
              <ShieldCheck size={18} className="shrink-0" />
              <span>Node Successfully Registered in TrackChain Cloud</span>
            </div>

            <div className="space-y-2">
              <label className="text-scada-muted uppercase font-bold text-[11px] flex items-center gap-1.5">
                <Key size={13} className="text-cyan-400" />
                <span>Node Ingestion Secret API Key</span>
              </label>

              <div className="relative">
                <pre className="w-full bg-slate-950 p-3 rounded-lg border border-scada-border text-cyan-400 font-mono text-[11px] break-all select-all">
                  {generatedApiKey}
                </pre>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="absolute top-2 right-2 p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-white border border-scada-border transition flex items-center gap-1 text-[10px]"
                >
                  {copied ? (
                    <>
                      <Check size={12} className="text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Warning Box */}
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 text-amber-400 p-2.5 rounded text-[11px]">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" />
              <p>
                <strong>Security Notice:</strong> This secret key will <strong>NOT</strong> be displayed again. Add it to <code className="text-white">TRACKCHAIN_API_KEY</code> on the physical edge node before deploying to the bogie.
              </p>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="primary" size="md" onClick={handleResetAndClose}>
                Done & Return to Fleet
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
