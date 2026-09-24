import { CompetitorsDashboard } from "@/components/scan/CompetitorsDashboard";

type CompetitorsPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: CompetitorsPageProps) {
  const { scanId } = await params;
  return {
    title: `Competitors — Scan #${scanId} — SiteLens`,
    description: "Compare measurable SiteLens findings against independently scanned competitor websites.",
  };
}

export default async function CompetitorsPage({ params }: CompetitorsPageProps) {
  const { scanId } = await params;
  return <CompetitorsDashboard scanId={scanId} />;
}
