// Color-coded severity pill (low/medium/high/critical).

import React from "react";
import { SEVERITY_CONFIG } from "../../lib/constants";
import type { SeverityLevel } from "../../lib/types";
import { cn } from "../../lib/utils";

interface SeverityBadgeProps {
  severity: SeverityLevel;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border",
        config.badgeClass,
        className
      )}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: config.color }}
      />
      {config.label.toUpperCase()}
    </span>
  );
}
