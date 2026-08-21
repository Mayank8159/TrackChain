// Zustand Store for 5-Stage Distributed Pipeline Tracing & Performance Metrics (tc.v1).

import { create } from "zustand";
import type { PipelineTrace, PerformanceMetrics, NodePerformanceSummary } from "../lib/types";
import { MOCK_PIPELINE_TRACES, MOCK_PERFORMANCE_METRICS } from "../lib/mock-provider";

export interface PerformanceState {
  traces: PipelineTrace[];
  windowSeconds: number;
  addTrace: (rawTrace: Omit<PipelineTrace, "delivered_at" | "e2e_ms">) => void;
  setWindowSeconds: (seconds: number) => void;
  getMetrics: () => PerformanceMetrics;
  reset: () => void;
}

export const usePerformanceStore = create<PerformanceState>((set, get) => ({
  traces: MOCK_PIPELINE_TRACES,
  windowSeconds: 300,

  setWindowSeconds: (windowSeconds) => set({ windowSeconds }),

  addTrace: (rawTrace) => {
    const delivered_at = Date.now();
    const captured_at = rawTrace.captured_at || delivered_at - 65;
    const ingested_at = rawTrace.ingested_at || delivered_at - 15;
    const inference_ms = rawTrace.inference_ms || 25.0;

    const transport_ms = Math.max(0, ingested_at - captured_at);
    const delivery_ms = Math.max(0, delivered_at - ingested_at);
    const e2e_ms = Math.max(0, delivered_at - captured_at);

    const completedTrace: PipelineTrace = {
      ...rawTrace,
      captured_at,
      ingested_at,
      inference_ms,
      delivered_at,
      transport_ms,
      delivery_ms,
      e2e_ms,
    };

    set((state) => ({
      traces: [...state.traces.slice(-499), completedTrace],
    }));
  },

  getMetrics: () => {
    const { traces, windowSeconds } = get();
    const cutoff = Date.now() - windowSeconds * 1000;
    const activeTraces = traces.filter((t) => (t.delivered_at || t.ingested_at) >= cutoff);

    if (activeTraces.length === 0) {
      return MOCK_PERFORMANCE_METRICS;
    }

    const total_events = activeTraces.length;
    const throughput_eps = Math.round((total_events / Math.max(1, windowSeconds)) * 100) / 100;

    const transport_times = activeTraces.map((t) => t.transport_ms || 25);
    const inference_times = activeTraces.map((t) => t.inference_ms || 30);
    const delivery_times = activeTraces.map((t) => t.delivery_ms || 12);
    const e2e_times = activeTraces.map((t) => t.e2e_ms || 70).sort((a, b) => a - b);

    const avg_transport_ms =
      Math.round((transport_times.reduce((a, b) => a + b, 0) / total_events) * 10) / 10;
    const avg_inference_ms =
      Math.round((inference_times.reduce((a, b) => a + b, 0) / total_events) * 10) / 10;
    const avg_delivery_ms =
      Math.round((delivery_times.reduce((a, b) => a + b, 0) / total_events) * 10) / 10;
    const avg_e2e_ms =
      Math.round((e2e_times.reduce((a, b) => a + b, 0) / total_events) * 10) / 10;

    const p95_index = Math.min(
      Math.floor(total_events * 0.95),
      total_events - 1
    );
    const p95_e2e_ms = Math.round(e2e_times[p95_index] * 10) / 10;

    // Composite Reliability Score (0 - 100)
    const p95_penalty = Math.min(40, Math.max(0, (p95_e2e_ms - 100) / 15));
    const inference_penalty = Math.min(20, Math.max(0, (avg_inference_ms - 25) / 4));
    const composite_score =
      Math.round(Math.max(10, Math.min(100, 100 - p95_penalty - inference_penalty)) * 10) / 10;

    let composite_grade: "A" | "B" | "C" | "D" | "F" = "A";
    if (composite_score >= 90) composite_grade = "A";
    else if (composite_score >= 75) composite_grade = "B";
    else if (composite_score >= 60) composite_grade = "C";
    else if (composite_score >= 45) composite_grade = "D";
    else composite_grade = "F";

    // Node Summaries
    const nodeMap = new Map<string, PipelineTrace[]>();
    activeTraces.forEach((t) => {
      const list = nodeMap.get(t.node_id) || [];
      list.push(t);
      nodeMap.set(t.node_id, list);
    });

    const node_summaries: NodePerformanceSummary[] = Array.from(nodeMap.entries()).map(
      ([node_id, nTraces]) => {
        const nTrans = nTraces.map((t) => t.transport_ms || 25);
        const nInf = nTraces.map((t) => t.inference_ms || 30);
        const nE2E = nTraces.map((t) => t.e2e_ms || 70).sort((a, b) => a - b);
        const nTotal = nTraces.length;

        const avgNTrans = Math.round((nTrans.reduce((a, b) => a + b, 0) / nTotal) * 10) / 10;
        const avgNInf = Math.round((nInf.reduce((a, b) => a + b, 0) / nTotal) * 10) / 10;
        const avgNE2E = Math.round((nE2E.reduce((a, b) => a + b, 0) / nTotal) * 10) / 10;
        const p95NE2E = Math.round(nE2E[Math.min(Math.floor(nTotal * 0.95), nTotal - 1)] * 10) / 10;

        return {
          node_id,
          hardware_type: node_id.includes("jetson")
            ? "Jetson Orin Nano (4G LTE)"
            : node_id.includes("gateway")
            ? "Industrial Gateway (WAN)"
            : "Raspberry Pi 5 (WiFi)",
          total_events: nTotal,
          avg_transport_ms: avgNTrans,
          avg_inference_ms: avgNInf,
          avg_e2e_ms: avgNE2E,
          p95_e2e_ms: p95NE2E,
          status: p95NE2E < 300 ? "optimal" : p95NE2E < 700 ? "warning" : "critical",
        };
      }
    );

    return {
      window_seconds: windowSeconds,
      total_events,
      throughput_eps,
      avg_transport_ms,
      avg_inference_ms,
      avg_delivery_ms,
      avg_e2e_ms,
      p95_e2e_ms,
      composite_score,
      composite_grade,
      node_summaries,
    };
  },

  reset: () => set({ traces: MOCK_PIPELINE_TRACES }),
}));
