from backend.analyzers.accessibility.checks.aria import run as aria
from backend.analyzers.accessibility.checks.contrast import run as contrast
from backend.analyzers.accessibility.checks.controls import run as controls
from backend.analyzers.accessibility.checks.document import run as document
from backend.analyzers.accessibility.checks.forms import run as forms
from backend.analyzers.accessibility.checks.headings import run as headings
from backend.analyzers.accessibility.checks.images import run as images
from backend.analyzers.accessibility.checks.keyboard import run as keyboard
from backend.analyzers.accessibility.checks.landmarks import run as landmarks
from backend.analyzers.accessibility.checks.links import run as links
from backend.analyzers.accessibility.checks.media import run as media
from backend.analyzers.accessibility.checks.other import run as other
from backend.analyzers.accessibility.checks.tables import run as tables

CHECK_RUNNERS = (
    document,
    landmarks,
    headings,
    images,
    links,
    controls,
    forms,
    aria,
    keyboard,
    tables,
    media,
    contrast,
    other,
)

__all__ = ["CHECK_RUNNERS"]
