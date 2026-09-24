import { RecommendationDetailView } from "@/components/scan/RecommendationDetail";

type ActionPlanDetailPageProps = {
  params: Promise<{ scanId: string; recommendationId: string }>;
};

export async function generateMetadata({ params }: ActionPlanDetailPageProps) {
  const { scanId, recommendationId } = await params;
  return {
    title: `Action ${recommendationId} — Scan #${scanId} — SiteLens`,
    description: "Action details generated from stored SiteLens recommendations.",
  };
}

export default async function ActionPlanDetailPage({ params }: ActionPlanDetailPageProps) {
  const { scanId, recommendationId } = await params;
  return <RecommendationDetailView scanId={scanId} recommendationId={recommendationId} surface="action-plan" />;
}
