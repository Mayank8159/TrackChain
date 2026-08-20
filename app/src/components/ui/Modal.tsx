// Accessible modal dialog wrapper.

"use client";

import React, { useEffect } from "react";
import { cn } from "../../lib/utils";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  className,
}: ModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
      />

      {/* Modal Container */}
      <div
        className={cn(
          "relative z-10 w-full max-w-2xl rounded-lg border border-scada-border bg-scada-panel p-6 shadow-2xl transition-all",
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-scada-border pb-3 mb-4">
            <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-scada-text">
              {title}
            </h3>
            <button
              onClick={onClose}
              className="text-scada-muted hover:text-scada-text font-mono text-sm px-1.5 py-0.5 rounded transition"
            >
              ✕
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
