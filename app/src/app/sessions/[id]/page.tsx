// Single run: synced telemetry, map trace, defects, and video for one session.

"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { GeometryChart } from "@/components/telemetry/GeometryChart";
import { TrackMap } from "@/components/map/TrackMap";
import { VideoPlayer } from "@/components/video/VideoPlayer";
import { DefectTable } from "@/components/defects/DefectTable";
import { EvidenceModal } from "@/components/video/EvidenceModal";
import { useSession } from "@/hooks/useSession";
import { useTelemetry } from "@/hooks/useTelemetry";
import { useDefects } from "@/hooks/useDefects";
import type { DefectEvent } from "@/lib/types";

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = (params?.id as string) || "";

  const { data: session } = useSession(sessionId);
  const { data: telemetry = [] } = useTelemetry(sessionId, 0);
  const { defects = [] } = useDefects({ sessionId }, 0);

  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(null);
  const [evidenceDefect, setEvidenceDefect] = useState<DefectEvent | null>(null);
  const [videoTime, setVideoTime] = useState<number>(0);

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        <PageHeader
          title={session?.name || `Session ${sessionId}`}
          description={`Track Section: ${session?.trackSection || "Mainline Corridor"}`}
          breadcrumbs={[
            { label: "Sessions", href: "/sessions" },
            { label: sessionId },
          ]}
          actions={
            <div className="flex gap-2">
              <Link href="/reports">
                <Button variant="outline" size="sm">
                  Generate Run Report
                </Button>
              </Link>
            </div>
          }
        />

        {/* Top Grid: Video & GIS Map */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Recorded Optical Video Stream">
            <VideoPlayer
              currentTime={videoTime}
              onTimeUpdate={(t) => setVideoTime(t)}
            />
          </Card>

          <Card title="Corridor GPS Trace">
            <TrackMap
              defects={defects}
              currentChainageM={14000}
              onSelectDefect={(d) => {
                setSelectedDefect(d);
                if (d.videoTimestampSec !== undefined) {
                  setVideoTime(d.videoTimestampSec);
                }
              }}
            />
          </Card>
        </div>

        {/* Telemetry Geometry Chart */}
        <Card title="EN 13848 Track Geometry & Multi-Channel Waveform">
          <GeometryChart data={telemetry} height={200} />
        </Card>

        {/* Defects in this Session */}
        <Card title={`Flagged Defect Events (${defects.length})`}>
          <DefectTable
            defects={defects}
            selectedId={selectedDefect?.id}
            onSelect={(d) => setSelectedDefect(d)}
            onViewEvidence={(d) => setEvidenceDefect(d)}
          />
        </Card>

        {/* Evidence Dialog */}
        <EvidenceModal
          defect={evidenceDefect}
          isOpen={!!evidenceDefect}
          onClose={() => setEvidenceDefect(null)}
        />
      </main>
    </div>
  );
}
