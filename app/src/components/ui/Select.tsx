// Mission Control Select dropdown primitive for filter & parameter selection (tc.v1).

import React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  icon?: React.ReactNode;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, icon, disabled, ...props }, ref) => {
    return (
      <div className="relative flex items-center w-full">
        {icon && (
          <div className="absolute left-3 text-scada-muted pointer-events-none flex items-center">
            {icon}
          </div>
        )}
        <select
          ref={ref}
          disabled={disabled}
          className={cn(
            "w-full appearance-none rounded-control border border-scada-border bg-slate-900/90 px-3 py-1.5 pr-8 text-xs font-mono text-scada-text transition-colors cursor-pointer",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent focus-visible:border-scada-accent focus-visible:ring-offset-1 focus-visible:ring-offset-scada-bg",
            "disabled:cursor-not-allowed disabled:opacity-50",
            icon && "pl-9",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          size={14}
          className="absolute right-2.5 text-scada-muted pointer-events-none"
        />
      </div>
    );
  }
);
Select.displayName = "Select";
