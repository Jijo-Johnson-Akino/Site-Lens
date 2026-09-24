"use server";

import { redirect } from "next/navigation";

import { parseWebsiteUrl } from "@/lib/parse-website-url";

const API_BASE = process.env.SITEBENCH_API_URL || "http://127.0.0.1:8001";

function failRedirect(message: string, url: string): never {
  const params = new URLSearchParams();
  params.set("error", message);
  if (url) {
    params.set("url", url);
  }
  redirect(`/?${params.toString()}`);
}

export async function startBenchmark(formData: FormData) {
  const raw = String(formData.get("url") ?? "");
  const parsed = parseWebsiteUrl(raw);
  if (!parsed.ok) {
    failRedirect(parsed.message, raw.trim());
  }

  let scanId = "";
  let errorMessage = "";
  try {
    const response = await fetch(`${API_BASE}/api/scans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: parsed.href }),
      cache: "no-store",
    });
    const body = (await response.json()) as {
      scan_id?: string;
      error?: { message?: string };
    };
    if (!response.ok || !body.scan_id) {
      errorMessage = body.error?.message || "Unable to start the scan engine. Try again in a moment.";
    } else {
      scanId = body.scan_id;
    }
  } catch {
    errorMessage = "Unable to start the scan engine. Confirm the SiteLens API is running, then try again.";
  }

  if (errorMessage || !scanId) {
    failRedirect(errorMessage || "Unable to start the scan engine. Try again in a moment.", parsed.href);
  }

  redirect(`/scan/${scanId}`);
}
