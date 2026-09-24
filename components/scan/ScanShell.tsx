"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";

import { Logo } from "@/components/landing/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { hostnameOf, scanStatusLabel } from "@/lib/scan/display";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

export type ScanNavId =
  | "overview"
  | "score"
  | "report"
  | "seo"
  | "aeo"
  | "uiux"
  | "accessibility"
  | "performance"
  | "content"
  | "structured-data"
  | "mobile"
  | "cro"
  | "trust"
  | "issues"
  | "recommendations"
  | "action-plan"
  | "pages"
  | "architecture"
  | "competitors";

const PAGE_TITLES: Record<ScanNavId, string> = {
  overview: "Overview",
  score: "Website Health Score",
  report: "Website Analysis Report",
  seo: "SEO analysis",
  aeo: "AEO analysis",
  uiux: "UI/UX analysis",
  accessibility: "Accessibility analysis",
  performance: "Performance analysis",
  content: "Content analysis",
  "structured-data": "Structured Data analysis",
  mobile: "Mobile analysis",
  cro: "CRO analysis",
  trust: "Trust Signals",
  issues: "Issues",
  recommendations: "Recommendations",
  "action-plan": "Action Plan",
  pages: "Pages",
  architecture: "Architecture",
  competitors: "Competitors",
};

type NavItem = { id: ScanNavId; label: string; href: (scanId: string) => string };

const NAV_GROUPS: Array<{ id: string; label: string; items: NavItem[] }> = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { id: "overview", label: "Overview", href: (id) => `/scan/${id}` },
      { id: "score", label: "Score Breakdown", href: (id) => `/scan/${id}/score` },
      { id: "issues", label: "Issues", href: (id) => `/scan/${id}/issues` },
      { id: "recommendations", label: "Recommendations", href: (id) => `/scan/${id}/recommendations` },
      { id: "pages", label: "Pages", href: (id) => `/scan/${id}/pages` },
      { id: "architecture", label: "Architecture", href: (id) => `/scan/${id}/architecture` },
    ],
  },
  {
    id: "analysis",
    label: "Analysis",
    items: [
      { id: "seo", label: "SEO", href: (id) => `/scan/${id}/seo` },
      { id: "aeo", label: "AEO", href: (id) => `/scan/${id}/aeo` },
      { id: "uiux", label: "UI/UX", href: (id) => `/scan/${id}/uiux` },
      { id: "accessibility", label: "Accessibility", href: (id) => `/scan/${id}/accessibility` },
      { id: "performance", label: "Performance", href: (id) => `/scan/${id}/performance` },
      { id: "content", label: "Content", href: (id) => `/scan/${id}/content` },
      { id: "structured-data", label: "Structured Data", href: (id) => `/scan/${id}/structured-data` },
      { id: "mobile", label: "Mobile", href: (id) => `/scan/${id}/mobile` },
      { id: "cro", label: "CRO", href: (id) => `/scan/${id}/cro` },
      { id: "trust", label: "Trust", href: (id) => `/scan/${id}/trust` },
    ],
  },
  {
    id: "optimization",
    label: "Optimization",
    items: [{ id: "action-plan", label: "Action Plan", href: (id) => `/scan/${id}/action-plan` }],
  },
  {
    id: "benchmark",
    label: "Benchmark",
    items: [{ id: "competitors", label: "Competitors", href: (id) => `/scan/${id}/competitors` }],
  },
  {
    id: "report",
    label: "Report",
    items: [{ id: "report", label: "Final Report", href: (id) => `/scan/${id}/report` }],
  },
];

function isDropdownGroup(group: (typeof NAV_GROUPS)[number]) {
  return group.id === "analysis";
}

function groupHasCurrent(group: (typeof NAV_GROUPS)[number], current: ScanNavId) {
  return group.items.some((item) => item.id === current);
}

export function ScanShell({
  scanId,
  current,
  children,
}: {
  scanId: string;
  current: ScanNavId;
  children: React.ReactNode;
}) {
  const { scan } = useScanStatus(scanId);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(NAV_GROUPS.filter(isDropdownGroup).map((group) => [group.id, groupHasCurrent(group, current)])),
  );

  useEffect(() => {
    const active = NAV_GROUPS.find((group) => isDropdownGroup(group) && groupHasCurrent(group, current));
    if (!active) return;
    setOpenGroups((prev) => (prev[active.id] ? prev : { ...prev, [active.id]: true }));
  }, [current]);

  const host = hostnameOf(scan?.result?.website?.final_url || scan?.normalized_url || scan?.url);
  const fullUrl = scan?.result?.website?.final_url || scan?.normalized_url || scan?.url;
  const badges: Partial<Record<ScanNavId, number>> = {
    issues: typeof scan?.result?.issues?.summary?.total === "number" ? scan.result.issues.summary.total : undefined,
    recommendations:
      typeof scan?.result?.recommendations?.summary?.total === "number" ? scan.result.recommendations.summary.total : undefined,
    pages: typeof scan?.result?.pages?.summary?.crawled === "number" ? scan.result.pages.summary.crawled : undefined,
  };

  return (
    <div className="flex min-h-full min-w-0 flex-1 flex-col bg-background lg:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-sidebar-border bg-navy text-navy-foreground print:hidden lg:sticky lg:top-0 lg:h-svh lg:w-56 lg:border-r lg:border-b-0">
        <div className="flex h-16 items-center justify-between gap-2 px-4">
          <Logo href="/" inverted />
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-lg text-navy-foreground hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:outline-none lg:hidden"
            aria-expanded={menuOpen}
            aria-controls="scan-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            <span className="sr-only">{menuOpen ? "Close scan navigation" : "Open scan navigation"}</span>
          </button>
        </div>
        <nav
          id="scan-nav"
          aria-label="Scan"
          className={cn(
            "flex-col gap-4 overflow-y-auto px-3 pb-4 lg:flex lg:min-h-0 lg:flex-1 lg:pb-6",
            menuOpen ? "flex" : "hidden",
          )}
        >
          {NAV_GROUPS.map((group) => {
            const dropdown = isDropdownGroup(group);
            const expanded = !dropdown || Boolean(openGroups[group.id]);
            const panelId = `scan-nav-${group.id}`;
            return (
              <div key={group.id}>
                {dropdown ? (
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 rounded-md px-3 py-1 text-[10px] font-medium tracking-[0.16em] text-navy-foreground/45 uppercase hover:bg-white/5 hover:text-navy-foreground/70 focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:outline-none"
                    aria-expanded={expanded}
                    aria-controls={panelId}
                    onClick={() => setOpenGroups((prev) => ({ ...prev, [group.id]: !prev[group.id] }))}
                  >
                    {group.label}
                    <ChevronDown
                      className={cn("size-3.5 shrink-0 transition-transform", expanded && "rotate-180")}
                      aria-hidden
                    />
                  </button>
                ) : (
                  <p className="px-3 pb-1 text-[10px] font-medium tracking-[0.16em] text-navy-foreground/45 uppercase">
                    {group.label}
                  </p>
                )}
                {expanded ? (
                  <div id={panelId} className="flex flex-col gap-0.5" role={dropdown ? "region" : undefined}>
                    {group.items.map((item) => (
                      <ShellLink
                        key={item.id}
                        href={item.href(scanId)}
                        active={current === item.id}
                        badge={badges[item.id]}
                        onNavigate={() => setMenuOpen(false)}
                      >
                        {item.label}
                      </ShellLink>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-white/10 bg-navy px-5 text-navy-foreground print:hidden sm:px-8">
          <div className="min-w-0">
            <p className="text-sm font-medium text-navy-foreground">{PAGE_TITLES[current]}</p>
            {host ? (
              <p className="truncate text-xs text-navy-foreground/60" title={fullUrl}>
                {host}
                {scan?.status ? ` · ${scanStatusLabel(scan.status)}` : ""}
              </p>
            ) : (
              <p className="text-xs text-navy-foreground/60">Loading website…</p>
            )}
          </div>
          <ThemeToggle className="border-white/15 bg-white/10 text-navy-foreground hover:bg-white/15" />
        </header>
        <main className="min-w-0 flex-1 overflow-x-hidden px-6 py-6">{children}</main>
      </div>
    </div>
  );
}

function ShellLink({
  href,
  active,
  badge,
  onNavigate,
  children,
}: {
  href: string;
  active: boolean;
  badge?: number;
  onNavigate: () => void;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={cn(
        "flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
        active
          ? "bg-white/10 font-semibold text-navy-foreground"
          : "font-normal text-navy-foreground/70 hover:bg-white/5 hover:text-navy-foreground",
      )}
    >
      <span>{children}</span>
      {typeof badge === "number" ? (
        <span className="rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-navy-foreground/80">
          {badge}
        </span>
      ) : null}
    </Link>
  );
}
