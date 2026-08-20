// Alert center: safety-critical defects with acknowledge workflow.

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SeverityBadge } from "@/components/defects/SeverityBadge";
import { useAlerts } from "@/hooks/useAlerts";
import { useToast } from "@/components/ui/Toast";
import { formatChainage, formatTimestamp } from "@/lib/format";

export default function AlertsPage() {
  const { alerts, acknowledgeAlert } = useAlerts();
  const { showToast } = useToast();
  const [filter, setFilter] = useState<"all" | "unacknowledged" | "acknowledged">(
    "unacknowledged"
  );

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "unacknowledged") return !a.acknowledged;
    if (filter === "acknowledged") return a.acknowledged;
    return true;
  });

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  const handleAcknowledge = (id: string) => {
    acknowledgeAlert(id);
    showToast({
      type: "success",
      title: "Alert Acknowledged",
      description: `Incident ${id} marked acknowledged by operator.`,
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        <PageHeader
          title="Critical Safety Alert Center"
          description="High-priority track defects requiring emergency dispatch or speed restriction"
          breadcrumbs={[{ label: "Alerts" }]}
          actions={
            <div className="flex items-center gap-3">
              {unacknowledgedCount > 0 && (
                <span className="badge-red animate-pulse">
                  {unacknowledgedCount} PENDING ACTION
                </span>
              )}
            </div>
          }
        />

        {/* Filter buttons */}
        <div className="flex gap-2 font-mono text-xs">
          {(["unacknowledged", "all", "acknowledged"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded uppercase font-bold transition ${
                filter === f
                  ? "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan/40"
                  : "bg-scada-panel text-scada-muted border border-scada-border hover:text-scada-text"
              }`}
            >
              {f} ({f === "all" ? alerts.length : alerts.filter((a) => f === "unacknowledged" ? !a.acknowledged : a.acknowledged).length})
            </button>
          ))}
        </div>

        {/* Alert Cards List */}
        <div className="space-y-4 font-mono">
          {filteredAlerts.length === 0 ? (
            <Card>
              <div className="py-12 text-center text-xs text-scada-muted">
                No alerts currently in this category. All clear!
              </div>
            </Card>
          ) : (
            filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-lg border p-4 transition-all ${
                  alert.acknowledged
                    ? "border-scada-border bg-scada-panel opacity-70"
                    : "border-scada-red/60 bg-scada-panel/90 shadow-lg shadow-scada-red/5"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-scada-border pb-3">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={alert.severity} />
                    <span className="text-sm font-bold text-scada-text uppercase">
                      {alert.defectClass.replace("_", " ")}
                    </span>
                    <span className="text-xs text-scada-cyan font-semibold">
                      {formatChainage(alert.chainageM)}
                    </span>
                  </div>
                  <span className="text-[10px] text-scada-muted">
                    {formatTimestamp(alert.timestamp)}
                  </span>
                </div>

                <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <p className="text-xs text-scada-muted leading-relaxed">
                    {alert.message}
                  </p>

                  <div className="flex items-center gap-3 shrink-0">
                    {!alert.acknowledged ? (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleAcknowledge(alert.id)}
                      >
                        Acknowledge Alert
                      </Button>
                    ) : (
                      <span className="text-[10px] text-scada-green flex items-center gap-1">
                        ✓ Ack by {alert.acknowledgedBy || "Operator"}
                      </span>
                    )}

                    <Link href={`/video?seek=0`}>
                      <Button variant="outline" size="sm">
                        View Footage →
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
