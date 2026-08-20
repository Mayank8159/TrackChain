// Reusable card container for dashboard panels.

import React from "react";

interface CardProps {
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
}: CardProps) {
  return (
    <div
      className={`scada-card overflow-hidden border border-scada-border transition-all duration-200 hover:border-scada-border-bright ${className}`}
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
