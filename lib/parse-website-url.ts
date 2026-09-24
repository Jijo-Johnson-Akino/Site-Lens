const EMPTY = "Please enter a website URL to continue.";
const INVALID = "Please enter a valid website URL.";

export type ParseWebsiteUrlResult =
  | { ok: true; href: string; host: string }
  | { ok: false; message: string };

function hasHttpProtocol(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

export function parseWebsiteUrl(value: string): ParseWebsiteUrlResult {
  const trimmed = value.trim();
  if (!trimmed) {
    return { ok: false, message: EMPTY };
  }

  const candidate = hasHttpProtocol(trimmed) ? trimmed : `https://${trimmed}`;

  try {
    const url = new URL(candidate);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return { ok: false, message: INVALID };
    }

    const host = url.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (!isLocal && !host.includes(".")) {
      return { ok: false, message: INVALID };
    }
    if (host.startsWith(".") || host.endsWith(".") || /\s/.test(host)) {
      return { ok: false, message: INVALID };
    }

    // Only add https:// when the user omitted a protocol. Keep supplied URLs intact.
    const href = hasHttpProtocol(trimmed) ? trimmed : `https://${trimmed}`;
    return { ok: true, href, host };
  } catch {
    return { ok: false, message: INVALID };
  }
}
