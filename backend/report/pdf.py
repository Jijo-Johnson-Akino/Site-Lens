"""Render an assembled SiteLens report as a PDF file. Presentation only."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from fpdf import FPDF

NAVY = (15, 23, 42)
TEAL = (13, 148, 136)
SLATE = (71, 85, 105)
LINE = (226, 232, 240)
WRAP = {"new_x": "LMARGIN", "new_y": "NEXT"}


def report_pdf_filename(payload: dict[str, Any]) -> str:
    scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else {}
    host = _host(str(scan.get("website") or scan.get("url") or "website"))
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", host).strip("-._") or "website"
    return f"SiteLens-{safe}-report.pdf"


def render_report_pdf(payload: dict[str, Any]) -> bytes:
    pdf = _ReportPdf()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _cover(pdf, payload)
    _overview(pdf, payload)
    _categories(pdf, payload)
    _issues(pdf, payload)
    _recommendations(pdf, payload)
    _methodology(pdf, payload)
    return bytes(pdf.output())


def _host(url: str) -> str:
    parsed = urlsplit(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or url).split("@")[-1]
    return host.split(":")[0].removeprefix("www.") or url


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).encode("latin-1", "replace").decode("latin-1")


def _score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(int(value) if float(value).is_integer() else value)
    return "Unavailable"


class _ReportPdf(FPDF):
    def header(self) -> None:
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 12, "F")
        self.set_xy(16, 3.5)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, "SiteLens  |  Website Analysis Report", **WRAP)
        self.set_y(16)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*LINE)
        self.line(16, self.get_y(), self.w - 16, self.get_y())
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        self.set_y(-11)
        self.cell(0, 6, f"Confidential  ·  Page {self.page_no()}", align="C", **WRAP)


def _heading(pdf: FPDF, title: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, _text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*TEAL)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(16, y, 52, y)
    pdf.ln(3)


def _body(pdf: FPDF, text: str, *, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 5, _text(text), **WRAP)


def _muted(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(0, 4.5, _text(text), **WRAP)


def _kv_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SLATE)
    pdf.cell(42, 6, _text(label))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 6, _text(value), **WRAP)


def _cover(pdf: FPDF, payload: dict[str, Any]) -> None:
    scan = payload.get("scan") if isinstance(payload.get("scan"), dict) else {}
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    website = str(scan.get("website") or scan.get("url") or "Unavailable")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 10, "Website Analysis Report", **WRAP)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*TEAL)
    pdf.multi_cell(0, 8, _text(_host(website)), **WRAP)
    pdf.ln(1)
    _muted(pdf, website)
    pdf.ln(3)
    status = str(payload.get("report_status") or scan.get("status") or "ready").replace("_", " ").title()
    _kv_row(pdf, "Report status", status)
    _kv_row(pdf, "Analyzed", str(scan.get("analyzed_at") or scan.get("completed_at") or "Unavailable"))
    _kv_row(pdf, "Health score", f"{_score(overview.get('overall_score'))} / 100")
    _kv_row(pdf, "Pages analyzed", _score(overview.get("pages_analyzed")))
    _kv_row(pdf, "Issues", _score(overview.get("issues_detected")))
    _kv_row(pdf, "Recommendations", _score(overview.get("recommendations")))


def _overview(pdf: FPDF, payload: dict[str, Any]) -> None:
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    pages = payload.get("pages") if isinstance(payload.get("pages"), dict) else {}
    _heading(pdf, "Overview")
    coverage = overview.get("score_coverage")
    band = overview.get("score_band") or overview.get("score_status") or ""
    lines = [
        f"Overall health: {_score(overview.get('overall_score'))} / 100"
        + (f" ({band})" if band else ""),
        f"Score coverage: {_score(coverage)}%" if coverage is not None else "Score coverage: Unavailable",
        f"Categories analyzed: {overview.get('categories_analyzed') or 0} of {overview.get('categories_configured') or 0}",
    ]
    summary = pages.get("summary") if isinstance(pages.get("summary"), dict) else {}
    if pages.get("available"):
        lines.append(
            f"Pages crawled: {summary.get('crawled') or 0}  ·  discovered: {summary.get('discovered') or 0}"
        )
    _body(pdf, "\n".join(lines))


def _categories(pdf: FPDF, payload: dict[str, Any]) -> None:
    rows = payload.get("categories") if isinstance(payload.get("categories"), list) else []
    if not rows:
        return
    _heading(pdf, "Scores by category")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*SLATE)
    pdf.cell(78, 6, "Category")
    pdf.cell(28, 6, "Score")
    pdf.cell(28, 6, "Status", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINE)
    pdf.line(16, pdf.get_y(), pdf.w - 16, pdf.get_y())
    for row in rows:
        if not isinstance(row, dict):
            continue
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*NAVY)
        name = str(row.get("name") or row.get("category") or "")
        score = _score(row.get("score")) if row.get("available") else "Unavailable"
        status = str(row.get("status") or "").replace("_", " ").title()
        pdf.cell(78, 6, _text(name))
        pdf.cell(28, 6, _text(score))
        pdf.cell(28, 6, _text(status), new_x="LMARGIN", new_y="NEXT")


def _issues(pdf: FPDF, payload: dict[str, Any]) -> None:
    issues = payload.get("issues") if isinstance(payload.get("issues"), dict) else {}
    items = issues.get("priority_issues") if isinstance(issues.get("priority_issues"), list) else []
    if not items:
        items = payload.get("priority_issues") if isinstance(payload.get("priority_issues"), list) else []
    _heading(pdf, "Priority issues")
    if not items:
        _muted(pdf, str(issues.get("empty_message") or "No issues were detected in the completed analysis."))
        return
    by_severity = issues.get("by_severity") if isinstance(issues.get("by_severity"), dict) else {}
    if by_severity:
        counts = "  ·  ".join(
            f"{key.title()} {value}"
            for key, value in by_severity.items()
            if value
        )
        if counts:
            _muted(pdf, f"Total {issues.get('total') or len(items)}. {counts}")
            pdf.ln(1)
    for item in items[:12]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Issue")
        severity = str(item.get("severity") or "").title()
        category = str(item.get("category") or "")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 5, _text(f"{severity}  ·  {category}: {title}" if category else f"{severity}: {title}"), **WRAP)
        detail = item.get("whats_wrong") or item.get("description") or item.get("why_it_matters")
        if detail:
            _muted(pdf, str(detail))
        pdf.ln(1)


def _recommendations(pdf: FPDF, payload: dict[str, Any]) -> None:
    recs = payload.get("recommendations") if isinstance(payload.get("recommendations"), dict) else {}
    items = recs.get("items") if isinstance(recs.get("items"), list) else []
    _heading(pdf, "Recommendations")
    if not items:
        _muted(pdf, str(recs.get("empty_message") or "No recommendations were generated from the available findings."))
        return
    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Recommendation")
        priority = str(item.get("priority") or "").title()
        category = str(item.get("category") or "")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 5, _text(f"{priority}  ·  {title}"), **WRAP)
        summary = item.get("action_summary") or item.get("summary")
        meta = "  ·  ".join(part for part in [category, summary] if part)
        if meta:
            _muted(pdf, str(meta))
        pdf.ln(1)


def _methodology(pdf: FPDF, payload: dict[str, Any]) -> None:
    methodology = payload.get("methodology") if isinstance(payload.get("methodology"), dict) else {}
    paragraphs = methodology.get("paragraphs") if isinstance(methodology.get("paragraphs"), list) else []
    limitations = payload.get("limitations") if isinstance(payload.get("limitations"), list) else []
    if not paragraphs and not limitations:
        return
    _heading(pdf, "Methodology")
    for paragraph in paragraphs:
        _body(pdf, str(paragraph), size=9)
        pdf.ln(1)
    if limitations:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Limitations", new_x="LMARGIN", new_y="NEXT")
        for item in limitations:
            _muted(pdf, f"- {item}")
