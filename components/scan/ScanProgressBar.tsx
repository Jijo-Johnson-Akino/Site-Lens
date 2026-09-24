export function ScanProgressBar({ progress }: { progress: number }) {
  const value = Math.min(100, Math.max(0, Math.round(progress)));

  return (
    <div className="w-full">
      <p className="text-center font-mono text-5xl font-semibold tracking-tight tabular-nums sm:text-6xl">
        {value}
        <span className="text-2xl text-muted-foreground sm:text-3xl">%</span>
      </p>
      <div
        className="mt-6 h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label="Scan progress"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
