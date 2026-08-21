// Button with Holographic variants — neon glow primary, glass hover states (tc.holo.v1).

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
      "inline-flex items-center justify-center font-mono font-medium rounded-control transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:opacity-40 disabled:pointer-events-none select-none";

    const variantStyles = {
      // Holographic primary: cyan→blue gradient with neon glow
      primary:
        "bg-gradient-to-r from-cyan-500 to-blue-600 text-white border border-cyan-400/30 shadow-[0_0_15px_rgba(6,182,212,0.30)] hover:shadow-[0_0_22px_rgba(6,182,212,0.50)] hover:brightness-110 active:brightness-95",
      secondary:
        "bg-white/5 text-slate-200 border border-white/10 hover:bg-white/10 hover:border-white/15 active:bg-white/5 backdrop-blur-sm",
      outline:
        "border border-white/10 bg-transparent text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 hover:bg-cyan-500/5",
      ghost:
        "bg-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5",
      danger:
        "bg-red-600/20 text-red-400 border border-red-500/40 hover:bg-red-600/30 hover:shadow-[0_0_12px_rgba(239,68,68,0.25)] active:bg-red-600/40",
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

