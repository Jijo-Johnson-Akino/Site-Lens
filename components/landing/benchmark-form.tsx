"use client";

import { useId, useState, type FormEvent } from "react";
import { useFormStatus } from "react-dom";
import { ArrowRight, CircleAlert, Loader2 } from "lucide-react";

import { startBenchmark } from "@/app/start-scan/actions";
import { CheckItems } from "@/components/landing/check-items";
import { parseWebsiteUrl } from "@/lib/parse-website-url";
import { cn } from "@/lib/utils";

type FormState = { status: "idle" } | { status: "error"; message: string } | { status: "valid" };

const DEFAULT_TRUST = [
  "No credit card required",
  "Crawl and analyze in minutes",
  "Comprehensive website audit",
] as const;

function SubmitButton({ tone }: { tone: "light" | "dark" }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className={cn(
        "inline-flex h-12 w-full shrink-0 items-center justify-center gap-2 rounded-[10px] bg-brand px-5 text-[15px] font-medium text-white transition-colors",
        "hover:bg-[#1d4ed8] focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:outline-none",
        "disabled:pointer-events-none disabled:opacity-60 sm:w-[11.5rem]",
        tone === "dark" && "focus-visible:ring-offset-[#0B1220]",
      )}
    >
      {pending ? (
        <>
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          Starting...
        </>
      ) : (
        <>
          Start Benchmark
          <ArrowRight className="size-4" aria-hidden="true" />
        </>
      )}
    </button>
  );
}

export function BenchmarkForm({
  initialUrl = "",
  initialError = "",
  tone = "light",
  formId = "benchmark",
  trustItems = DEFAULT_TRUST,
}: {
  initialUrl?: string;
  initialError?: string;
  tone?: "light" | "dark";
  formId?: string;
  trustItems?: readonly string[];
}) {
  const inputId = useId();
  const statusId = useId();
  const [value, setValue] = useState(initialUrl);
  const [state, setState] = useState<FormState>(() => {
    if (initialError) return { status: "error", message: initialError };
    return parseWebsiteUrl(initialUrl).ok ? { status: "valid" } : { status: "idle" };
  });

  function validate(nextValue: string, { fromSubmit }: { fromSubmit: boolean }) {
    const parsed = parseWebsiteUrl(nextValue);
    if (parsed.ok) {
      setState({ status: "valid" });
      return parsed;
    }
    if (fromSubmit || nextValue.trim() !== "") {
      setState({ status: "error", message: parsed.message });
    } else {
      setState({ status: "idle" });
    }
    return parsed;
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    const parsed = validate(value, { fromSubmit: true });
    if (!parsed.ok) event.preventDefault();
  }

  return (
    <div className="w-full max-w-[37.5rem]">
      <form id={formId} action={startBenchmark} onSubmit={onSubmit} className="flex scroll-mt-28 flex-col gap-3">
        <label
          htmlFor={inputId}
          className={cn("block text-sm font-medium", tone === "dark" ? "text-slate-200" : "text-ink")}
        >
          Website URL
        </label>
        <div
          className={cn(
            "flex flex-col gap-2 rounded-[14px] p-1.5 sm:flex-row sm:items-center sm:gap-1.5",
            tone === "dark" ? "bg-white" : "border border-border bg-card shadow-landing",
          )}
        >
          <input
            id={inputId}
            name="url"
            type="text"
            inputMode="url"
            autoComplete="url"
            placeholder="https://example.com"
            value={value}
            onChange={(event) => {
              const next = event.target.value;
              setValue(next);
              if (next.trim() === "") {
                setState({ status: "idle" });
                return;
              }
              const parsed = parseWebsiteUrl(next);
              if (parsed.ok) setState({ status: "valid" });
              else if (state.status === "error") setState({ status: "error", message: parsed.message });
            }}
            onBlur={() => {
              if (value.trim() !== "") validate(value, { fromSubmit: false });
            }}
            aria-invalid={state.status === "error"}
            aria-describedby={statusId}
            className={cn(
              "h-12 min-w-0 flex-1 rounded-[10px] border-0 bg-transparent px-3.5 text-base outline-none",
              tone === "dark" ? "text-slate-900 placeholder:text-slate-400" : "text-ink placeholder:text-muted-foreground",
              "focus-visible:ring-2 focus-visible:ring-brand/30 md:text-[15px]",
            )}
          />
          <SubmitButton tone={tone} />
        </div>
      </form>

      <p
        id={statusId}
        role={state.status === "error" ? "alert" : "status"}
        className={cn(
          "mt-3 flex min-h-5 items-start gap-1.5 text-sm",
          state.status === "error" ? (tone === "dark" ? "text-red-300" : "text-critical") : "sr-only",
        )}
      >
        {state.status === "error" ? (
          <>
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {state.message}
          </>
        ) : (
          "Enter a website URL to start a SiteLens analysis."
        )}
      </p>

      <div className="mt-4">
        <CheckItems items={trustItems} tone={tone} />
      </div>
    </div>
  );
}
