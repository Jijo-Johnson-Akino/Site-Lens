export function ScanWebsiteCard({
  host,
  href,
}: {
  host?: string;
  href?: string;
}) {
  if (!host || !href) {
    return (
      <div className="rounded-xl border border-border bg-muted/60 px-4 py-3 text-center">
        <p className="text-sm text-muted-foreground">No website URL provided.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-muted/60 px-4 py-3 text-center">
      <p className="font-medium tracking-tight text-foreground">{host}</p>
      <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
        {href}
      </p>
    </div>
  );
}
