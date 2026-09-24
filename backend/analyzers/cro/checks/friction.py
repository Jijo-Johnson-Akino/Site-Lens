"""Trust signals are recorded as context only. Phase 18 owns Trust & Credibility scoring."""

from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(_ctx: PageCroContext) -> list[CheckResult]:
    return []
