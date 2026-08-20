// Button with variants (primary/secondary/ghost/danger) and loading state.

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
      "inline-flex items-center justify-center font-mono font-medium rounded transition-colors focus:outline-none focus:ring-1 focus:ring-scada-cyan disabled:opacity-50 disabled:pointer-events-none";

    const variantStyles = {
      primary:
        "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan/40 hover:bg-scada-cyan/30 active:bg-scada-cyan/40",
      secondary:
        "bg-scada-panel text-scada-text border border-scada-border hover:bg-scada-panel-header active:bg-scada-panel",
      outline:
        "border border-scada-border text-scada-muted hover:text-scada-text hover:border-scada-border-bright",
      ghost:
        "text-scada-muted hover:text-scada-text hover:bg-scada-panel/60",
      danger:
        "bg-scada-red/20 text-scada-red border border-scada-red/40 hover:bg-scada-red/30 active:bg-scada-red/40",
    }[variant];

    const sizeStyles = {
      sm: "px-2.5 py-1 text-[11px]",
      md: "px-3.5 py-1.5 text-xs",
      lg: "px-4 py-2 text-sm",
    }[size];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variantStyles, sizeStyles, className)}
        {...props}
      >
        {isLoading && (
          <span className="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
