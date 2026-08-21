// Base table primitives for high-density railway telemetry & defect logs (tc.v1).

import React from "react";
import { cn } from "../../lib/utils";

export function Table({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto rounded-card border border-scada-border bg-scada-panel">
      <table
        className={cn("w-full caption-bottom text-left text-xs font-mono", className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn(
        "border-b border-scada-border bg-scada-panel-header text-[10px] font-bold uppercase tracking-wider text-scada-muted select-none",
        className
      )}
      {...props}
    />
  );
}

export function TableBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody
      className={cn("divide-y divide-scada-border/60", className)}
      {...props}
    />
  );
}

export function TableRow({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "transition-colors hover:bg-slate-800/60 focus-visible:bg-slate-800/80",
        className
      )}
      {...props}
    />
  );
}

export function TableHead({
  className,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("p-3 font-semibold text-scada-muted align-middle", className)}
      {...props}
    />
  );
}

export function TableCell({
  className,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("p-3 align-middle text-scada-text font-mono text-xs", className)}
      {...props}
    />
  );
}
