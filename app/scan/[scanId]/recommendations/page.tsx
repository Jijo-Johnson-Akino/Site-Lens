import { RecommendationsDashboard } from "@/components/scan/RecommendationsDashboard";

type RecommendationsPageProps = {
  params: Promise<{ scanId: string }>;
  searchParams: Promise<{ category?: string }>;
};

export async function generateMetadata({ params }: RecommendationsPageProps) {
  const { scanId } = await params;
  return {
    title: `Recommendations — Scan #${scanId} — SiteLens`,
    description: "Prioritized implementation guidance generated from SiteLens findings.",
  };
}

export default async function RecommendationsPage({ params, searchParams }: RecommendationsPageProps) {
  const { scanId } = await params;
  const query = await searchParams;
  return <RecommendationsDashboard scanId={scanId} categoryFilter={query.category} />;
}
