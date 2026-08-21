// Small badge for KPI values and severity levels (tc.v1).

import React from "react";
import type { SeverityLevel } from "../../lib/types";
import { getSeverityMeta } from "../../lib/severity";
import { cn } from "../../lib/utils";

interface StatBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  severity?: SeverityLevel | "info" | "success" | "warning" | string;
  children: React.ReactNode;
  className?: string;
  showIcon?: boolean;
}

export function StatBadge({
  severity = "info",
  children,
  className = "",
  showIcon = false,
  ...props
}: StatBadgeProps) {
  const meta = getSeverityMeta(severity);
  const Icon = meta.Icon;

  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border uppercase tracking-wider",
        meta.badgeClass,
        meta.pulse && "animate-pulse",
        className
      )}
      {...props}
    >
      {showIcon && <Icon size={12} className="shrink-0" />}
      {children}
    </span>
  );
}
