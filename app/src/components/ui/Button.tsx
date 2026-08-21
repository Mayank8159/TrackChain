// Button with Mission Control variants (primary/secondary/outline/ghost/danger) and loading state (tc.v1).

import React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-mono font-medium rounded-control transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent focus-visible:ring-offset-2 focus-visible:ring-offset-scada-bg disabled:opacity-50 disabled:pointer-events-none select-none";

    const variantStyles = {
      primary:
        "bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white shadow-sm border border-blue-500/50",
      secondary:
        "bg-scada-panel text-scada-text border border-scada-border hover:bg-scada-panel-header hover:border-scada-border-bright active:bg-scada-panel",
      outline:
        "border border-scada-border bg-transparent text-scada-text hover:bg-scada-panel hover:text-white hover:border-scada-border-bright",
      ghost:
        "bg-transparent text-scada-muted hover:text-scada-text hover:bg-scada-panel/60",
      danger:
        "bg-red-600/20 text-red-400 border border-red-500/40 hover:bg-red-600/30 active:bg-red-600/40",
    }[variant];

    const sizeStyles = {
      sm: "px-2.5 py-1 text-[11px] gap-1.5",
      md: "px-3.5 py-1.5 text-xs gap-2",
      lg: "px-4 py-2 text-sm gap-2.5",
    }[size];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variantStyles, sizeStyles, className)}
        {...props}
      >
        {isLoading && (
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent shrink-0" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
