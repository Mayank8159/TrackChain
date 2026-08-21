// Reusable React Error Boundary for isolated crash isolation & graceful recovery (tc.v1).

"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "./Button";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled exception:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-red-500/40 bg-slate-900/95 p-6 text-center font-mono shadow-xl flex flex-col items-center justify-center min-h-[220px]">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/15 border border-red-500/30 text-red-400 mb-3">
            <AlertOctagon size={24} />
          </div>

          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            {this.props.fallbackTitle || "Component Telemetry Suspended"}
          </h3>

          <p className="text-xs text-scada-muted mt-1 max-w-md">
            {this.props.fallbackMessage ||
              "An isolated subsystem fault occurred. Remaining control room instruments remain fully operational."}
          </p>

          {this.state.error?.message && (
            <div className="mt-2.5 max-w-md bg-slate-950 px-3 py-1.5 rounded border border-scada-border text-[10px] text-red-400/90 break-words">
              ERR_CODE: {this.state.error.message.slice(0, 120)}
            </div>
          )}

          <div className="mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={this.handleReset}
              className="text-xs font-mono"
            >
              <RotateCcw size={13} className="mr-1.5 text-cyan-400" />
              Reinitialize Module
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
