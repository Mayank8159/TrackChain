// Small badge for KPI values and severity levels.

import React from "react";
import type { SeverityLevel } from "../../lib/types";

interface StatBadgeProps {
  severity?: SeverityLevel | "info" | "success";
  children: React.ReactNode;
  className?: string;
}

export function StatBadge({
  severity = "info",
  children,
  className = "",
}: StatBadgeProps) {
  const getBadgeStyle = () => {
    switch (severity) {
      case "critical":
        return "badge-red";
      case "high":
        return "badge-amber";
      case "medium":
        return "bg-amber-500/10 text-amber-300 border-amber-500/30";
      case "low":
        return "badge-cyan";
      case "normal":
      case "success":
        return "badge-green";
      default:
        return "badge-cyan";
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${getBadgeStyle()} ${className}`}
    >
      {children}
    </span>
  );
}
