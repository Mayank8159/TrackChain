"use client";

import { Header } from "./Header";
import { FrameViewer } from "./FrameViewer";
import { GaugeMetric } from "./GaugeMetric";
import { AnomalyFeed } from "./AnomalyFeed";
import { StatsBar } from "./StatsBar";

export function ControlRoom() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <div className="glow-line" />

      <div className="flex-1 p-4 lg:p-6">
        <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[1fr_360px] xl:grid-cols-[1fr_400px]">
          {/* Left: Frame viewer + Gauges */}
          <div className="flex flex-col gap-4">
            <FrameViewer />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <GaugeMetric
                label="Track Gauge"
                unit="mm"
                standard={1435}
                current={1436}
                min={1425}
                max={1445}
                warnDelta={5}
                critDelta={10}
              />
              <GaugeMetric
                label="Cant Deficiency"
                unit="mm"
                standard={0}
                current={12}
                min={0}
                max={100}
                warnDelta={40}
                critDelta={75}
              />
              <GaugeMetric
                label="Alignment Dev."
                unit="mm"
                standard={0}
                current={3}
                min={-20}
                max={20}
                warnDelta={8}
                critDelta={15}
              />
            </div>
          </div>

          {/* Right: Anomaly feed */}
          <div className="flex flex-col gap-4">
            <AnomalyFeed />
          </div>
        </div>
      </div>

      <div className="glow-line" />
      <StatsBar />
    </div>
  );
}
