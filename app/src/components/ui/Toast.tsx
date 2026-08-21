// Transient success/error notification.

"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { cn } from "../../lib/utils";

interface ToastMessage {
  id: string;
  type: "success" | "error" | "info" | "warning";
  title: string;
  description?: string;
}

interface ToastContextType {
  showToast: (toast: Omit<ToastMessage, "id">) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((t: Omit<ToastMessage, "id">) => {
    const id = `toast-${Date.now()}-${++toastCounter}`;
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 p-3.5 rounded-lg border shadow-xl backdrop-blur-md transition-all font-mono text-xs",
              toast.type === "error" && "bg-scada-panel border-scada-red text-scada-red",
              toast.type === "warning" && "bg-scada-panel border-scada-amber text-scada-amber",
              toast.type === "success" && "bg-scada-panel border-scada-green text-scada-green",
              toast.type === "info" && "bg-scada-panel border-scada-cyan text-scada-cyan"
            )}
          >
            <div className="flex-1">
              <div className="font-bold uppercase tracking-wider">{toast.title}</div>
              {toast.description && (
                <div className="mt-1 text-[11px] text-scada-text/80">{toast.description}</div>
              )}
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((item) => item.id !== toast.id))}
              className="text-scada-muted hover:text-scada-text text-sm"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
