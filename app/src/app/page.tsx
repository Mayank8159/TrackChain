// The Operational Dashboard: Network Overview, Route Line Diagram, and Live Feeds (tc.v1).

"use client";

import React, { useState, useEffect } from "react";
import {
  Train,
  AlertTriangle,
  Siren,
  Activity,
  RefreshCw,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import { KPICard } from "@/components/dashboard/KPICard";
import { RouteLineDiagram } from "@/components/dashboard/RouteLineDiagram";
import { LiveAlertsFeed } from "@/components/dashboard/LiveAlertsFeed";
import { RecentDefects } from "@/components/dashboard/RecentDefects";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useDashboardSummary } from "@/hooks/useDashboardSummary";
import { useSessions } from "@/hooks/useSessions";
import { useDefects } from "@/hooks/useDefects";
import { useAlerts } from "@/hooks/useAlerts";
import { useToast } from "@/components/ui/Toast";
import { sseClient } from "@/lib/sse";
import { triggerDemoAlert } from "@/lib/mock-provider";

export default function OperationalDashboard() {
  const [timeRange, setTimeRange] = useState("24h");
  const { data: summary } = useDashboardSummary();
  const { data: sessions = [], refetch: refetchSessions } = useSessions();
  const { defects = [], refetch: refetchDefects } = useDefects();
  const { alerts } = useAlerts();
  const { showToast } = useToast();

  const handleTriggerSimulatedFault = () => {
    const demoAlert = triggerDemoAlert();
    // Broadcast to SSE stream listeners
    (sseClient as any).notifyAlert(demoAlert);
    showToast({
      type: "error",
      title: "CRITICAL IAL FAULT DETECTED",
      description: `Track Twist Exceedance (6.2 mm/m) flagged by EN13848 Engine at Km 21+950!`,
    });
  };

  // Keyboard shortcut Ctrl+Shift+D or Cmd+Shift+D
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        handleTriggerSimulatedFault();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const activeSessionsCount = sessions.filter((s) => s.status === "active").length;
  const criticalAlertsCount = alerts.filter(
    (a) => !a.acknowledged && a.severity === "critical"
  ).length;

  const handleRefresh = () => {
    refetchSessions();
    refetchDefects();
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header & Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-scada-border pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-wider text-scada-text uppercase">
              Network Overview
            </h1>
            <span className="badge-cyan text-[10px] font-mono font-bold">
              DELHI DIVISION (NR)
            </span>
          </div>
          <p className="text-xs font-mono text-scada-muted mt-1">
            Real-time optical defect inference and EN 13848-1 geometry surveillance
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="danger"
            size="md"
            onClick={handleTriggerSimulatedFault}
            title="Inject simulated CRITICAL IAL fault (Shortcut: Ctrl+Shift+D)"
            className="text-xs font-mono font-bold"
          >
            <Zap size={13} className="mr-1.5 fill-current animate-pulse" />
            Simulate Fault
          </Button>

          <div className="w-40">
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              icon={<SlidersHorizontal size={13} />}
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="all">Full Season Run</option>
            </Select>
          </div>

          <Button
            variant="secondary"
            size="md"
            onClick={handleRefresh}
            title="Refresh dashboard telemetry"
          >
            <RefreshCw size={13} className="mr-1.5" />
            Sync
          </Button>
        </div>
      </div>

      {/* 2. Top KPI Metric Cards (4 Grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Sessions */}
        <KPICard
          title="Active Inspection Runs"
          value={activeSessionsCount > 0 ? activeSessionsCount : 1}
          icon={<Train size={18} className="text-blue-400" />}
          subtitle="Car: ITMS-EDGE-01"
          severity="ok"
        />

        {/* Card 2: Defects Today */}
        <KPICard
          title="Defects Flagged"
          value={defects.length || summary?.totalDefects || 5}
          icon={<AlertTriangle size={18} className="text-amber-400" />}
          trend={12}
          trendLabel="vs avg"
          subtitle="Across 140.0 km track"
          severity="medium"
        />

        {/* Card 3: Critical Alerts */}
        <KPICard
          title="Critical Alarms"
          value={criticalAlertsCount}
          icon={<Siren size={18} className="text-red-400" />}
          pulse={criticalAlertsCount > 0}
          severity="critical"
          subtitle={
            criticalAlertsCount > 0
              ? "Immediate Action Limit"
              : "Zero active IAL alarms"
          }
        />

        {/* Card 4: Track Quality Index */}
        <KPICard
          title="Network TQI Score"
          value="88.4"
          icon={<Activity size={18} className="text-emerald-400" />}
          subtitle="RDSO Standard: Category A"
          severity="ok"
        />
      </div>

      {/* 3. Signature Route Line Diagram */}
      <RouteLineDiagram
        defects={defects}
        totalKm={140}
        corridorName="NDLS → AGC Mainline (Down Track · Km 0.0 to 140.0)"
      />

      {/* 4. 2-Column Live Operational Feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Live Alerts */}
        <LiveAlertsFeed />

        {/* Right Column: Recent Defects */}
        <RecentDefects />
      </div>
    </div>
  );
}
