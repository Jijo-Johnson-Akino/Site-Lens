import { PagesDashboard } from "@/components/scan/PagesDashboard";

type PagesPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: PagesPageProps) {
  const { scanId } = await params;
  return {
    title: `Pages — Scan #${scanId} — SiteLens`,
    description: "Inspect pages discovered during this SiteLens scan.",
  };
}

export default async function PagesPage({ params }: PagesPageProps) {
  const { scanId } = await params;
  return <PagesDashboard scanId={scanId} />;
}
