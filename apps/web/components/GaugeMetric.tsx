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

function getStatus(
  current: number,
  standard: number,
  warnDelta: number,
  critDelta: number,
): "nominal" | "warning" | "critical" {
  const delta = Math.abs(current - standard);
  if (delta >= critDelta) return "critical";
  if (delta >= warnDelta) return "warning";
  return "nominal";
}

const STATUS_COLORS = {
  nominal: { stroke: "#06d6a0", bg: "bg-scada-cyan/10", text: "text-scada-cyan", badge: "badge-green" },
  warning: { stroke: "#f59e0b", bg: "bg-scada-amber/10", text: "text-scada-amber", badge: "badge-amber" },
  critical: { stroke: "#ef4444", bg: "bg-scada-red/10", text: "text-scada-red", badge: "badge-red" },
};

const RADIUS = 45;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const ARC_LENGTH = CIRCUMFERENCE * 0.75;
const GAP = CIRCUMFERENCE - ARC_LENGTH;

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
  const status = getStatus(current, standard, warnDelta, critDelta);
  const colors = STATUS_COLORS[status];
  const delta = current - standard;
  const deltaSign = delta >= 0 ? "+" : "";

  const range = max - min;
  const normalized = Math.max(0, Math.min(1, (current - min) / range));
  const dashOffset = ARC_LENGTH - ARC_LENGTH * normalized;

  return (
    <div className="glass-panel flex flex-col items-center p-4">
      <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-scada-muted">
        {label}
      </p>

      {/* SVG arc gauge */}
      <div className="relative h-[110px] w-[110px]">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-[125deg]">
          {/* Track */}
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke="#1e293b"
            strokeWidth="6"
            strokeDasharray={`${ARC_LENGTH} ${GAP}`}
            strokeLinecap="round"
          />
          {/* Value */}
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="6"
            strokeDasharray={`${ARC_LENGTH} ${GAP}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-lg font-bold tabular-nums ${colors.text}`}>
            {current}
          </span>
          <span className="text-[9px] text-scada-muted">{unit}</span>
        </div>
      </div>

      {/* Delta + status */}
      <div className="mt-2 flex flex-col items-center gap-1">
        <span className="text-[10px] text-scada-muted">
          Std: {standard} {unit}
        </span>
        <span className={`text-xs font-bold tabular-nums ${colors.text}`}>
          {deltaSign}{delta} {unit}
        </span>
        <span className={colors.badge}>
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              status === "nominal"
                ? "bg-scada-green"
                : status === "warning"
                  ? "bg-scada-amber"
                  : "bg-scada-red animate-pulse"
            }`}
          />
          {status.toUpperCase()}
        </span>
      </div>
    </div>
  );
}
