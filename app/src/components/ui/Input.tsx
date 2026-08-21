// Mission Control Input primitive for operational parameters and query filters (tc.v1).

import React from "react";
import { cn } from "../../lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", icon, disabled, ...props }, ref) => {
    return (
      <div className="relative flex items-center w-full">
        {icon && (
          <div className="absolute left-3 text-scada-muted pointer-events-none flex items-center">
            {icon}
          </div>
        )}
        <input
          type={type}
          ref={ref}
          disabled={disabled}
          className={cn(
            "w-full rounded-control border border-scada-border bg-slate-900/90 px-3 py-1.5 text-xs font-mono text-scada-text placeholder:text-scada-muted/60 transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent focus-visible:border-scada-accent focus-visible:ring-offset-1 focus-visible:ring-offset-scada-bg",
            "disabled:cursor-not-allowed disabled:opacity-50",
            icon && "pl-9",
            className
          )}
          {...props}
        />
      </div>
    );
  }
);
Input.displayName = "Input";
