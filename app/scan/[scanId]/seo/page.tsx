import { SeoDashboard } from "@/components/scan/SeoDashboard";

type SeoPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: SeoPageProps) {
  const { scanId } = await params;
  return {
    title: `SEO — Scan #${scanId} — SiteLens`,
    description: "SEO analysis for this website scan.",
  };
}

export default async function SeoPage({ params }: SeoPageProps) {
  const { scanId } = await params;
  return <SeoDashboard scanId={scanId} />;
}
