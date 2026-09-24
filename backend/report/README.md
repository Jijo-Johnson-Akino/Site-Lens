# SiteLens Final Report

The report is a presentation layer over persisted scan results. It does not crawl, re-run analyzers, or invent checks.

## Assembly

Existing scan data → stored analyzer results → Health Score → Unified Issues → Recommendations → Pages → Architecture → CRO → Trust → competitor snapshots → report payload.

`assemble_report` reads stored payloads only. It never calls `calculate_health` or analyzer engines.

## Version

`report_version = 1.0` (layout and aggregation contract)

This is separate from `calculation_version` on the Health Score.

## Status

- `ready` — stored Health Score coverage is complete and analyzer payloads are present
- `partial` — some analyzers, scores, or supporting modules are missing
- `unavailable` — no stored analysis could be assembled

Unavailable category scores are omitted from display as `Unavailable`, never shown as `0`.

## API

`GET /api/scans/{scan_id}/report`

Generated on demand from the scan record. No report snapshot table.

Frontend: `/scan/[scanId]/report`
