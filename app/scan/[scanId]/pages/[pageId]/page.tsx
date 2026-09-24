import { PageDetail } from "@/components/scan/PageDetail";

type PageDetailPageProps = {
  params: Promise<{ scanId: string; pageId: string }>;
};

export async function generateMetadata({ params }: PageDetailPageProps) {
  const { scanId, pageId } = await params;
  return {
    title: `Page ${pageId} — Scan #${scanId} — SiteLens`,
    description: "Page details from this SiteLens scan.",
  };
}

export default async function PageDetailPage({ params }: PageDetailPageProps) {
  const { scanId, pageId } = await params;
  return <PageDetail scanId={scanId} pageId={pageId} />;
}
