import { ArchitectureDashboard } from "@/components/scan/ArchitectureDashboard";

type ArchitecturePageProps = {
  params: Promise<{ scanId: string }>;
  searchParams: Promise<{ focus?: string; page?: string }>;
};

export async function generateMetadata({ params }: ArchitecturePageProps) {
  const { scanId } = await params;
  return {
    title: `Architecture — Scan #${scanId} — SiteLens`,
    description: "Website architecture from pages and internal links observed during this SiteLens crawl.",
  };
}

export default async function ArchitecturePage({ params, searchParams }: ArchitecturePageProps) {
  const { scanId } = await params;
  const query = await searchParams;
  const focusPageId = query.focus || query.page;
  return <ArchitectureDashboard scanId={scanId} focusPageId={focusPageId} />;
}
