"use client";

import { useEffect, useId, useState } from "react";
import { Menu, X } from "lucide-react";

import { Logo } from "@/components/landing/logo";
import { LANDING_NAV } from "@/components/landing/nav-links";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function close() {
    setOpen(false);
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/90 backdrop-blur-md">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-[10px] focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-white focus:outline-none"
      >
        Skip to content
      </a>
      <div className="landing-container relative z-50 flex h-16 items-center justify-between gap-4 lg:h-[4.5rem]">
        <Logo />

        <nav className="absolute top-1/2 left-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-8 md:flex" aria-label="Page">
          {LANDING_NAV.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-muted-foreground transition-colors hover:text-ink focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <a
            href="#benchmark"
            className="hidden h-10 items-center rounded-[10px] bg-brand px-4 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8] focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:outline-none md:inline-flex"
          >
            Start Free Analysis
          </a>
          <button
            type="button"
            className="inline-flex size-10 items-center justify-center rounded-[10px] border border-border bg-card text-ink md:hidden focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
            aria-expanded={open}
            aria-controls={menuId}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
      </div>

      {open ? (
        <div className="md:hidden">
          <button
            type="button"
            className="fixed inset-x-0 top-16 bottom-0 z-40 bg-ink/25"
            aria-label="Close menu"
            onClick={close}
          />
          <nav
            id={menuId}
            aria-label="Mobile"
            className="relative z-50 border-t border-border bg-card px-5 py-4 shadow-landing"
          >
            <ul className="flex flex-col gap-1">
              {LANDING_NAV.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    onClick={close}
                    className="block rounded-[10px] px-3 py-2.5 text-sm font-medium text-ink hover:bg-muted focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
              <li className="pt-2">
                <a
                  href="#benchmark"
                  onClick={close}
                  className={cn(
                    "flex h-11 items-center justify-center rounded-[10px] bg-brand text-sm font-medium text-white",
                    "hover:bg-[#1d4ed8] focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none",
                  )}
                >
                  Start Free Analysis
                </a>
              </li>
            </ul>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
