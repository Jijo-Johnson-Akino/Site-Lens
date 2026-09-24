import { ScoreDashboard } from "@/components/scan/ScoreDashboard";

type ScorePageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: ScorePageProps) {
  const { scanId } = await params;
  return {
    title: `Website Health — Scan #${scanId} — SiteLens`,
    description: "SiteLens overall website health score from completed analyzer results.",
  };
}

export default async function ScorePage({ params }: ScorePageProps) {
  const { scanId } = await params;
  return <ScoreDashboard scanId={scanId} />;
}
