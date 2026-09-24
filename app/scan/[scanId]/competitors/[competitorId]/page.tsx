import { CompetitorDetailView } from "@/components/scan/CompetitorDetail";

type CompetitorDetailPageProps = {
  params: Promise<{ scanId: string; competitorId: string }>;
};

export async function generateMetadata({ params }: CompetitorDetailPageProps) {
  const { scanId, competitorId } = await params;
  return {
    title: `Competitor ${competitorId} — Scan #${scanId} — SiteLens`,
    description: "Competitor scan summary from SiteLens observable analysis.",
  };
}

export default async function CompetitorDetailPage({ params }: CompetitorDetailPageProps) {
  const { scanId, competitorId } = await params;
  return <CompetitorDetailView scanId={scanId} competitorId={competitorId} />;
}
