export function ReportSkeletons() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading report dashboard">
      <div className="h-36 animate-pulse rounded-xl border border-border bg-card" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-44 animate-pulse rounded-xl border border-border bg-card" />
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="h-64 animate-pulse rounded-xl border border-border bg-card" />
        <div className="h-64 animate-pulse rounded-xl border border-border bg-card" />
      </div>
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
        <div className="h-56 animate-pulse rounded-xl border border-border bg-card" />
        <div className="h-56 animate-pulse rounded-xl border border-border bg-card" />
      </div>
    </div>
  );
}
