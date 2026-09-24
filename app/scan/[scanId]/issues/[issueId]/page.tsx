import { IssueDetail } from "@/components/scan/IssueDetail";

type IssuePageProps = {
  params: Promise<{ scanId: string; issueId: string }>;
};

export async function generateMetadata({ params }: IssuePageProps) {
  const { scanId, issueId } = await params;
  return {
    title: `Issue ${issueId} — Scan #${scanId} — SiteLens`,
    description: "Unified SiteLens issue details.",
  };
}

export default async function IssuePage({ params }: IssuePageProps) {
  const { scanId, issueId } = await params;
  return <IssueDetail scanId={scanId} issueId={issueId} />;
}
