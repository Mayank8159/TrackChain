// Reusable Mission Control card container for dashboard panels (tc.v1).

import React from "react";
import { cn } from "../../lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Card({
  title,
  badge,
  actions,
  children,
  className = "",
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "scada-card overflow-hidden border border-scada-border bg-scada-panel rounded-card transition-colors hover:border-scada-border-bright",
        className
      )}
      {...props}
    >
      {title && (
        <div className="scada-card-header flex items-center justify-between border-b border-scada-border bg-scada-panel-header px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-scada-text font-mono">
              {title}
            </h3>
            {badge}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
