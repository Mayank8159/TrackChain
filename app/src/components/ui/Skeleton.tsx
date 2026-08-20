// Loading placeholder to reduce layout shift.

import React from "react";
import { cn } from "../../lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-scada-panel-header border border-scada-border/40",
        className
      )}
      {...props}
    />
  );
}
