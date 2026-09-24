import { ReportDashboard } from "@/components/scan/ReportDashboard";

type ReportPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: ReportPageProps) {
  const { scanId } = await params;
  return {
    title: `Website Analysis Report — Scan #${scanId} — SiteLens`,
    description: "SiteLens professional website analysis report assembled from stored scan results.",
  };
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { scanId } = await params;
  return <ReportDashboard scanId={scanId} />;
}
