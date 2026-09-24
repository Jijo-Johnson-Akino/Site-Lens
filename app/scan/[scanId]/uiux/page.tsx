import { UiuxDashboard } from "@/components/scan/UiuxDashboard";

type UiuxPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: UiuxPageProps) {
  const { scanId } = await params;
  return {
    title: `UI/UX — Scan #${scanId} — SiteLens`,
    description: "UI/UX analysis for this website scan.",
  };
}

export default async function UiuxPage({ params }: UiuxPageProps) {
  const { scanId } = await params;
  return <UiuxDashboard scanId={scanId} />;
}
