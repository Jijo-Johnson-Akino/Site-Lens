import Link from "next/link";

import { cn } from "@/lib/utils";

export function Logo({
  compact = false,
  href = "/",
  inverted = false,
}: {
  compact?: boolean;
  href?: string;
  inverted?: boolean;
}) {
  const mark = "/brand/sitelens-mark.png";
  const onLight = "/brand/sitelens-logo.png";
  const onDark = "/brand/sitelens-logo-on-dark.png";

  return (
    <Link href={href} aria-label="SiteLens home" className="inline-flex min-w-0 items-center">
      {compact ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={mark} alt="" className="h-7 w-auto max-w-8 object-contain object-left sm:h-8" />
      ) : inverted ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={onDark} alt="" className="h-7 w-auto max-w-[9.75rem] object-contain object-left sm:h-8 sm:max-w-[12rem]" />
      ) : (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={onLight}
            alt=""
            className={cn("h-7 w-auto max-w-[9.75rem] object-contain object-left sm:h-8 sm:max-w-[12rem]", "dark:hidden")}
          />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={onDark}
            alt=""
            className={cn("hidden h-7 w-auto max-w-[9.75rem] object-contain object-left sm:h-8 sm:max-w-[12rem]", "dark:block")}
          />
        </>
      )}
    </Link>
  );
}
