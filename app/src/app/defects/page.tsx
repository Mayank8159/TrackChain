// Defect Register & URL-synced triage table with slide-in Evidence Drawer (tc.v1).

"use client";

import React, { useState, useEffect, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Eye,
  SlidersHorizontal,
  Download,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { EvidenceDrawer } from "@/components/defects/EvidenceDrawer";
import { useDefects } from "@/hooks/useDefects";
import { useExport } from "@/hooks/useExport";
import { useToast } from "@/components/ui/Toast";
import { formatChainage, formatTimestamp, formatConfidence } from "@/lib/format";
import type { DefectEvent } from "@/lib/types";

function DefectRegistryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL-synced filter parameters
  const initialSeverity = searchParams?.get("severity") || "all";
  const initialClass = searchParams?.get("class") || "all";
  const initialSource = searchParams?.get("source") || "all";
  const initialSearch = searchParams?.get("q") || "";

  const [severityFilter, setSeverityFilter] = useState<string>(initialSeverity);
  const [classFilter, setClassFilter] = useState<string>(initialClass);
  const [sourceFilter, setSourceFilter] = useState<string>(initialSource);
  const [searchQuery, setSearchQuery] = useState<string>(initialSearch);

  const { defects: initialDefects = [], isDemoData } = useDefects();
  const [defectsList, setDefectsList] = useState<DefectEvent[]>(initialDefects);
  const { exportDefectsCSV } = useExport();
  const { showToast } = useToast();

  const [selectedDrawerDefect, setSelectedDrawerDefect] = useState<DefectEvent | null>(null);
  const [isMutating, setIsMutating] = useState<boolean>(false);

  // Sync defects if query data updates
  useEffect(() => {
    if (initialDefects.length > 0 && defectsList.length === 0) {
      setDefectsList(initialDefects);
    }
  }, [initialDefects, defectsList.length]);

  // Push updated filter state to URL query params
  const updateUrlParams = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams ? searchParams.toString() : "");
    if (value === "all" || !value) {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    router.replace(`/defects?${params.toString()}`, { scroll: false });
  };

  const handleSeverityChange = (val: string) => {
    setSeverityFilter(val);
    updateUrlParams("severity", val);
  };

  const handleClassChange = (val: string) => {
    setClassFilter(val);
    updateUrlParams("class", val);
  };

  const handleSourceChange = (val: string) => {
    setSourceFilter(val);
    updateUrlParams("source", val);
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    updateUrlParams("q", val);
  };

  const defects = defectsList.length > 0 ? defectsList : initialDefects;

  // Filtered defects calculation
  const filteredDefects = useMemo(() => {
    return defects.filter((d) => {
      if (severityFilter !== "all" && d.severity !== severityFilter) return false;
      if (classFilter !== "all" && d.defectClass !== classFilter) return false;
      if (sourceFilter !== "all" && d.streamSource !== sourceFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchId = d.id.toLowerCase().includes(q);
        const matchClass = d.defectClass.toLowerCase().includes(q);
        const matchDesc = d.description?.toLowerCase().includes(q);
        if (!matchId && !matchClass && !matchDesc) return false;
      }
      return true;
    });
  }, [defects, severityFilter, classFilter, sourceFilter, searchQuery]);

  // Human-in-the-loop optimistic mutations
  const handleAcknowledgeDefect = (defect: DefectEvent) => {
    setIsMutating(true);
    setDefectsList((prev) =>
      prev.map((d) =>
        d.id === defect.id
          ? {
              ...d,
              status: "acknowledged",
              acknowledgedBy: "Chief Track Inspector",
              acknowledgedAt: new Date().toISOString(),
            }
          : d
      )
    );
    if (selectedDrawerDefect?.id === defect.id) {
      setSelectedDrawerDefect((prev) =>
        prev
          ? {
              ...prev,
              status: "acknowledged",
              acknowledgedBy: "Chief Track Inspector",
              acknowledgedAt: new Date().toISOString(),
            }
          : null
      );
    }
    setIsMutating(false);
    showToast({
      type: "success",
      title: "Defect Acknowledged",
      description: `Incident ${defect.id} marked as verified & acknowledged by inspector.`,
    });
  };

  const handleRejectDefect = (defect: DefectEvent) => {
    setIsMutating(true);
    setDefectsList((prev) =>
      prev.map((d) =>
        d.id === defect.id ? { ...d, status: "false_positive" } : d
      )
    );
    if (selectedDrawerDefect?.id === defect.id) {
      setSelectedDrawerDefect((prev) =>
        prev ? { ...prev, status: "false_positive" } : null
      );
    }
    setIsMutating(false);
    showToast({
      type: "warning",
      title: "False Positive Dismissed",
      description: `Defect ${defect.id} marked as false positive. Feedback sample queued for model retraining.`,
    });
  };

  const handleAssignCrew = (defect: DefectEvent) => {
    showToast({
      type: "info",
      title: "Maintenance Crew Assigned",
      description: `Dispatched work order to PWL Section Gang #4 for ${formatChainage(defect.chainageM)}.`,
    });
  };

  const criticalCount = defects.filter((d) => d.severity === "critical" && d.status !== "false_positive").length;
  const highCount = defects.filter((d) => d.severity === "high" && d.status !== "false_positive").length;
  const ackCount = defects.filter((d) => d.status === "acknowledged").length;

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="Track Defect Intelligence Register"
        description="High-density triage matrix for optical AI detections and EN 13848 geometry anomalies"
        breadcrumbs={[{ label: "Defects" }]}
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="md"
              onClick={() => exportDefectsCSV(filteredDefects)}
            >
              <Download size={14} className="mr-1.5" />
              Export CSV
            </Button>
          </div>
        }
      />

      {/* 2. Top Summary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Total Flagged Defects
          </h4>
          <p className="text-2xl font-mono font-bold text-white mt-1">
            {defects.length} <span className="text-xs text-scada-muted">items</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Northern Railway Mainline
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Critical Action (IAL)
          </h4>
          <p className="text-2xl font-mono font-bold text-red-400 mt-1">
            {criticalCount} <span className="text-xs text-scada-muted">urgent</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Requires Speed Restriction
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            High Severity
          </h4>
          <p className="text-2xl font-mono font-bold text-amber-400 mt-1">
            {highCount} <span className="text-xs text-scada-muted">faults</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Scheduled Maintenance
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <h4 className="text-xs font-mono font-bold uppercase text-scada-muted">
            Operator Acknowledged
          </h4>
          <p className="text-2xl font-mono font-bold text-emerald-400 mt-1">
            {ackCount} <span className="text-xs text-scada-muted">cleared</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Human-in-the-Loop Verified
          </p>
        </div>
      </div>

      {/* 3. URL-Synced Filter Controls */}
      <Card title="Defect Query & Triage Filters">
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 bg-slate-900/60 p-3 rounded-control border border-scada-border">
            {/* Search Input */}
            <Input
              placeholder="Search by defect ID, keyword, or sleeper..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              icon={<Search size={14} />}
            />

            {/* Severity Multi-Pill Select */}
            <Select
              value={severityFilter}
              onChange={(e) => handleSeverityChange(e.target.value)}
              icon={<Filter size={13} />}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical (IAL)</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>

            {/* Defect Class Dropdown */}
            <Select
              value={classFilter}
              onChange={(e) => handleClassChange(e.target.value)}
            >
              <option value="all">All Defect Classes</option>
              <option value="crack">Crack (Rail Head / Foot)</option>
              <option value="gauge_widening">Gauge Widening</option>
              <option value="missing_fastener">Missing Fastener</option>
              <option value="spalling">Spalling & Wheel Burn</option>
              <option value="twist_exceedance">Twist Exceedance</option>
            </Select>

            {/* Stream Source Dropdown */}
            <Select
              value={sourceFilter}
              onChange={(e) => handleSourceChange(e.target.value)}
            >
              <option value="all">All Source Streams</option>
              <option value="vision">Vision (YOLOv8)</option>
              <option value="geometry">Geometry (IMU/Laser)</option>
              <option value="fused">Fused Vision-Geometry</option>
            </Select>
          </div>

          {/* Quick Active Filters Summary Bar */}
          <div className="flex items-center justify-between text-xs font-mono text-scada-muted px-1">
            <div className="flex items-center gap-2">
              <span>Showing {filteredDefects.length} of {defects.length} defect records</span>
              {(severityFilter !== "all" || classFilter !== "all" || sourceFilter !== "all" || searchQuery) && (
                <button
                  onClick={() => {
                    setSeverityFilter("all");
                    setClassFilter("all");
                    setSourceFilter("all");
                    setSearchQuery("");
                    router.replace("/defects", { scroll: false });
                  }}
                  className="text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
                >
                  <RotateCcw size={12} />
                  Reset Filters
                </button>
              )}
            </div>
            <span>Click any row to open the Investigation Drawer</span>
          </div>

          {/* 4. High-Density Defect Data Table */}
          <div className="relative w-full overflow-x-auto touch-pan-x overscroll-contain">
            <div className="min-w-[900px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Defect ID</TableHead>
                    <TableHead>Chainage (KM)</TableHead>
                    <TableHead>Defect Class</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Source Model</TableHead>
                    <TableHead>Detected At</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDefects.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="py-12 text-center text-scada-muted">
                        No defects matching the selected criteria.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredDefects.map((defect) => {
                      const isAck = defect.status === "acknowledged";
                      const isDism = defect.status === "false_positive";

                      return (
                        <TableRow
                          key={defect.id}
                          onClick={() => setSelectedDrawerDefect(defect)}
                          className={`cursor-pointer transition-colors ${
                            isDism
                              ? "opacity-50 line-through"
                              : isAck
                              ? "bg-emerald-950/10 hover:bg-emerald-950/20"
                              : "hover:bg-slate-800/50"
                          }`}
                        >
                          {/* Defect ID + Checkmark if Acknowledged */}
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {isAck && <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />}
                              {isDism && <XCircle size={14} className="text-red-400 shrink-0" />}
                              <div>
                                <div className="font-mono font-bold text-white">{defect.id}</div>
                                <div className="text-[10px] font-mono text-scada-muted">
                                  {defect.sessionId}
                                </div>
                              </div>
                            </div>
                          </TableCell>

                          {/* Chainage */}
                          <TableCell className="font-mono font-semibold text-cyan-400">
                            {formatChainage(defect.chainageM)}
                          </TableCell>

                          {/* Defect Class */}
                          <TableCell className="uppercase font-mono text-scada-text font-bold">
                            {defect.defectClass.replace("_", " ")}
                          </TableCell>

                          {/* Severity */}
                          <TableCell>
                            <SeverityBadge severity={defect.severity} size="sm" />
                          </TableCell>

                          {/* Confidence */}
                          <TableCell className="font-mono text-emerald-400 font-semibold">
                            {formatConfidence(defect.confidence)}
                          </TableCell>

                          {/* Source Model */}
                          <TableCell className="font-mono text-xs text-slate-300">
                            {defect.sourceModel || "YOLOv8-Detector"}
                          </TableCell>

                          {/* Detected Timestamp */}
                          <TableCell className="text-[10px] font-mono text-scada-muted">
                            {formatTimestamp(defect.timestamp)}
                          </TableCell>

                          {/* Status */}
                          <TableCell>
                            {isDism ? (
                              <span className="badge-red text-[10px]">DISMISSED</span>
                            ) : isAck ? (
                              <span className="badge-green text-[10px]">ACKNOWLEDGED</span>
                            ) : (
                              <span className="badge-cyan text-[10px]">OPEN / UNVERIFIED</span>
                            )}
                          </TableCell>

                          {/* Actions */}
                          <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedDrawerDefect(defect)}
                                className="text-[10px]"
                              >
                                <Eye size={12} className="mr-1" />
                                Inspect
                              </Button>

                              <Link
                                href={`/sessions/${defect.sessionId || "ses-delhi-agra-001"}?seek=${defect.videoTimestampSec || 0}`}
                              >
                                <Button variant="primary" size="sm" className="text-[10px]">
                                  Footage ▶
                                </Button>
                              </Link>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </Card>

      {/* 5. Slide-In Evidence Drawer */}
      <EvidenceDrawer
        defect={selectedDrawerDefect}
        isOpen={!!selectedDrawerDefect}
        onClose={() => setSelectedDrawerDefect(null)}
        onAcknowledge={handleAcknowledgeDefect}
        onReject={handleRejectDefect}
        onAssign={handleAssignCrew}
        isMutating={isMutating}
      />
    </div>
  );
}

export default function DefectsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center font-mono text-scada-muted">Loading Defect Intelligence Registry...</div>}>
      <DefectRegistryContent />
    </Suspense>
  );
}
