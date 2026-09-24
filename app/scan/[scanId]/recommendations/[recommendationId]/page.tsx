import { RecommendationDetailView } from "@/components/scan/RecommendationDetail";

type RecommendationPageProps = {
  params: Promise<{ scanId: string; recommendationId: string }>;
};

export async function generateMetadata({ params }: RecommendationPageProps) {
  const { scanId, recommendationId } = await params;
  return {
    title: `Recommendation ${recommendationId} — Scan #${scanId} — SiteLens`,
    description: "SiteLens recommendation details, evidence, and action steps.",
  };
}

export default async function RecommendationPage({ params }: RecommendationPageProps) {
  const { scanId, recommendationId } = await params;
  return <RecommendationDetailView scanId={scanId} recommendationId={recommendationId} />;
}
