# SiteLens Health Score

The Health Score is an aggregation of existing analyzer scores. It does not crawl pages, re-run analyzers, or invent checks.

## Formula

`overall = sum(category_score × category_weight) / sum(weights of available categories)`

Unavailable or failed categories are excluded. They are not treated as zero.

## Default weights

| Category | Weight |
| --- | --- |
| SEO | 15 |
| AEO / AI Search Readiness | 10 |
| UI/UX | 10 |
| Accessibility | 10 |
| Performance | 15 |
| Content | 10 |
| Structured Data | 5 |
| Mobile | 10 |
| CRO | 7.5 |
| Trust & Credibility | 7.5 |

Total = 100. Website Architecture is informational and is not included.

## Score coverage

Score coverage is the share of configured category weight that had a usable analyzer score. It is not a statistical confidence interval.

- 100%: complete
- 80–99.99%: partial
- 50–79.99%: limited
- below 50%: unavailable / insufficient

## Score bands

These labels describe the numeric band only. They are not a judgment of the business.

- 90–100 Excellent
- 75–89 Good
- 60–74 Needs Improvement
- 40–59 Poor
- 0–39 Critical

## Calculation version

`calculation_version = 1.0`

If the formula or weights change, increment this version. Previous score records keep the version that produced them.

## APIs

- `GET /api/scans/{scan_id}/score`
- `GET /api/scans/{scan_id}/score/methodology`
- `GET /api/scans/{scan_id}/report` (Phase 20 presentation layer; uses stored Health Score values)

Frontend: `/scan/[scanId]/score`

Issue counts are supporting context. They are not subtracted from analyzer scores.

## Limitation

The SiteLens Health Score is a composite website analysis metric based on the categories included in the scan. It is not a prediction of search rankings, traffic, revenue, conversions, business success, or user trust.
