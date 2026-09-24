import { ScanProgress } from "@/components/scan/ScanProgress";

type ScanPageProps = {
  params: Promise<{ scanId: string }>;
};

export async function generateMetadata({ params }: ScanPageProps) {
  await params;
  return {
    title: `Analyzing website — SiteLens`,
    description: "Website scan in progress. SiteLens is analyzing this site across SEO, AEO, UI/UX, accessibility, performance, and more.",
  };
}

export default async function ScanPage({ params }: ScanPageProps) {
  const { scanId } = await params;
  return <ScanProgress scanId={scanId} />;
}
