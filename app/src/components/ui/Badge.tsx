// Generic badge for labels and counts.

import React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "cyan" | "green" | "amber" | "red" | "neutral";
}

export function Badge({
  className,
  variant = "cyan",
  children,
  ...props
}: BadgeProps) {
  const styles = {
    cyan: "badge-cyan",
    green: "badge-green",
    amber: "badge-amber",
    red: "badge-red",
    neutral:
      "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-scada-panel border border-scada-border text-scada-muted",
  }[variant];

  return (
    <span className={cn(styles, className)} {...props}>
      {children}
    </span>
  );
}
