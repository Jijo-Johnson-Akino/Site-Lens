"use client";

import { useEffect, useId, useState } from "react";

import { cn } from "@/lib/utils";

export type IssueEvidenceData = {
  title?: string;
  screenshot_url?: string | null;
  screenshot_caption?: string | null;
  snippet?: string | null;
  snippet_language?: string | null;
  snippet_highlight_line?: number | null;
  screenshot_unavailable?: boolean;
  screenshot_unavailable_reason?: string | null;
};

export function captureInProgress(status?: string | null) {
  return status === "pending" || status === "running";
}

export function IssueEvidence({
  issue,
  capturing = false,
  compact = false,
}: {
  issue: IssueEvidenceData;
  capturing?: boolean;
  compact?: boolean;
}) {
  if (issue.screenshot_url) {
    return <IssueScreenshot issue={issue} compact={compact} />;
  }
  if (issue.snippet) {
    return <IssueSnippet issue={issue} />;
  }
  if (issue.screenshot_unavailable) {
    return (
      <p className="text-xs text-muted-foreground">
        {issue.screenshot_unavailable_reason || "Screenshot unavailable for this page"}
      </p>
    );
  }
  if (capturing) {
    return (
      <div
        className={cn("w-full animate-pulse rounded-[10px] bg-muted", compact ? "h-40" : "h-[200px]")}
        aria-hidden="true"
      />
    );
  }
  return null;
}

function IssueScreenshot({ issue, compact }: { issue: IssueEvidenceData; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [zoom, setZoom] = useState(1);
  const alt = issue.screenshot_caption || `Highlighted issue: ${issue.title || "page"}`;

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!open) {
      setZoom(1);
    }
  }, [open]);

  return (
    <figure className="issue-screenshot w-full">
      <div className="relative w-full overflow-hidden rounded-[10px] border border-[#E2E5EA] bg-muted/40 shadow-[0_1px_3px_rgba(15,23,42,0.08)]">
        {!loaded ? <div className={cn("absolute inset-0 animate-pulse bg-muted", compact ? "min-h-40" : "min-h-[180px]")} /> : null}
        <button
          type="button"
          className="block w-full cursor-zoom-in text-left"
          onClick={() => setOpen(true)}
          aria-label="Open screenshot at full size"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- scan captures are API-served WebP, not static assets */}
          <img
            src={issue.screenshot_url || ""}
            alt={alt}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            className={cn("w-full object-contain object-top", compact ? "max-h-52" : "max-h-[320px]")}
          />
        </button>
      </div>
      {issue.screenshot_caption ? (
        <figcaption className="mt-2 text-xs text-muted-foreground">{issue.screenshot_caption}</figcaption>
      ) : null}
      {open ? (
        <div className="issue-lightbox fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4" role="dialog" aria-modal="true" aria-label="Issue screenshot">
          <button
            type="button"
            className="absolute top-4 right-4 rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-slate-900"
            onClick={() => setOpen(false)}
          >
            Close
          </button>
          <div className="absolute top-4 left-4 flex gap-2">
            <button type="button" className="rounded-lg bg-white px-3 py-1.5 text-sm text-slate-900" onClick={() => setZoom((value) => Math.max(1, value - 0.5))}>
              −
            </button>
            <button type="button" className="rounded-lg bg-white px-3 py-1.5 text-sm text-slate-900" onClick={() => setZoom((value) => Math.min(3, value + 0.5))}>
              +
            </button>
          </div>
          <div className="max-h-full max-w-full overflow-auto">
            {/* eslint-disable-next-line @next/next/no-img-element -- lightbox uses the same captured screenshot URL */}
            <img
              src={issue.screenshot_url || ""}
              alt={alt}
              style={{ transform: `scale(${zoom})`, transformOrigin: "center top" }}
              className="max-h-[90vh] max-w-[min(1100px,92vw)] object-contain transition-transform"
            />
          </div>
        </div>
      ) : null}
    </figure>
  );
}

function IssueSnippet({ issue }: { issue: IssueEvidenceData }) {
  const [copied, setCopied] = useState(false);
  const labelId = useId();
  const lines = (issue.snippet || "").split("\n");
  const highlight = issue.snippet_highlight_line && issue.snippet_highlight_line > 0 ? issue.snippet_highlight_line - 1 : -1;

  async function copy() {
    try {
      await navigator.clipboard.writeText(issue.snippet || "");
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="issue-snippet relative overflow-hidden rounded-[10px] border border-[#1f2937] bg-[#0f172a] text-[#e2e8f0] shadow-[0_1px_3px_rgba(15,23,42,0.08)]">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
        <p id={labelId} className="text-[11px] tracking-wide text-slate-400 uppercase">
          {issue.snippet_language || "code"}
        </p>
        <button type="button" className="text-[11px] font-medium text-slate-200 hover:underline" onClick={() => void copy()}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="max-h-56 overflow-auto p-3 font-mono text-[12px] leading-5" aria-labelledby={labelId}>
        {lines.map((line, index) => (
          <span
            key={`${index}-${line.slice(0, 24)}`}
            className={cn("block whitespace-pre-wrap", index === highlight && "bg-[#E11D48]/25")}
          >
            {line || " "}
          </span>
        ))}
      </pre>
    </div>
  );
}
