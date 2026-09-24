import { StructuredDataDashboard } from "@/components/scan/StructuredDataDashboard";

type SchemaPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: SchemaPageProps) {
  const { scanId } = await params;
  return {
    title: `Structured Data — Scan #${scanId} — SiteLens`,
    description: "Automated analysis of structured data and machine-readable page metadata.",
  };
}

export default async function StructuredDataPage({ params }: SchemaPageProps) {
  const { scanId } = await params;
  return <StructuredDataDashboard scanId={scanId} />;
}
