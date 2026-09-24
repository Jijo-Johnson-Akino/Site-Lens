import { Logo } from "@/components/landing/logo";
import { FOOTER_PRODUCT } from "@/components/landing/nav-links";

export function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-card">
      <div className="landing-container grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-[1.2fr_0.7fr_0.9fr] lg:py-16">
        <div>
          <Logo />
          <p className="mt-3 max-w-xs text-sm text-muted-foreground">Website benchmarking &amp; intelligence</p>
        </div>
        <div>
          <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">Product</p>
          <ul className="mt-4 space-y-2.5">
            {FOOTER_PRODUCT.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="text-sm text-muted-foreground transition-colors hover:text-ink focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">Get started</p>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Analyze a website to see scores, issues, recommendations, and an Action Plan. Accounts and
            billing are not part of this product yet.
          </p>
          <a
            href="#benchmark"
            className="mt-4 inline-flex text-sm font-medium text-brand hover:text-[#1d4ed8] focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
          >
            Start Free Analysis
          </a>
        </div>
      </div>
      <div className="border-t border-border">
        <div className="landing-container flex flex-col gap-2 py-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[13px] text-muted-foreground">© {year} SiteLens. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
