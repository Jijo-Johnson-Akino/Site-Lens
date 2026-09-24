import { cn } from "@/lib/utils";

export function LandingSection({
  id,
  children,
  className,
  containerClassName,
}: {
  id?: string;
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
}) {
  return (
    <section id={id} className={cn("scroll-mt-24 py-16 sm:py-20 lg:py-32", className)}>
      <div className={cn("landing-container", containerClassName)}>{children}</div>
    </section>
  );
}

export function SectionEyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold tracking-[0.18em] text-brand uppercase">{children}</p>
  );
}

export function SectionHeading({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn("mt-3 max-w-xl text-[1.75rem] leading-[1.15] font-semibold tracking-tight text-ink sm:text-4xl lg:text-[2.75rem]", className)}>
      {children}
    </h2>
  );
}
