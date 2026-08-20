// Lists monitoring runs with status, duration, defect counts; links to detail.

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { useSessions } from "@/hooks/useSessions";
import { useExport } from "@/hooks/useExport";
import { formatTimestamp } from "@/lib/format";

export default function SessionsPage() {
  const { data: sessions = [], isLoading } = useSessions();
  const { exportSessionsCSV } = useExport();
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const filtered = sessions.filter((s) => {
    if (filterStatus !== "all" && s.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        <PageHeader
          title="Track Inspection Runs & Monitoring Sessions"
          description="Historical & active inspection runs recorded by edge telemetry acquisition cars"
          breadcrumbs={[{ label: "Sessions" }]}
          actions={
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => exportSessionsCSV(sessions)}
              >
                Export CSV
              </Button>
            </div>
          }
        />

        {/* Sessions Filter & Table */}
        <Card title="Recorded Inspection Missions">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 font-mono text-xs text-scada-muted">
              <span>Filter Status:</span>
              {(["all", "active", "completed"] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setFilterStatus(st)}
                  className={`px-2.5 py-0.5 rounded text-[11px] uppercase transition ${
                    filterStatus === st
                      ? "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan/40"
                      : "text-scada-muted hover:text-scada-text"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Session ID / Run Name</TableHead>
                  <TableHead>Track Section</TableHead>
                  <TableHead>Distance</TableHead>
                  <TableHead>Defects Flagged</TableHead>
                  <TableHead>Start Time</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>
                      <div className="font-bold text-scada-text">{s.name}</div>
                      <div className="text-[10px] text-scada-muted">{s.id}</div>
                    </TableCell>
                    <TableCell>{s.trackSection}</TableCell>
                    <TableCell className="font-mono font-semibold text-scada-cyan">
                      {s.totalDistanceKm.toFixed(1)} km
                    </TableCell>
                    <TableCell>
                      <span
                        className={`font-mono font-bold ${
                          s.defectsCount > 0 ? "text-scada-red" : "text-scada-green"
                        }`}
                      >
                        {s.defectsCount} defects
                      </span>
                    </TableCell>
                    <TableCell className="text-[10px] text-scada-muted">
                      {formatTimestamp(s.startTime)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          s.status === "active" ? "badge-green" : "badge-cyan"
                        }
                      >
                        {s.status.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/sessions/${s.id}`}>
                        <Button variant="primary" size="sm">
                          Inspect Run →
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </main>
    </div>
  );
}
