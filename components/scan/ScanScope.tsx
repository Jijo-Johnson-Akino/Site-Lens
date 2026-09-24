import type { LucideIcon } from "lucide-react";
import {
  Accessibility,
  Brain,
  FileSearch,
  LayoutDashboard,
  ListChecks,
  MonitorSmartphone,
  MousePointerClick,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Timer,
} from "lucide-react";

const LEFT = [
  { label: "SEO", icon: Search },
  { label: "AEO / AI Search", icon: Brain },
  { label: "UI/UX", icon: LayoutDashboard },
  { label: "Accessibility", icon: Accessibility },
  { label: "Performance", icon: Timer },
  { label: "Content", icon: FileSearch },
];

const RIGHT = [
  { label: "Structured Data", icon: Sparkles },
  { label: "Mobile", icon: Smartphone },
  { label: "CRO", icon: MousePointerClick },
  { label: "Trust & Credibility", icon: ShieldCheck },
  { label: "Architecture", icon: MonitorSmartphone },
  { label: "Issues & Recommendations", icon: ListChecks },
];

export function ScanScope() {
  return (
    <section className="scan-monitor-card p-5 sm:p-6">
      <h2 className="text-lg font-semibold text-ink">What we&apos;re checking</h2>
      <p className="mt-1 text-sm text-muted-foreground">Scope of this SiteLens analysis.</p>
      <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
        <ul className="space-y-2.5">
          {LEFT.map((item) => (
            <ScopeItem key={item.label} label={item.label} Icon={item.icon} />
          ))}
        </ul>
        <ul className="space-y-2.5">
          {RIGHT.map((item) => (
            <ScopeItem key={item.label} label={item.label} Icon={item.icon} />
          ))}
        </ul>
      </div>
    </section>
  );
}

function ScopeItem({
  label,
  Icon,
}: {
  label: string;
  Icon: LucideIcon;
}) {
  return (
    <li className="flex items-center gap-2 text-sm text-ink">
      <Icon className="size-4 shrink-0 text-brand" aria-hidden />
      {label}
    </li>
  );
}
