"use client";

import { ReportDashboard } from "@/components/scan/ReportDashboard";
import type { ScanStatusResponse } from "@/lib/scan/api";

export function ScanOverview({ scan }: { scan: ScanStatusResponse }) {
  return <ReportDashboard scanId={scan.scan_id} current="overview" />;
}
