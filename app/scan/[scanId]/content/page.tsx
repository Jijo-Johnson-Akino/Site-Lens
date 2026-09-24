import { ContentDashboard } from "@/components/scan/ContentDashboard";

type ContentPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: ContentPageProps) {
  const { scanId } = await params;
  return {
    title: `Content — Scan #${scanId} — SiteLens`,
    description: "Deterministic content analysis for this website scan.",
  };
}

export default async function ContentPage({ params }: ContentPageProps) {
  const { scanId } = await params;
  return <ContentDashboard scanId={scanId} />;
}
