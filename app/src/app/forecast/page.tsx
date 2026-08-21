// Oracle: Predictive Maintenance & Degradation Forecasting — /forecast route (tc.oracle.v1).

"use client";

import React, { useState, useMemo } from "react";
import {
  BrainCircuit,
  ChevronDown,
  Cpu,
  Calendar,
  TrendingDown,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { HorizonChart } from "@/components/forecast/HorizonChart";
import { InterventionSimulator, applyIntervention } from "@/components/forecast/InterventionSimulator";
import { SurvivalSidebar } from "@/components/forecast/SurvivalSidebar";
import { useModeStore } from "@/stores/mode-store";
import { useSessions } from "@/hooks/useSessions";
import { useDefects } from "@/hooks/useDefects";
import { MOCK_TRACK_SEGMENTS, computeSurvivalProbs, findBreachDay } from "@/lib/mock-provider";
import { RDSO_LIMITS, type TrackClass } from "@/lib/rdso-thresholds";

// ─── Track class label map ────────────────────────────────────────────────────

const CLASS_LABELS: Record<TrackClass, string> = {
  CLASS_A: "Class A — High Speed Passenger (≥130 km/h)",
  CLASS_B: "Class B — Mixed Traffic (110 km/h)",
  CLASS_C: "Class C — Heavy Freight (80 km/h)",
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function ForecastPage() {
  const { mode } = useModeStore();
  const { data: realSessions = [] } = useSessions();
  const { defects = [] } = useDefects();

  const availableSegments = useMemo(() => {
    if (mode !== "REAL" || realSessions.length === 0) {
      return MOCK_TRACK_SEGMENTS;
    }
    return realSessions.map((s, idx) => {
      const sessionDefects = defects.filter((d) => d.sessionId === s.id);
      const criticalCount = sessionDefects.filter((d) => d.severity === "critical").length;
      const currentTqi = Math.max(62.0, Math.min(96.0, 92.0 - sessionDefects.length * 3.0 - criticalCount * 5.0));
      const mockTemplate = MOCK_TRACK_SEGMENTS[idx % MOCK_TRACK_SEGMENTS.length];

      const forecast = mockTemplate.forecast.map((pt) => {
        if (pt.day <= 0) {
          const delta = pt.day * 0.05;
          return { ...pt, tqi_actual: Math.max(50, Math.min(100, currentTqi - delta)) };
        } else {
          const deg = pt.day * (0.12 + criticalCount * 0.05);
          const predicted = Math.max(45, currentTqi - deg);
          return {
            ...pt,
            tqi_predicted: predicted,
            lower_bound_95: Math.max(35, predicted - 4.5),
            upper_bound_95: Math.min(100, predicted + 4.5),
            lower_bound_80: Math.max(38, predicted - 2.8),
            upper_bound_80: Math.min(100, predicted + 2.8),
          };
        }
      });

      return {
        id: s.id,
        label: `${s.trackSection || s.name || s.id}`,
        trackClass: (idx === 0 ? "CLASS_A" : idx === 1 ? "CLASS_B" : "CLASS_C") as TrackClass,
        currentTqi,
        breachDayEstimate: findBreachDay(forecast, 70),
        survivalProbs: computeSurvivalProbs(forecast, 70),
        forecast,
      };
    });
  }, [mode, realSessions, defects]);

  // Segment selector
  const [selectedSegmentId, setSelectedSegmentId] = useState(availableSegments[0]?.id || "seg-01");

  // Track class override (user can change from segment default)
  const [trackClass, setTrackClass] = useState<TrackClass>(
    availableSegments[0]?.trackClass || "CLASS_A"
  );

  // What-If intervention state
  const [interventionActive, setInterventionActive] = useState(false);
  const [interventionDay, setInterventionDay] = useState(20);

  // ── Derived data ──────────────────────────────────────────────────────────
  const baseSegment = useMemo(
    () => availableSegments.find((s) => s.id === selectedSegmentId) ?? availableSegments[0] ?? MOCK_TRACK_SEGMENTS[0],
    [availableSegments, selectedSegmentId]
  );

  const rdsoLimit = RDSO_LIMITS[trackClass];

  // If user changed track class, recompute survival probs and breach day
  const survivalProbs = useMemo(
    () => computeSurvivalProbs(baseSegment.forecast, rdsoLimit.tqi_critical),
    [baseSegment.forecast, rdsoLimit.tqi_critical]
  );

  const breachDayEstimate = useMemo(
    () => findBreachDay(baseSegment.forecast, rdsoLimit.tqi_critical),
    [baseSegment.forecast, rdsoLimit.tqi_critical]
  );

  // Apply intervention to get chart data
  const chartForecast = useMemo(
    () =>
      interventionActive
        ? applyIntervention(baseSegment.forecast, interventionDay)
        : baseSegment.forecast,
    [baseSegment.forecast, interventionActive, interventionDay]
  );

  // When segment changes, reset the track class to the segment default
  const handleSegmentChange = (id: string) => {
    setSelectedSegmentId(id);
    const seg = MOCK_TRACK_SEGMENTS.find((s) => s.id === id);
    if (seg) setTrackClass(seg.trackClass);
    setInterventionActive(false);
  };

  // ── Breach date string ────────────────────────────────────────────────────
  const breachDateStr = useMemo(() => {
    if (breachDayEstimate === null) return "No breach predicted";
    const date = new Date(Date.now() + breachDayEstimate * 86_400_000);
    return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  }, [breachDayEstimate]);

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">

      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-control bg-violet-500/15 border border-violet-500/30 text-violet-400 shadow-[0_0_10px_rgba(139,92,246,0.20)]">
              <BrainCircuit size={16} strokeWidth={1.5} />
            </div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-slate-200 uppercase">
              Oracle: Predictive Maintenance
            </h1>
          </div>
          <p className="text-xs font-mono text-slate-500 mt-1 ml-11">
            Degradation forecasting with conformal prediction intervals and RDSO threshold analysis
          </p>
        </div>

        {/* Selectors */}
        <div className="flex flex-wrap items-center gap-2.5 ml-11 sm:ml-0">
          {/* Segment selector */}
          <div className="w-52">
            <Select
              value={selectedSegmentId}
              onChange={(e) => handleSegmentChange(e.target.value)}
              icon={<Cpu size={13} strokeWidth={1.5} />}
            >
              {availableSegments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Track class selector */}
          <div className="w-60">
            <Select
              value={trackClass}
              onChange={(e) => setTrackClass(e.target.value as TrackClass)}
              icon={<ChevronDown size={13} strokeWidth={1.5} />}
            >
              {(Object.keys(RDSO_LIMITS) as TrackClass[]).map((c) => (
                <option key={c} value={c}>
                  {CLASS_LABELS[c]}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      {/* ── KPI Strip ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Current TQI */}
        <div className="glass-card px-4 py-3 flex flex-col gap-1">
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-500">Current TQI</span>
          <span className="text-2xl font-mono font-bold text-white tabular-nums">
            {baseSegment.currentTqi.toFixed(1)}
          </span>
          <span className="text-[10px] font-mono text-slate-500">{rdsoLimit.label.split("—")[0].trim()}</span>
        </div>

        {/* RDSO Critical Limit */}
        <div className="glass-card px-4 py-3 flex flex-col gap-1">
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-500">RDSO Critical</span>
          <span className="text-2xl font-mono font-bold text-red-400 tabular-nums">
            {rdsoLimit.tqi_critical}
          </span>
          <span className="text-[10px] font-mono text-slate-500">{rdsoLimit.speed_kmh} km/h corridor</span>
        </div>

        {/* Predicted Breach */}
        <div className="glass-card px-4 py-3 flex flex-col gap-1 border border-amber-500/20">
          <span className="text-[9px] font-mono uppercase tracking-widest text-amber-500/70">Predicted Breach</span>
          <span className="text-base font-mono font-bold text-amber-300 tabular-nums leading-tight">
            {breachDateStr}
          </span>
          {breachDayEstimate !== null && (
            <span className="text-[10px] font-mono text-amber-500/70">Day +{breachDayEstimate}</span>
          )}
        </div>

        {/* 30-Day Survival */}
        <div className="glass-card px-4 py-3 flex flex-col gap-1">
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-500">30-Day Survival</span>
          <span
            className={`text-2xl font-mono font-bold tabular-nums ${
              (survivalProbs[0]?.probability ?? 1) >= 0.8
                ? "text-emerald-400"
                : (survivalProbs[0]?.probability ?? 1) >= 0.5
                ? "text-amber-400"
                : "text-red-400"
            }`}
          >
            {Math.round((survivalProbs[0]?.probability ?? 1) * 100)}%
          </span>
          <span className="text-[10px] font-mono text-slate-500">probability no breach</span>
        </div>
      </div>

      {/* ── Main 2-Column Layout ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left: Horizon Chart + Intervention Simulator */}
        <div className="lg:col-span-2 flex flex-col gap-5">

          <Card title="Degradation Horizon" badge={
            <span className="badge-amber text-[9px]">
              {interventionActive ? "SIMULATION ACTIVE" : "FORECAST MODE"}
            </span>
          }>
            <HorizonChart
              forecast={chartForecast}
              rdsoLimit={rdsoLimit}
              interventionDay={interventionActive ? interventionDay : null}
            />
          </Card>

          <Card title="What-If Intervention Simulator">
            <InterventionSimulator
              baseForecast={baseSegment.forecast}
              thresholdTqi={rdsoLimit.tqi_critical}
              interventionDay={interventionDay}
              onInterventionChange={setInterventionDay}
              isActive={interventionActive}
              onToggle={() => setInterventionActive((v) => !v)}
            />
          </Card>

          {/* Maintenance Gantt — simplified visual */}
          <Card title="Maintenance Task Horizon">
            <div className="flex flex-col gap-2 font-mono text-[11px]">
              {[
                { label: "Visual Inspection", start: 0, span: 15, color: "#06B6D4" },
                { label: "Tamping Gang Dispatch", start: breachDayEstimate ? breachDayEstimate - 7 : 75, span: 8, color: "#F59E0B" },
                { label: "Lining & Levelling", start: breachDayEstimate ? breachDayEstimate - 4 : 83, span: 5, color: "#10B981" },
                { label: "Post-maintenance Survey", start: breachDayEstimate ? breachDayEstimate + 2 : 90, span: 5, color: "#8B5CF6" },
              ].map((task) => (
                <div key={task.label} className="flex items-center gap-3">
                  <span className="w-44 text-slate-500 shrink-0 text-right">{task.label}</span>
                  <div className="flex-1 relative h-5 rounded bg-white/[0.03]">
                    <div
                      className="absolute top-0.5 bottom-0.5 rounded"
                      style={{
                        left: `${(task.start / 90) * 100}%`,
                        width: `${(task.span / 90) * 100}%`,
                        backgroundColor: task.color + "40",
                        border: `1px solid ${task.color}60`,
                      }}
                    />
                  </div>
                  <span className="text-slate-600 w-16 shrink-0">D+{task.start}–{task.start + task.span}</span>
                </div>
              ))}
              <div className="flex items-center gap-3 mt-1">
                <span className="w-44 shrink-0" />
                <div className="flex-1 flex justify-between text-[9px] text-slate-600 px-1">
                  <span>Day 0</span>
                  <span>Day 30</span>
                  <span>Day 60</span>
                  <span>Day 90</span>
                </div>
                <span className="w-16 shrink-0" />
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Survival Probability + Work Orders */}
        <div className="flex flex-col gap-5">
          <Card title="Asset Survival">
            <SurvivalSidebar
              survivalProbs={survivalProbs}
              segmentId={baseSegment.id}
              segmentLabel={baseSegment.label}
              breachDayEstimate={breachDayEstimate}
            />
          </Card>

          {/* Segment Intelligence Summary */}
          <Card title="Segment Intelligence">
            <div className="flex flex-col gap-3 font-mono text-xs">
              {MOCK_TRACK_SEGMENTS.map((s) => {
                const limit = RDSO_LIMITS[s.trackClass];
                const bd = findBreachDay(s.forecast, limit.tqi_critical);
                const isSelected = s.id === selectedSegmentId;
                return (
                  <button
                    key={s.id}
                    onClick={() => handleSegmentChange(s.id)}
                    className={`text-left flex items-start justify-between gap-2 px-3 py-2.5 rounded-control border transition-all ${
                      isSelected
                        ? "bg-cyan-500/10 border-cyan-500/30 text-white"
                        : "bg-white/[0.02] border-white/[0.05] text-slate-400 hover:border-white/10 hover:text-slate-300"
                    }`}
                  >
                    <div className="flex flex-col">
                      <span className="font-bold text-[11px]">{s.label}</span>
                      <span className="text-[10px] text-slate-600">{s.trackClass.replace("_", " ")}</span>
                    </div>
                    <div className="text-right shrink-0">
                      {bd !== null ? (
                        <span className={`text-[11px] font-bold ${bd <= 14 ? "text-red-400" : bd <= 45 ? "text-amber-400" : "text-slate-400"}`}>
                          D+{bd}
                        </span>
                      ) : (
                        <span className="text-[11px] text-emerald-400">Safe</span>
                      )}
                      <div className="text-[9px] text-slate-600">
                        TQI {s.currentTqi.toFixed(1)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
