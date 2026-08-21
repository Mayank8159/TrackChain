// Real-time track geometry gauge indicator with tolerance thresholds (tc.v1).

"use client";

interface GaugeMetricProps {
  label: string;
  unit: string;
  standard: number;
  current: number;
  min: number;
  max: number;
  warnDelta: number;
  critDelta: number;
}

export function GaugeMetric({
  label,
  unit,
  standard,
  current,
  min,
  max,
  warnDelta,
  critDelta,
}: GaugeMetricProps) {
  const val = Number(current.toFixed(1));
  const delta = Math.abs(val - standard);
  const isCrit = delta >= critDelta;
  const isWarn = delta >= warnDelta && !isCrit;

  const pct = Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));

  const statusColor = isCrit
    ? "text-scada-red"
    : isWarn
    ? "text-scada-amber"
    : "text-scada-green";

  const barColor = isCrit
    ? "bg-scada-red"
    : isWarn
    ? "bg-scada-amber"
    : "bg-scada-cyan";

  return (
    <div className="scada-card p-3 border border-scada-border">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-scada-muted font-mono">
          {label}
        </span>
        <span
          className={`text-[10px] font-mono font-semibold ${
            isCrit
              ? "text-scada-red"
              : isWarn
              ? "text-scada-amber"
              : "text-scada-green"
          }`}
        >
          {isCrit ? "CRIT" : isWarn ? "WARN" : "NORM"}
        </span>
      </div>

      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-2xl font-bold font-mono tracking-tight ${statusColor}`}>
          {val}
        </span>
        <span className="text-xs font-mono text-scada-muted">{unit}</span>
        <span className="ml-auto text-[10px] font-mono text-scada-muted">
          Δ {val >= standard ? `+${(val - standard).toFixed(1)}` : (val - standard).toFixed(1)}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-scada-panel border border-scada-border">
        <div
          className={`h-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-1.5 flex justify-between text-[9px] font-mono text-scada-muted">
        <span>{min}{unit}</span>
        <span className="text-scada-muted/80">STD {standard}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}
