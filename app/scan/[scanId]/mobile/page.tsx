import { MobileDashboard } from "@/components/scan/MobileDashboard";

type MobilePageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: MobilePageProps) {
  const { scanId } = await params;
  return {
    title: `Mobile — Scan #${scanId} — SiteLens`,
    description: "Automated analysis of responsive behavior and mobile-specific layout signals.",
  };
}

export default async function MobilePage({ params }: MobilePageProps) {
  const { scanId } = await params;
  return <MobileDashboard scanId={scanId} />;
}
