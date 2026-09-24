export function HelpHint({ label, children }: { label: string; children: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      {label}
      <abbr
        className="inline-flex size-4 cursor-help items-center justify-center rounded-full border border-border text-[10px] font-medium text-muted-foreground no-underline"
        title={children}
      >
        ?
        <span className="sr-only">{children}</span>
      </abbr>
    </span>
  );
}
