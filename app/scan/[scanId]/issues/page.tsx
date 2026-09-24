import { IssuesDashboard } from "@/components/scan/IssuesDashboard";

type IssuesPageProps = {
  params: Promise<{ scanId: string }>;
  searchParams: Promise<{ page_url?: string; issue_key?: string; issue_ids?: string; category?: string }>;
};

export async function generateMetadata({ params }: IssuesPageProps) {
  const { scanId } = await params;
  return {
    title: `Issues — Scan #${scanId} — SiteLens`,
    description: "All detected website issues across SiteLens analyses.",
  };
}

export default async function IssuesPage({ params, searchParams }: IssuesPageProps) {
  const { scanId } = await params;
  const query = await searchParams;
  return <IssuesDashboard scanId={scanId} pageUrl={query.page_url} issueKey={query.issue_key} issueIds={query.issue_ids} categoryFilter={query.category} />;
}
