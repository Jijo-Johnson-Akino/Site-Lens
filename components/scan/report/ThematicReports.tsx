import Link from "next/link";
import {
  Accessibility,
  Braces,
  FileText,
  Gauge,
  LayoutDashboard,
  MessageSquareText,
  MousePointerClick,
  Network,
  Search,
  ShieldCheck,
  Smartphone,
  type LucideIcon,
} from "lucide-react";

import type { ScanReportResponse } from "@/lib/scan/api";
import { compactCategoryLabel } from "@/lib/scan/report-ui";

const ICONS: Record<string, LucideIcon> = {
  architecture: Network,
  seo: Search,
  aeo: MessageSquareText,
  uiux: LayoutDashboard,
  accessibility: Accessibility,
  performance: Gauge,
  content: FileText,
  structured_data: Braces,
  mobile: Smartphone,
  cro: MousePointerClick,
  trust: ShieldCheck,
};

export function ThematicReports({ report }: { report: ScanReportResponse }) {
  const cards: Array<{ id: string; name: string; href: string; score: number | null; available: boolean }> = [
    {
      id: "architecture",
      name: "Architecture",
      href: report.architecture.href || `/scan/${report.scan.scan_id}/architecture`,
      score: null,
      available: report.architecture.available,
    },
    ...report.categories.map((row) => ({
      id: row.category,
      name: compactCategoryLabel(row.name || row.category),
      href: row.href.startsWith("/") ? row.href : `/scan/${report.scan.scan_id}/${row.href}`,
      score: row.available && typeof row.score === "number" ? row.score : null,
      available: row.available,
    })),
  ];

  return (
    <section>
      <h2 className="mb-3 text-[15px] font-semibold text-foreground">Thematic Reports</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        {cards.map((card) => {
          const Icon = ICONS[card.id] ?? FileText;
          let scoreLabel = "Unavailable";
          if (card.id === "architecture" && card.available) scoreLabel = "—";
          else if (typeof card.score === "number") scoreLabel = `${card.score}%`;
          return (
            <Link
              key={card.id}
              href={card.href}
              className="rounded-xl border border-border bg-card p-3 shadow-[0_1px_3px_rgba(15,23,42,0.04)] transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              <Icon className="size-4 text-primary" aria-hidden="true" />
              <p className="mt-2 text-[13px] font-medium text-foreground">{card.name}</p>
              <p className="text-[15px] font-semibold tabular-nums text-foreground">{scoreLabel}</p>
              <p className="mt-1 text-[11px] text-primary">View details →</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
