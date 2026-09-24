export function ScoreRing({
  score,
  band,
  size = 160,
}: {
  score: number | null;
  band: string;
  size?: number;
}) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const value = typeof score === "number" ? Math.max(0, Math.min(100, score)) : 0;
  const offset = circumference - (value / 100) * circumference;
  const label = typeof score === "number" ? `Website Health Score: ${score} out of 100. ${band}.` : "Website Health Score unavailable.";
  return (
    <div className="flex flex-col items-center justify-center">
      <svg width={size} height={size} viewBox="0 0 160 160" role="img" aria-label={label}>
        <circle cx="80" cy="80" r={radius} fill="none" stroke="currentColor" className="text-muted" strokeWidth="12" />
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke="currentColor"
          className={ringClass(score)}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={typeof score === "number" ? offset : circumference}
          strokeLinecap="round"
          transform="rotate(-90 80 80)"
        />
        <text x="80" y="76" textAnchor="middle" className="fill-foreground text-3xl font-semibold">
          {typeof score === "number" ? score : "—"}
        </text>
        <text x="80" y="98" textAnchor="middle" className="fill-muted-foreground text-xs">
          /100
        </text>
      </svg>
      <p className="mt-2 text-center text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

function ringClass(score: number | null) {
  if (typeof score !== "number") return "text-muted-foreground";
  if (score >= 75) return "text-primary";
  if (score >= 60) return "text-warn";
  return "text-critical";
}
