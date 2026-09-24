import { ActionPlanDashboard } from "@/components/scan/ActionPlanDashboard";

type ActionPlanPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: ActionPlanPageProps) {
  const { scanId } = await params;
  return {
    title: `Action Plan — Scan #${scanId} — SiteLens`,
    description: "Prioritized actions generated from the findings detected during this scan.",
  };
}

export default async function ActionPlanPage({ params }: ActionPlanPageProps) {
  const { scanId } = await params;
  return <ActionPlanDashboard scanId={scanId} />;
}
