import { PerformanceDashboard } from "@/components/scan/PerformanceDashboard";

type PerformancePageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: PerformancePageProps) {
  const { scanId } = await params;
  return {
    title: `Performance — Scan #${scanId} — SiteLens`,
    description: "Automated browser performance analysis for this website scan.",
  };
}

export default async function PerformancePage({ params }: PerformancePageProps) {
  const { scanId } = await params;
  return <PerformanceDashboard scanId={scanId} />;
}
