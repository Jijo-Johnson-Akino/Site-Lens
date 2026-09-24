import type { Metadata } from "next";

import { AnalysisAreas } from "@/components/landing/analysis-areas";
import { FinalCta } from "@/components/landing/final-cta";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { ProductInsights } from "@/components/landing/product-insights";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";
import { TeamBenefits } from "@/components/landing/team-benefits";

const TITLE = "SiteLens — Website Intelligence & Benchmarking";
const DESCRIPTION =
  "Analyze your website across SEO, AEO, performance, UX, accessibility, content, CRO and more with SiteLens.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    type: "website",
    siteName: "SiteLens",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ url?: string | string[]; error?: string | string[] }>;
}) {
  const params = await searchParams;
  const initialUrl = typeof params.url === "string" ? params.url : "";
  const initialError = typeof params.error === "string" ? params.error : "";

  return (
    <div className="landing relative flex min-h-full w-full max-w-[100vw] min-w-0 flex-1 flex-col overflow-x-clip">
      <SiteHeader />
      <main id="main" className="relative min-w-0 flex-1">
        <Hero initialUrl={initialUrl} initialError={initialError} />
        <AnalysisAreas />
        <HowItWorks />
        <TeamBenefits />
        <ProductInsights />
        <FinalCta initialUrl={initialUrl} initialError={initialError} />
      </main>
      <SiteFooter />
    </div>
  );
}
