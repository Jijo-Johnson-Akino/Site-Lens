import { CroDashboard } from "@/components/scan/CroDashboard";

type CroPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: CroPageProps) {
  const { scanId } = await params;
  return {
    title: `CRO — Scan #${scanId} — SiteLens`,
    description: "Observable conversion-readiness signals measured by SiteLens.",
  };
}

export default async function CroPage({ params }: CroPageProps) {
  const { scanId } = await params;
  return <CroDashboard scanId={scanId} />;
}
