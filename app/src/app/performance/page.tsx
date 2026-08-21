// SOTA Distributed Pipeline Performance Observatory & SRE Latency Workbench (tc.v1).

"use client";

import React, { useState } from "react";
import {
  Activity,
  Gauge,
  Zap,
  Radio,
  Server,
  Layers,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Terminal,
  Cpu,
  RefreshCw,
  Copy,
  Check,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { DataError } from "@/components/ui/DataError";
import { usePerformance } from "@/hooks/usePerformance";
import { useModeStore } from "@/stores/mode-store";
import { useToast } from "@/components/ui/Toast";

export default function PerformanceObservatoryPage() {
  const [windowSeconds, setWindowSeconds] = useState<number>(300);
  const { mode } = useModeStore();
  const { metrics, traces, isError, refetch } = usePerformance(windowSeconds);
  const { showToast } = useToast();
  const [copiedTraceId, setCopiedTraceId] = useState<string | null>(null);

  const handleCopyTrace = (trace: any) => {
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2));
    setCopiedTraceId(trace.trace_id);
    showToast({
      type: "info",
      title: "Trace Copied",
      description: `Copied JSON trace ${trace.trace_id} to clipboard.`,
    });
    setTimeout(() => setCopiedTraceId(null), 2000);
  };

  // Format chart data from last 20 traces
  const chartData = traces.slice(-20).map((t, idx) => {
    const transport = Math.round(t.transport_ms || 25);
    const inference = Math.round(t.inference_ms || 30);
    const delivery = Math.round(t.delivery_ms || 12);
    return {
      name: `#${idx + 1} ${t.node_id.split("-").slice(-2).join("-")}`,
      traceId: t.trace_id,
      nodeId: t.node_id,
      eventType: t.event_type,
      transport_ms: transport,
      inference_ms: inference,
      delivery_ms: delivery,
      total_e2e: transport + inference + delivery,
    };
  });

  const getGradeStyle = (grade: string) => {
    switch (grade) {
      case "A":
        return {
          badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.3)]",
          text: "text-emerald-400",
          desc: "Optimal High-Speed SLA Compliance (E2E < 200ms)",
        };
      case "B":
        return {
          badge: "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.3)]",
          text: "text-cyan-300",
          desc: "Acceptable Ingestion Performance (E2E 200-500ms)",
        };
      case "C":
        return {
          badge: "bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-[0_0_20px_rgba(245,158,11,0.3)]",
          text: "text-amber-300",
          desc: "Degraded Ingestion Telemetry (E2E 500-1000ms)",
        };
      default:
        return {
          badge: "bg-red-500/20 text-red-400 border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.3)]",
          text: "text-red-400",
          desc: "Critical Latency Failure (Exceeds 1000ms SLA)",
        };
    }
  };

  const gradeStyle = getGradeStyle(metrics.composite_grade);

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="Pipeline Performance Observatory"
        description="5-stage distributed latency profiling, real-time edge throughput & Composite Reliability Ratings"
        breadcrumbs={[{ label: "Performance" }]}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-44">
              <Select
                value={windowSeconds.toString()}
                onChange={(e) => setWindowSeconds(parseInt(e.target.value, 10))}
              >
                <option value="60">Window: Last 1 Min</option>
                <option value="300">Window: Last 5 Mins</option>
                <option value="900">Window: Last 15 Mins</option>
                <option value="3600">Window: Last 1 Hour</option>
              </Select>
            </div>

            <Button
              variant="secondary"
              size="md"
              onClick={() => refetch()}
              className="text-xs font-mono font-bold"
            >
              <RefreshCw size={13} className="mr-1.5" />
              Sync Trace
            </Button>
          </div>
        }
      />

      {/* REAL Mode Backend Error */}
      {mode === "REAL" && isError && (
        <DataError
          title="Performance Ingestion Telemetry Offline"
          message="Failed to retrieve latency traces and throughput metrics from the backend /api/dashboard/performance endpoint."
          onRetry={() => refetch()}
        />
      )}

      {/* 2. Segment 1: Hero Metrics Row (4 Grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        {/* Card 1: Composite Grade */}
        <div className="scada-card p-5 border border-scada-border flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[11px] text-scada-muted uppercase font-bold tracking-wider">
              Composite Reliability
            </span>
            <div className="flex items-baseline gap-2">
              <span className={`text-5xl font-black ${gradeStyle.text}`}>
                {metrics.composite_grade}
              </span>
              <span className="text-sm text-scada-muted font-bold">
                {metrics.composite_score.toFixed(1)} / 100
              </span>
            </div>
            <p className="text-[10px] text-scada-muted truncate max-w-[160px] mt-0.5">
              {gradeStyle.desc}
            </p>
          </div>

          <div
            className={`flex h-16 w-16 items-center justify-center rounded-2xl border text-3xl font-black ${gradeStyle.badge}`}
          >
            {metrics.composite_grade}
          </div>
        </div>

        {/* Card 2: Throughput EPS */}
        <div className="scada-card p-5 border border-scada-border space-y-1">
          <span className="text-[11px] text-scada-muted uppercase font-bold tracking-wider">
            Inbound Throughput
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">
              {metrics.throughput_eps.toFixed(1)}
            </span>
            <span className="text-xs text-cyan-400 font-bold">EPS</span>
          </div>
          <p className="text-[10px] text-scada-muted mt-1">
            {metrics.total_events} events processed in window
          </p>
        </div>

        {/* Card 3: Avg E2E Latency */}
        <div className="scada-card p-5 border border-scada-border space-y-1">
          <span className="text-[11px] text-scada-muted uppercase font-bold tracking-wider">
            Mean E2E Latency
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">
              {metrics.avg_e2e_ms.toFixed(1)}
            </span>
            <span className="text-xs text-scada-muted">ms</span>
          </div>
          <p className="text-[10px] text-scada-muted mt-1">
            Trans {metrics.avg_transport_ms}ms · Inf {metrics.avg_inference_ms}ms · Push {metrics.avg_delivery_ms}ms
          </p>
        </div>

        {/* Card 4: P95 E2E Latency */}
        <div className="scada-card p-5 border border-scada-border space-y-1">
          <span className="text-[11px] text-scada-muted uppercase font-bold tracking-wider">
            95th Percentile (P95)
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-3xl font-bold ${
                metrics.p95_e2e_ms > 500
                  ? "text-red-400"
                  : metrics.p95_e2e_ms > 250
                  ? "text-amber-400"
                  : "text-cyan-400"
              }`}
            >
              {metrics.p95_e2e_ms.toFixed(1)}
            </span>
            <span className="text-xs text-scada-muted">ms</span>
          </div>
          <p className="text-[10px] text-scada-muted mt-1">
            SLA Threshold Limit: &lt; 500.0 ms
          </p>
        </div>
      </div>

      {/* 3. Segment 2: The Waterfall Latency Chart (Recharts) */}
      <Card
        title="5-Stage Distributed Latency Waterfall (Last 20 Packets)"
        badge={
          <span className="badge-cyan text-[10px] flex items-center gap-1">
            <Layers size={10} />
            STACKED LATENCY DELTAS
          </span>
        }
      >
        <div className="h-80 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "monospace" }}
                interval={0}
                angle={-25}
                textAnchor="end"
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 10, fontFamily: "monospace" }}
                unit="ms"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#020617",
                  borderColor: "#334155",
                  borderRadius: "8px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                }}
                formatter={(value: any, name: any) => [
                  `${value} ms`,
                  name === "transport_ms"
                    ? "Transport (Edge → Gateway)"
                    : name === "inference_ms"
                    ? "Inference (AI / Physics)"
                    : "Delivery (SSE Push)",
                ]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                wrapperStyle={{
                  fontSize: "11px",
                  fontFamily: "monospace",
                  paddingBottom: "10px",
                }}
              />
              {/* Reference SLA Threshold line at 500ms */}
              <ReferenceLine
                y={500}
                stroke="#ef4444"
                strokeDasharray="4 4"
                label={{
                  value: "SLA THRESHOLD (500ms)",
                  fill: "#ef4444",
                  fontSize: 10,
                  fontFamily: "monospace",
                  position: "top",
                }}
              />

              {/* Stacked Bars */}
              <Bar dataKey="transport_ms" name="Transport (4G/WiFi)" stackId="a" fill="#38bdf8" radius={[0, 0, 0, 0]} />
              <Bar dataKey="inference_ms" name="Inference (YOLO/Physics)" stackId="a" fill="#fbbf24" radius={[0, 0, 0, 0]} />
              <Bar dataKey="delivery_ms" name="Delivery (SSE Push)" stackId="a" fill="#34d399" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 4. Segment 3: Node Fleet Latency Leaderboard (Table) */}
      <Card
        title="Edge Fleet Ingestion Leaderboard & Health Profiles"
        badge={
          <span className="badge-green text-[10px] flex items-center gap-1">
            <Radio size={10} />
            NODE FLEET METRICS
          </span>
        }
      >
        <div className="relative w-full overflow-x-auto touch-pan-x overscroll-contain">
          <div className="min-w-[850px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Node ID & Identifier</TableHead>
                  <TableHead>Hardware & Backhaul Profile</TableHead>
                  <TableHead>Total Traces (5m)</TableHead>
                  <TableHead>Avg Transport</TableHead>
                  <TableHead>Avg Inference</TableHead>
                  <TableHead>Avg E2E</TableHead>
                  <TableHead>P95 E2E</TableHead>
                  <TableHead className="text-right">SLA Health</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {metrics.node_summaries.map((node) => (
                  <TableRow key={node.node_id}>
                    <TableCell>
                      <div className="flex items-center gap-2 font-mono">
                        <span
                          className={`h-2 w-2 rounded-full ${
                            node.status === "optimal"
                              ? "bg-emerald-400"
                              : node.status === "warning"
                              ? "bg-amber-400"
                              : "bg-red-400"
                          }`}
                        />
                        <span className="font-bold text-white">{node.node_id}</span>
                      </div>
                    </TableCell>

                    <TableCell className="text-xs text-scada-muted font-mono">
                      {node.hardware_type || "Edge Node"}
                    </TableCell>

                    <TableCell className="text-xs font-mono text-cyan-300 font-bold">
                      {node.total_events}
                    </TableCell>

                    <TableCell className="text-xs font-mono text-white">
                      {node.avg_transport_ms} ms
                    </TableCell>

                    <TableCell className="text-xs font-mono text-white">
                      {node.avg_inference_ms} ms
                    </TableCell>

                    <TableCell className="text-xs font-mono text-emerald-400 font-bold">
                      {node.avg_e2e_ms} ms
                    </TableCell>

                    <TableCell className="text-xs font-mono text-amber-400 font-bold">
                      {node.p95_e2e_ms} ms
                    </TableCell>

                    <TableCell className="text-right">
                      <span
                        className={
                          node.status === "optimal"
                            ? "badge-green text-[10px]"
                            : node.status === "warning"
                            ? "badge-amber text-[10px]"
                            : "badge-red text-[10px]"
                        }
                      >
                        {node.status.toUpperCase()}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </Card>

      {/* 5. Segment 4: Live Distributed Trace Console */}
      <Card
        title="Live Distributed Ingestion Trace Stream"
        badge={
          <span className="badge-cyan text-[10px] flex items-center gap-1">
            <Terminal size={10} />
            TRACE AUDIT LOG
          </span>
        }
      >
        <div className="space-y-2 p-1 font-mono text-xs">
          <div className="flex items-center justify-between text-scada-muted pb-2 border-b border-scada-border/60 text-[11px]">
            <span>Recent distributed trace packets (Latest 10 events):</span>
            <span className="text-cyan-400">Epoch Millis Precision</span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {traces.slice(-10).reverse().map((trace) => {
              const e2e = Math.round(trace.e2e_ms || (trace.transport_ms || 25) + (trace.inference_ms || 30) + (trace.delivery_ms || 12));
              const isCopied = copiedTraceId === trace.trace_id;

              return (
                <div
                  key={trace.trace_id}
                  className="flex flex-wrap items-center justify-between gap-3 p-2.5 rounded bg-slate-950 border border-scada-border hover:border-slate-600 transition"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-scada-muted text-[10px]">
                      {new Date(trace.captured_at).toLocaleTimeString("en-IN", { hour12: false })}
                    </span>
                    <span className="font-bold text-white">{trace.node_id}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                        trace.event_type === "DEFECT"
                          ? "bg-red-500/20 text-red-400 border border-red-500/40"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                      }`}
                    >
                      {trace.event_type}
                    </span>
                    <span className="text-scada-muted text-[11px]">
                      Transport: <strong className="text-cyan-300">{Math.round(trace.transport_ms || 25)}ms</strong>
                    </span>
                    <span className="text-scada-muted text-[11px]">
                      Inference: <strong className="text-amber-300">{Math.round(trace.inference_ms || 30)}ms</strong>
                    </span>
                    <span className="text-scada-muted text-[11px]">
                      Delivery: <strong className="text-emerald-300">{Math.round(trace.delivery_ms || 12)}ms</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="font-bold text-emerald-400 text-xs">
                      E2E: {e2e}ms
                    </span>
                    <button
                      onClick={() => handleCopyTrace(trace)}
                      className="p-1 rounded text-scada-muted hover:text-white hover:bg-slate-800 transition"
                      title="Copy JSON Trace"
                    >
                      {isCopied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>
    </div>
  );
}
