import { AeoDashboard } from "@/components/scan/AeoDashboard";

type AeoPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: AeoPageProps) {
  const { scanId } = await params;
  return {
    title: `AEO — Scan #${scanId} — SiteLens`,
    description: "AEO / AI search readiness analysis for this website scan.",
  };
}

export default async function AeoPage({ params }: AeoPageProps) {
  const { scanId } = await params;
  return <AeoDashboard scanId={scanId} />;
}
