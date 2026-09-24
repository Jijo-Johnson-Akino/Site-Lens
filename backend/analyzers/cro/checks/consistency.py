"""CTA consistency checks live in clarity.py to avoid duplicate findings."""

from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(_ctx: PageCroContext) -> list[CheckResult]:
    return []
