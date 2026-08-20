// Friendly empty state with icon, title, and call to action.

import React from "react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center rounded-lg border border-dashed border-scada-border bg-scada-panel/40",
        className
      )}
    >
      {icon && <div className="mb-3 text-scada-muted">{icon}</div>}
      <h4 className="text-sm font-mono font-bold uppercase tracking-wider text-scada-text">
        {title}
      </h4>
      {description && (
        <p className="mt-1 max-w-sm text-xs font-mono text-scada-muted">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
