// Route-level error boundary; catches render errors and offers retry.

"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Route render error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] w-full flex-col items-center justify-center gap-4 bg-scada-bg p-6 text-scada-text">
      <div className="rounded-lg border border-scada-red/40 bg-scada-panel p-6 text-center max-w-md w-full shadow-2xl">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-scada-red/10 text-scada-red text-xl font-mono font-bold">
          !
        </div>
        <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-scada-red">
          System Interface Fault
        </h2>
        <p className="mt-2 text-xs font-mono text-scada-muted leading-relaxed">
          {error.message || "An unexpected error occurred while rendering this view."}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="danger" size="sm" onClick={() => reset()}>
            Retry Segment
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => (window.location.href = "/")}
          >
            Return to Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
