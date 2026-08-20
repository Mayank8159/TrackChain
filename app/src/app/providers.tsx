// Client providers wrapper (TanStack Query, theme, websocket); mounted in layout.tsx.

"use client";

import React, { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../lib/queryClient";
import { realtimeClient } from "../lib/websocket";
import { ToastProvider } from "../components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initiate websocket/realtime stream connection on client mount
    realtimeClient.connect();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
