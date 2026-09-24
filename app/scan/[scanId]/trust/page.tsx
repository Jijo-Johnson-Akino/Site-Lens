import { TrustDashboard } from "@/components/scan/TrustDashboard";

type TrustPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: TrustPageProps) {
  const { scanId } = await params;
  return {
    title: `Trust & Credibility — Scan #${scanId} — SiteLens`,
    description: "Observable trust and credibility signals identified by SiteLens.",
  };
}

export default async function TrustPage({ params }: TrustPageProps) {
  const { scanId } = await params;
  return <TrustDashboard scanId={scanId} />;
}
