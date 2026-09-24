from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AeoContext:
    """Normalized website data collected by the scan engine. No extra HTTP from checks."""

    page_url: str
    final_url: str
    status_code: int | None
    html: dict
    robots_txt: dict
    llms_txt: dict
