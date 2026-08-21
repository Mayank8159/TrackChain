// Status badge for inspection missions and sessions (tc.v1).

import React from "react";
import { cn } from "../../lib/utils";

export type SessionStatusType =
  | "active"
  | "running"
  | "completed"
  | "paused"
  | "failed"
  | "error"
  | string;

interface SessionStatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: SessionStatusType;
  size?: "sm" | "md";
}

export function SessionStatusBadge({
  status,
  size = "md",
  className,
  ...props
}: SessionStatusBadgeProps) {
  const norm = (status || "completed").toLowerCase().trim();

  let config = {
    label: "COMPLETED",
    bgClass: "bg-slate-800 text-slate-300 border-slate-700",
    dotClass: "bg-slate-400",
    pulse: false,
  };

  if (norm === "active" || norm === "running") {
    config = {
      label: "LIVE / RUNNING",
      bgClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      dotClass: "bg-emerald-500",
      pulse: true,
    };
  } else if (norm === "paused") {
    config = {
      label: "PAUSED",
      bgClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      dotClass: "bg-amber-500",
      pulse: false,
    };
  } else if (norm === "failed" || norm === "error") {
    config = {
      label: "FAILED",
      bgClass: "bg-red-500/15 text-red-400 border-red-500/40",
      dotClass: "bg-red-500",
      pulse: false,
    };
  }

  const sizeStyles = {
    sm: "px-2 py-0.5 text-[10px] gap-1.5",
    md: "px-2.5 py-0.5 text-xs gap-2",
  }[size];

  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center rounded-full font-mono font-medium border uppercase tracking-wider",
        config.bgClass,
        sizeStyles,
        className
      )}
      {...props}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full shrink-0",
          config.dotClass,
          config.pulse && "animate-ping"
        )}
      />
      <span>{config.label}</span>
    </span>
  );
}
