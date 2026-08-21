// Accessible SeverityBadge adhering strictly to Icon + Color + Text hierarchy (tc.v1).

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

export function SeverityBadge({
  severity,
  labelOverride,
  size = "md",
  showIcon = true,
  className,
  ...props
}: SeverityBadgeProps) {
  const meta = getSeverityMeta(severity);
  const Icon = meta.Icon;

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
        meta.pulse && "animate-pulse",
        sizeStyles,
        className
      )}
      {...props}
    >
      {showIcon && <Icon size={iconSizes} className="shrink-0" />}
      <span>{labelOverride || meta.label}</span>
    </span>
  );
}
