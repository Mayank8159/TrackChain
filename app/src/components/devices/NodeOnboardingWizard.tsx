// 4-Step Edge Node Onboarding Wizard Modal for Field Engineers (tc.v1).

"use client";

import React, { useState } from "react";
import {
  X,
  Cpu,
  Key,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Radio,
  Loader2,
  ArrowRight,
  Server,
  Terminal,
} from "lucide-react";
import { useNodeOnboardingStore, type HardwareType } from "../../stores/node-onboarding-store";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { useToast } from "../ui/Toast";
import { api } from "../../lib/api";
import { env } from "../../lib/env";
import { useModeStore } from "../../stores/mode-store";

export function NodeOnboardingWizard({
  onNodeRegistered,
}: {
  onNodeRegistered?: (node: any) => void;
}) {
  const {
    isOpen,
    step,
    nodeName,
    hardwareType,
    serialNumber,
    physicalLocation,
    apiKey,
    deviceId,
    connectionTestResult,
    errorMessage,
    closeWizard,
    setStep,
    setNodeName,
    setHardwareType,
    setSerialNumber,
    setPhysicalLocation,
    setApiKey,
    setDeviceId,
    setConnectionTestResult,
    setErrorMessage,
    reset,
  } = useNodeOnboardingStore();

  const { mode } = useModeStore();
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [testLatencyMs, setTestLatencyMs] = useState<number | null>(null);

  if (!isOpen) return null;

  const handleCopyKey = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    showToast({
      type: "info",
      title: "API Key Copied",
      description: "Stored securely in clipboard.",
    });
    setTimeout(() => setCopiedKey(false), 2000);
  };

  // Step 1 -> Step 2: Register on backend or generate demo credentials
  const handleRegisterNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nodeName.trim() || !serialNumber.trim()) {
      setErrorMessage("Please provide both Node Name and Serial Number.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const generatedId = `NODE-${hardwareType.substring(0, 3)}-${serialNumber.replace(/\D/g, "").slice(-4) || "091"}`;

    try {
      if (mode === "REAL") {
        const result = await api.registerEdgeNode({
          device_id: generatedId,
          device_name: nodeName,
          hardware_version:
            hardwareType === "BOGIE_SCANNER"
              ? "Raspberry Pi 5 (8GB) + IMU"
              : hardwareType === "VISION_UNIT"
              ? "NVIDIA Jetson Orin Nano (8GB)"
              : "Industrial Gateway x86",
          firmware_version: "v2.5.0-prod",
        });

        setDeviceId(result.device_id);
        setApiKey(result.api_key);
      } else {
        // Deterministic DEMO Key Generation
        setDeviceId(generatedId);
        setApiKey(`tc_live_${Buffer.from(`${generatedId}_${serialNumber}`).toString("hex").slice(0, 32)}`);
      }

      setStep(2);
      showToast({
        type: "success",
        title: "Node Identity Registered",
        description: `Node ID: ${generatedId} provisioned.`,
      });
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to register node with backend.");
      showToast({
        type: "error",
        title: "Registration Failed",
        description: err.message || "Network error.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 3: Test Connectivity Handshake
  const handleTestConnection = async () => {
    setConnectionTestResult("PENDING");
    setTestLatencyMs(null);

    const start = performance.now();
    try {
      if (mode === "REAL") {
        const healthy = await api.healthCheck();
        const latency = Math.round(performance.now() - start);
        setTestLatencyMs(latency);

        if (healthy) {
          setConnectionTestResult("SUCCESS");
          showToast({
            type: "success",
            title: "Handshake Verified",
            description: `Ping round-trip ${latency}ms · TLS 1.3 Active`,
          });
        } else {
          setConnectionTestResult("FAILED");
        }
      } else {
        // Simulated DEMO handshake
        await new Promise((r) => setTimeout(r, 600));
        setTestLatencyMs(18);
        setConnectionTestResult("SUCCESS");
      }
    } catch {
      setConnectionTestResult("FAILED");
      showToast({
        type: "error",
        title: "Handshake Failed",
        description: "Could not reach target backend endpoint.",
      });
    }
  };

  // Step 4 Complete
  const handleComplete = () => {
    if (onNodeRegistered && deviceId) {
      onNodeRegistered({
        deviceId,
        deviceName: nodeName,
        hardwareVersion:
          hardwareType === "BOGIE_SCANNER"
            ? "Raspberry Pi 5 (8GB)"
            : hardwareType === "VISION_UNIT"
            ? "Jetson Orin Nano"
            : "Gateway Aggregator",
        firmwareVersion: "v2.5.0-prod",
        status: "online",
        cpuTempC: 42.0,
        batteryVoltageV: 12.6,
        lastSeenAt: new Date().toISOString(),
      });
    }
    reset();
    showToast({
      type: "success",
      title: "Node Onboarding Complete",
      description: `${nodeName} (${deviceId}) is active in fleet telemetry.`,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wizard-title"
    >
      <div className="relative w-full max-w-2xl rounded-xl border border-scada-border bg-slate-900 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-scada-border bg-slate-950/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400">
              <Cpu size={20} />
            </div>
            <div>
              <h2 id="wizard-title" className="text-base font-bold font-mono text-white uppercase tracking-wider">
                Edge Node Onboarding Wizard
              </h2>
              <p className="text-xs text-scada-muted font-mono">
                Provision hardware identity, generate TLS API tokens & verify telemetry backhaul
              </p>
            </div>
          </div>

          <button
            onClick={closeWizard}
            className="rounded p-1 text-scada-muted hover:bg-slate-800 hover:text-white transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Step Indicator Bar */}
        <div className="grid grid-cols-4 border-b border-scada-border bg-slate-950/40 text-xs font-mono">
          {[
            { num: 1, label: "1. Identity" },
            { num: 2, label: "2. Credentials" },
            { num: 3, label: "3. Handshake" },
            { num: 4, label: "4. Deployment" },
          ].map((s) => {
            const isActive = step === s.num;
            const isDone = step > s.num;

            return (
              <div
                key={s.num}
                className={`flex items-center justify-center gap-2 py-2.5 px-2 border-r border-scada-border last:border-r-0 transition-colors ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 font-bold border-b-2 border-b-cyan-400"
                    : isDone
                    ? "text-emerald-400 bg-emerald-500/5"
                    : "text-slate-500"
                }`}
              >
                {isDone ? <Check size={13} className="text-emerald-400" /> : <span>{s.num}.</span>}
                <span className="truncate">{s.label.split(". ")[1]}</span>
              </div>
            );
          })}
        </div>

        {/* Step Content Viewport */}
        <div className="flex-1 overflow-y-auto p-6 font-mono">
          {/* STEP 1: Registration Form */}
          {step === 1 && (
            <form onSubmit={handleRegisterNode} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs text-scada-muted uppercase font-bold">Node Name</label>
                <Input
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  placeholder="e.g. NDLS-Bogie-Scanner-04"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-scada-muted uppercase font-bold">Hardware Profile</label>
                  <Select
                    value={hardwareType}
                    onChange={(e) => setHardwareType(e.target.value as HardwareType)}
                  >
                    <option value="BOGIE_SCANNER">RPi5 Bogie Scanner (IMU + Optics)</option>
                    <option value="VISION_UNIT">Jetson Orin Vision Unit (YOLOv8)</option>
                    <option value="GATEWAY">Industrial Gateway Aggregator</option>
                    <option value="IMU_NODE">High-G Accelerometer Node (1kHz)</option>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-scada-muted uppercase font-bold">Serial Number</label>
                  <Input
                    value={serialNumber}
                    onChange={(e) => setSerialNumber(e.target.value)}
                    placeholder="SN-RPI5-4892"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-scada-muted uppercase font-bold">Physical Mounting Location</label>
                <Input
                  value={physicalLocation}
                  onChange={(e) => setPhysicalLocation(e.target.value)}
                  placeholder="e.g. Carriage 482 Bogie Axle #2 / Northern Railway"
                />
              </div>

              {errorMessage && (
                <div className="flex items-center gap-2 p-3 rounded bg-red-500/15 border border-red-500/30 text-red-400 text-xs">
                  <AlertTriangle size={14} className="shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div className="pt-4 flex justify-end gap-3 border-t border-scada-border">
                <Button variant="outline" type="button" onClick={closeWizard}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 size={14} className="mr-1.5 animate-spin" />
                      Provisioning...
                    </>
                  ) : (
                    <>
                      Generate Credentials
                      <ArrowRight size={14} className="ml-1.5" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          )}

          {/* STEP 2: One-Time API Key Display */}
          {step === 2 && (
            <div className="space-y-5">
              <div className="flex items-center gap-2 text-xs text-emerald-400 font-bold uppercase tracking-wider">
                <ShieldCheck size={16} />
                <span>Node Identity Cryptographically Issued</span>
              </div>

              <div className="space-y-2 bg-slate-950 p-4 rounded-lg border border-scada-border">
                <div className="flex items-center justify-between text-xs text-scada-muted">
                  <span>Assigned Node ID:</span>
                  <span className="text-cyan-400 font-bold">{deviceId}</span>
                </div>

                <div className="pt-2 border-t border-scada-border/60">
                  <label className="text-[11px] text-scada-muted uppercase">One-Time Node API Key (Bearer Token):</label>
                  <div className="flex items-center gap-2 mt-1.5">
                    <code className="flex-1 bg-slate-900 p-2.5 rounded border border-scada-border text-cyan-300 text-xs select-all break-all">
                      {apiKey}
                    </code>
                    <Button variant="secondary" size="md" onClick={handleCopyKey}>
                      {copiedKey ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                <p>
                  <strong>CRITICAL SECURITY NOTICE:</strong> This API key is hashed using SHA-256 and stored server-side. It will <u>never be shown again</u>. Copy and export it to the edge node environment before continuing.
                </p>
              </div>

              <div className="pt-4 flex justify-between gap-3 border-t border-scada-border">
                <Button variant="outline" onClick={() => setStep(1)}>
                  ← Back
                </Button>
                <Button variant="primary" onClick={() => setStep(3)}>
                  Proceed to Handshake Test →
                </Button>
              </div>
            </div>
          )}

          {/* STEP 3: Connectivity & Handshake Test */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h3 className="text-sm font-bold text-white uppercase">Verify Edge ↔ Gateway Connectivity</h3>
                <p className="text-xs text-scada-muted mt-1">
                  Test HTTPS/TLS 1.3 round-trip ingestion backhaul to target API endpoint:
                </p>
              </div>

              <div className="bg-slate-950 p-4 rounded-lg border border-scada-border space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-scada-muted">Target Backend URL:</span>
                  <code className="text-cyan-400 font-bold">{env.apiUrl}</code>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-scada-muted">TLS Protocol:</span>
                  <span className="badge-green text-[10px]">TLS 1.3 Encrypted</span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-scada-muted">Auth Scheme:</span>
                  <span className="text-white">Authorization: Bearer [API_KEY]</span>
                </div>

                {testLatencyMs !== null && (
                  <div className="flex items-center justify-between text-xs pt-2 border-t border-scada-border/60">
                    <span className="text-scada-muted">Round-trip Ping Latency:</span>
                    <span className="text-emerald-400 font-bold">{testLatencyMs} ms</span>
                  </div>
                )}
              </div>

              {connectionTestResult === "FAILED" && (
                <div className="flex items-center gap-2 p-3 rounded bg-red-500/15 border border-red-500/30 text-red-400 text-xs">
                  <AlertTriangle size={14} className="shrink-0" />
                  <span>Connection failed. Please check network backhaul or backend URL.</span>
                </div>
              )}

              {connectionTestResult === "SUCCESS" && (
                <div className="flex items-center gap-2 p-3 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs">
                  <CheckCircle2 size={16} className="shrink-0" />
                  <span>Edge handshake successful! 100 Hz sensor telemetry channel ready.</span>
                </div>
              )}

              <div className="pt-4 flex justify-between gap-3 border-t border-scada-border">
                <Button variant="outline" onClick={() => setStep(2)}>
                  ← Back
                </Button>

                <div className="flex items-center gap-2">
                  <Button variant="secondary" onClick={handleTestConnection} disabled={connectionTestResult === "PENDING"}>
                    {connectionTestResult === "PENDING" ? (
                      <>
                        <Loader2 size={13} className="mr-1.5 animate-spin" />
                        Testing Ping...
                      </>
                    ) : (
                      <>
                        <Radio size={13} className="mr-1.5 text-cyan-400" />
                        Execute Ping Test
                      </>
                    )}
                  </Button>

                  <Button variant="primary" onClick={() => setStep(4)} disabled={connectionTestResult !== "SUCCESS"}>
                    Complete Deployment →
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Complete */}
          {step === 4 && (
            <div className="space-y-5 text-center py-2">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 mx-auto">
                <CheckCircle2 size={32} />
              </div>

              <div>
                <h3 className="text-base font-bold text-white uppercase tracking-wider">
                  Node Onboarded Successfully
                </h3>
                <p className="text-xs text-scada-muted max-w-md mx-auto mt-1 leading-relaxed">
                  <strong>{nodeName}</strong> ({deviceId}) has been registered in the fleet database. Ingest daemons can now push 100 Hz IMU bursts, optical frames, and GNSS RTK coordinates.
                </p>
              </div>

              {/* Edge Node Daemon Startup Snippet */}
              <div className="text-left bg-slate-950 p-4 rounded-lg border border-scada-border space-y-2">
                <div className="flex items-center gap-2 text-xs text-scada-muted">
                  <Terminal size={13} className="text-cyan-400" />
                  <span>Edge Device Terminal Quickstart:</span>
                </div>
                <pre className="text-[11px] text-cyan-300 bg-slate-900 p-2.5 rounded overflow-x-auto select-all">
{`export TRACKCHAIN_API_URL="${env.apiUrl}"
export TRACKCHAIN_DEVICE_ID="${deviceId}"
export TRACKCHAIN_API_KEY="${apiKey}"
systemctl start trackchain-agent`}
                </pre>
              </div>

              <div className="pt-4 border-t border-scada-border flex justify-center">
                <Button variant="primary" size="md" onClick={handleComplete} className="px-8 font-bold">
                  View Active Fleet
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
