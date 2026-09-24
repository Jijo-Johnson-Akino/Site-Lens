import type { LucideIcon } from "lucide-react";
import {
  Accessibility,
  FileText,
  Gauge,
  GitCompare,
  LayoutDashboard,
  Network,
  ScanSearch,
  Search,
  ShieldCheck,
  Smartphone,
  SquareCode,
  Target,
} from "lucide-react";

import { LandingSection, SectionEyebrow } from "@/components/landing/section";

const AREAS: { name: string; icon: LucideIcon }[] = [
  { name: "SEO", icon: Search },
  { name: "AEO / AI Search", icon: ScanSearch },
  { name: "UI/UX", icon: LayoutDashboard },
  { name: "Performance", icon: Gauge },
  { name: "Accessibility", icon: Accessibility },
  { name: "Content", icon: FileText },
  { name: "Structured Data", icon: SquareCode },
  { name: "Mobile", icon: Smartphone },
  { name: "CRO", icon: Target },
  { name: "Trust", icon: ShieldCheck },
  { name: "Architecture", icon: Network },
  { name: "Competitors", icon: GitCompare },
];

export function AnalysisAreas() {
  return (
    <LandingSection id="areas">
      <div className="text-center">
        <SectionEyebrow>One platform. Twelve analysis areas.</SectionEyebrow>
      </div>
      <ul className="mt-8 grid grid-cols-2 gap-2.5 sm:gap-3 md:grid-cols-3 lg:grid-cols-4">
        {AREAS.map((area) => (
          <li key={area.name}>
            <article className="group flex items-center gap-3 rounded-2xl border border-border bg-card px-3.5 py-3 shadow-landing transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:border-brand hover:shadow-md">
              <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-xl border border-border bg-muted text-brand transition-colors group-hover:border-brand/30 group-hover:bg-accent">
                <area.icon className="size-4" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <h3 className="text-[15px] leading-tight font-medium text-ink sm:text-base">{area.name}</h3>
            </article>
          </li>
        ))}
      </ul>
    </LandingSection>
  );
}
