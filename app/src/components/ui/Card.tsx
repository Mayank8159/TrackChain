// Reusable Holographic SCADA card container — glassmorphic surface (tc.holo.v1).

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
        // Glass surface: 60% opacity slate-900, heavy backdrop blur, top-edge highlight
        "glass-card overflow-hidden rounded-card transition-all",
        className
      )}
      {...props}
    >
      {title && (
        <div className="scada-card-header flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-mono">
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
