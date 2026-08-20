// Route-level Suspense fallback shown while a page segment loads.

export default function Loading() {
  return (
    <div className="flex min-h-[60vh] w-full flex-col items-center justify-center gap-4 bg-scada-bg text-scada-text p-6">
      <div className="relative flex h-16 w-16 items-center justify-center">
        <div className="absolute inset-0 rounded-full border-2 border-scada-cyan/20 animate-ping" />
        <div className="h-10 w-10 rounded-full border-2 border-scada-cyan border-t-transparent animate-spin" />
      </div>
      <div className="text-center font-mono">
        <p className="text-xs uppercase tracking-widest text-scada-cyan font-bold">
          Telemetry Link Initializing
        </p>
        <p className="mt-1 text-[10px] text-scada-muted">
          Synchronizing telemetry buffers & ML model registries...
        </p>
      </div>
    </div>
  );
}
