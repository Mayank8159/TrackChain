// Sessions Registry Table with filters, status badges, and lifecycle actions (tc.v1).

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Plus, Search, Filter, Route as RouteIcon, Download, Train } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { SessionStatusBadge } from "@/components/sessions/SessionStatusBadge";
import { DataError } from "@/components/ui/DataError";
import { useModeStore } from "@/stores/mode-store";
import { useSessions } from "@/hooks/useSessions";
import { useExport } from "@/hooks/useExport";
import { useToast } from "@/components/ui/Toast";
import { formatTimestamp, formatSessionDuration } from "@/lib/format";
import type { MonitoringSession } from "@/lib/types";

export default function SessionsPage() {
  const { mode } = useModeStore();
  const { data: initialSessions = [], isError, refetch } = useSessions();
  const [sessionsList, setSessionsList] = useState<MonitoringSession[]>([]);
  const { exportSessionsCSV } = useExport();
  const { showToast } = useToast();

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const sessions = sessionsList.length > 0 ? sessionsList : initialSessions;

  const filteredSessions = sessions.filter((s) => {
    if (statusFilter !== "all") {
      if (statusFilter === "running" && s.status !== "active" && s.status !== "running") return false;
      if (statusFilter === "completed" && s.status !== "completed") return false;
      if (statusFilter === "paused" && s.status !== "paused") return false;
      if (statusFilter === "failed" && s.status !== "failed") return false;
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = s.id.toLowerCase().includes(q);
      const matchName = s.name.toLowerCase().includes(q);
      const matchSection = s.trackSection.toLowerCase().includes(q);
      const matchTrackId = s.trackId.toLowerCase().includes(q);
      if (!matchId && !matchName && !matchSection && !matchTrackId) return false;
    }

    return true;
  });

  const activeCount = sessions.filter((s) => s.status === "active" || s.status === "running").length;
  const totalKm = sessions.reduce((acc, s) => acc + (s.totalDistanceKm || 0), 0);
  const totalDefects = sessions.reduce((acc, s) => acc + (s.defectsCount || 0), 0);

  const handleStartNewInspection = () => {
    const newSessionId = `ses-live-${Date.now().toString().slice(-4)}`;
    const newSession: MonitoringSession = {
      id: newSessionId,
      name: "NDLS-PWL Live Track Diagnostic Run",
      trackId: "IR-NR-01",
      trackSection: "New Delhi to Palwal (Down Main · Km 0.0 to 58.0)",
      startTime: new Date().toISOString(),
      status: "active",
      totalDistanceKm: 58.0,
      defectsCount: 0,
      operatorName: "Chief Track Inspector A. Sharma",
      weather: "Clear / 30°C",
    };

    setSessionsList((prev) => [newSession, ...prev]);
    showToast({
      type: "success",
      title: "Inspection Mission Started",
      description: `Initialized live run ${newSessionId} on NDLS-PWL corridor. Ingestion active.`,
    });
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="Track Inspection Runs & Monitoring Missions"
        description="Historical and active inspection missions recorded by automated edge acquisition units"
        breadcrumbs={[{ label: "Sessions" }]}
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="md"
              onClick={() => exportSessionsCSV(sessions)}
            >
              <Download size={14} className="mr-1.5" />
              Export CSV
            </Button>

            <Button
              variant="primary"
              size="md"
              onClick={handleStartNewInspection}
            >
              <Plus size={14} className="mr-1.5" />
              Start New Inspection
            </Button>
          </div>
        }
      />

      {/* 2. Top Summary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Total Missions
          </h4>
          <p className="text-2xl font-mono font-bold text-white mt-1">
            {sessions.length} <span className="text-xs text-scada-muted">runs</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Historical Registry Log
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Active Runs
          </h4>
          <p className="text-2xl font-mono font-bold text-emerald-400 mt-1">
            {activeCount} <span className="text-xs text-scada-muted">live</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Edge Car Ingesting Telemetry
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Total Track Monitored
          </h4>
          <p className="text-2xl font-mono font-bold text-cyan-400 mt-1">
            {totalKm.toFixed(1)} <span className="text-xs text-scada-muted">km</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Northern & Western Corridors
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Defects Flagged
          </h4>
          <p className="text-2xl font-mono font-bold text-amber-400 mt-1">
            {totalDefects} <span className="text-xs text-scada-muted">anomalies</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            RDSO Verified Defects
          </p>
        </div>
      </div>

      {/* 3. Filters & Search Bar */}
      <Card title="Recorded Inspection Missions">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-control border border-scada-border">
            {/* Search Input */}
            <div className="w-full sm:max-w-md">
              <Input
                placeholder="Search by route, section name, or session ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search size={14} />}
              />
            </div>

            {/* Status Select Filter */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-mono text-scada-muted whitespace-nowrap">
                Status:
              </span>
              <div className="w-44">
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  icon={<Filter size={13} />}
                >
                  <option value="all">All Statuses ({sessions.length})</option>
                  <option value="running">Live / Running ({activeCount})</option>
                  <option value="completed">Completed</option>
                  <option value="paused">Paused</option>
                  <option value="failed">Failed</option>
                </Select>
              </div>
            </div>
          </div>

          {/* REAL Mode Error State */}
          {mode === "REAL" && isError ? (
            <DataError
              title="Sessions Registry Offline"
              message="Failed to fetch active inspection missions from the backend. The server may be unreachable."
              onRetry={() => refetch()}
            />
          ) : (
            /* Sessions Table with Responsive Scroll */
            <div className="relative w-full overflow-x-auto touch-pan-x overscroll-contain">
              <div className="min-w-[850px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Session ID</TableHead>
                    <TableHead>Route & Track Section</TableHead>
                    <TableHead>Edge Unit</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Distance</TableHead>
                    <TableHead>Defects</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSessions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="py-12 text-center text-scada-muted">
                        No inspection runs found for this criteria.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredSessions.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell>
                          <div className="font-bold font-mono text-white">{s.id}</div>
                          <div className="text-[10px] font-mono text-scada-muted truncate max-w-[140px]">
                            {s.trackId}
                          </div>
                        </TableCell>

                        <TableCell>
                          <div className="font-bold text-scada-text">{s.name}</div>
                          <div className="text-[11px] font-mono text-scada-muted">
                            {s.trackSection}
                          </div>
                        </TableCell>

                        <TableCell className="font-mono text-xs text-cyan-400">
                          DEV-EDGE-01
                        </TableCell>

                        <TableCell>
                          <SessionStatusBadge status={s.status} size="sm" />
                        </TableCell>

                        <TableCell className="font-mono font-semibold text-cyan-400">
                          {s.totalDistanceKm ? `${s.totalDistanceKm.toFixed(1)} km` : "—"}
                        </TableCell>

                        <TableCell>
                          <span
                            className={`font-mono font-bold ${
                              s.defectsCount > 0 ? "text-red-400" : "text-emerald-400"
                            }`}
                          >
                            {s.defectsCount} defects
                          </span>
                        </TableCell>

                        <TableCell className="font-mono text-xs text-slate-300">
                          {formatSessionDuration(s.startTime, s.endTime)}
                        </TableCell>

                        <TableCell className="text-[10px] font-mono text-scada-muted">
                          {formatTimestamp(s.startTime)}
                        </TableCell>

                        <TableCell className="text-right">
                          <Link href={`/sessions/${s.id}`}>
                            <Button variant="primary" size="sm">
                              Inspect Run →
                            </Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
          )}
        </div>
      </Card>
    </div>
  );
}
