// Holographic SeverityBadge — colored glow + CRITICAL animated ring (tc.holo.v1).

"use client";

import React from "react";
import { getSeverityMeta, type CanonicalSeverity } from "../../lib/severity";
import type { SeverityLevel } from "../../lib/types";
import { cn } from "../../lib/utils";

export interface SeverityBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  severity: CanonicalSeverity | SeverityLevel | "info" | "warning" | "success" | string;
  labelOverride?: string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

// Maps severity to a CSS glow color value
const SEVERITY_GLOW: Record<string, string> = {
  ok: "rgba(16, 185, 129, 0.35)",
  low: "rgba(132, 204, 22, 0.35)",
  medium: "rgba(245, 158, 11, 0.40)",
  high: "rgba(249, 115, 22, 0.40)",
  critical: "rgba(239, 68, 68, 0.50)",
};

export function SeverityBadge({
  severity,
  labelOverride,
  size = "md",
  showIcon = true,
  className,
  style,
  ...props
}: SeverityBadgeProps) {
  const meta = getSeverityMeta(severity);
  const Icon = meta.Icon;
  const glowColor = SEVERITY_GLOW[meta.level] ?? "transparent";

  const sizeStyles = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-2.5 py-0.5 text-xs gap-1.5",
    lg: "px-3 py-1 text-sm gap-2 font-bold",
  }[size];

  const iconSizes = {
    sm: 11,
    md: 13,
    lg: 15,
  }[size];

  return (
    <span
      role="status"
      aria-label={`Severity: ${meta.label}`}
      className={cn(
        "inline-flex items-center rounded-full font-mono font-medium border uppercase tracking-wider transition-all",
        meta.badgeClass,
        // CRITICAL: add pulsing ring + stronger glow
        meta.level === "critical" && "ring-1 ring-red-500/60 animate-pulse",
        sizeStyles,
        className
      )}
      style={{
        boxShadow: `0 0 8px ${glowColor}`,
        ...style,
      }}
      {...props}
    >
      {showIcon && <Icon size={iconSizes} className="shrink-0" />}
      <span>{labelOverride || meta.label}</span>
    </span>
  );
}

