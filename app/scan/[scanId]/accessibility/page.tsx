import { AccessibilityDashboard } from "@/components/scan/AccessibilityDashboard";

type AccessibilityPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: AccessibilityPageProps) {
  const { scanId } = await params;
  return {
    title: `Accessibility — Scan #${scanId} — SiteLens`,
    description: "Automated accessibility analysis for this website scan.",
  };
}

export default async function AccessibilityPage({ params }: AccessibilityPageProps) {
  const { scanId } = await params;
  return <AccessibilityDashboard scanId={scanId} />;
}
