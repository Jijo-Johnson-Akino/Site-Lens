import type { ReactNode } from "react";

import type { NamedCount, ScoreHistoryPoint } from "@/lib/scan/report-ui";
import { formatReportDate } from "@/lib/scan/report-ui";
import { cn } from "@/lib/utils";

export function HealthScoreGauge({
  score,
  band,
}: {
  score: number | null;
  band: string;
}) {
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const value = typeof score === "number" ? Math.max(0, Math.min(100, score)) : 0;
  const offset = circumference - (value / 100) * circumference;
  const label =
    typeof score === "number" ? `Website health score ${score} out of 100. ${band}.` : "Website health score unavailable.";

  return (
    <svg width="120" height="120" viewBox="0 0 120 120" role="img" aria-label={label} className="shrink-0">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" className="text-muted" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="currentColor"
        className={typeof score === "number" ? "text-primary" : "text-muted-foreground"}
        strokeWidth="10"
        strokeDasharray={circumference}
        strokeDashoffset={typeof score === "number" ? offset : circumference}
        strokeLinecap="round"
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="56" textAnchor="middle" className="fill-foreground text-[28px] font-semibold">
        {typeof score === "number" ? score : "—"}
      </text>
      <text x="60" y="74" textAnchor="middle" className="fill-muted-foreground text-[10px]">
        /100
      </text>
    </svg>
  );
}

export function DonutChart({
  slices,
  total,
  centerLabel,
  ariaLabel,
  size = 148,
  thickness = 16,
  className,
}: {
  slices: NamedCount[];
  total: number;
  centerLabel: string;
  ariaLabel: string;
  size?: number;
  thickness?: number;
  className?: string;
}) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const arcTotal = slices.reduce((sum, slice) => sum + slice.count, 0);
  const visible = slices.filter((slice) => slice.count > 0);
  const gap = visible.length > 1 ? 3 : 0;
  const usable = Math.max(circumference - gap * visible.length, 0);
  const segments = visible.reduce<Array<NamedCount & { length: number; dashOffset: number }>>((items, slice) => {
    const length = (slice.count / Math.max(arcTotal, 1)) * usable;
    const previous = items[items.length - 1];
    const start = previous ? previous.dashOffset + previous.length + gap : 0;
    return [...items, { ...slice, length, dashOffset: start }];
  }, []);

  return (
    <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label={ariaLabel} className={cn("shrink-0", className)}>
      <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" className="text-muted" strokeWidth={thickness} />
      {segments.map((slice) => (
        <circle
          key={slice.id}
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke={slice.color}
          strokeWidth={thickness}
          strokeDasharray={`${slice.length} ${Math.max(circumference - slice.length, 0)}`}
          strokeDashoffset={-slice.dashOffset}
          transform="rotate(-90 60 60)"
        />
      ))}
      <text x="60" y="56" textAnchor="middle" className="fill-foreground text-[22px] font-semibold">
        {total}
      </text>
      <text x="60" y="74" textAnchor="middle" className="fill-muted-foreground text-[9px]">
        {centerLabel}
      </text>
    </svg>
  );
}

export function HorizontalStackedBar({ slices, ariaLabel }: { slices: NamedCount[]; ariaLabel: string }) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted" role="img" aria-label={ariaLabel}>
      {total > 0 ? (
        <div className="flex h-full w-full">
          {slices
            .filter((slice) => slice.count > 0)
            .map((slice) => (
              <span
                key={slice.id}
                className="h-full"
                style={{ width: `${(slice.count / total) * 100}%`, backgroundColor: slice.color }}
              />
            ))}
        </div>
      ) : null}
    </div>
  );
}

export function CategoryBarChart({
  bars,
  ariaLabel,
}: {
  bars: Array<{ id: string; label: string; score: number }>;
  ariaLabel: string;
}) {
  const width = 640;
  const height = 248;
  const pad = { top: 22, right: 8, bottom: 64, left: 8 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const n = Math.max(bars.length, 1);
  const gap = 10;
  const barW = Math.min(36, Math.max(16, (innerW - gap * (n - 1)) / n));
  const startX = pad.left + Math.max(0, (innerW - (barW * n + gap * (n - 1))) / 2);

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel} className="overflow-visible">
      {[0, 25, 50, 75, 100].map((tick) => {
        const y = pad.top + innerH - (tick / 100) * innerH;
        return (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="currentColor" className="text-border" strokeWidth="1" />
          </g>
        );
      })}
      {bars.map((bar, index) => {
        const x = startX + index * (barW + gap);
        const h = (Math.max(0, Math.min(100, bar.score)) / 100) * innerH;
        const y = pad.top + innerH - h;
        return (
          <g key={bar.id}>
            <rect x={x} y={y} width={barW} height={Math.max(h, 0)} rx="4" fill="currentColor" className="text-primary" />
            <text x={x + barW / 2} y={y - 6} textAnchor="middle" className="fill-foreground text-[11px] font-medium">
              {bar.score}
            </text>
            <text
              x={x + barW / 2}
              y={height - 8}
              textAnchor="end"
              className="fill-muted-foreground text-[10px]"
              transform={`rotate(-32 ${x + barW / 2} ${height - 8})`}
            >
              {bar.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ScoreTrendArea({ points }: { points: ScoreHistoryPoint[] }) {
  const width = 640;
  const height = 220;
  const pad = { top: 16, right: 16, bottom: 32, left: 28 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const xs = points.map((_, index) => pad.left + (index / Math.max(points.length - 1, 1)) * innerW);
  const ys = points.map((point) => pad.top + innerH - (Math.max(0, Math.min(100, point.score)) / 100) * innerH);
  const line = xs.map((x, index) => `${index === 0 ? "M" : "L"} ${x} ${ys[index]}`).join(" ");
  const area = `${line} L ${xs[xs.length - 1]} ${pad.top + innerH} L ${xs[0]} ${pad.top + innerH} Z`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={points.map((point) => `${formatReportDate(point.analyzed_at)}: ${point.score} / 100`).join(". ")}
    >
      {[0, 25, 50, 75, 100].map((tick) => {
        const y = pad.top + innerH - (tick / 100) * innerH;
        return (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="currentColor" className="text-border" strokeWidth="1" />
            <text x={pad.left - 6} y={y + 3} textAnchor="end" className="fill-muted-foreground text-[9px]">
              {tick}
            </text>
          </g>
        );
      })}
      <path d={area} fill="currentColor" className="text-primary/15" />
      <path d={line} fill="none" stroke="currentColor" className="text-primary" strokeWidth="2.5" />
      {points.map((point, index) => (
        <circle key={`${point.analyzed_at}-${index}`} cx={xs[index]} cy={ys[index]} r="3.5" fill="currentColor" className="text-primary">
          <title>
            {formatReportDate(point.analyzed_at)}
            {`\n${point.score} / 100`}
          </title>
        </circle>
      ))}
      {points.map((point, index) => (
        <text key={`x-${point.analyzed_at}-${index}`} x={xs[index]} y={height - 10} textAnchor="middle" className="fill-muted-foreground text-[10px]">
          {shortAxisDate(point.analyzed_at)}
        </text>
      ))}
    </svg>
  );
}

function shortAxisDate(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

export function ChartCard({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-xl border border-border bg-card p-4 shadow-[0_1px_3px_rgba(15,23,42,0.04)] sm:p-5", className)}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-foreground">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
