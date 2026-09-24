from backend.analyzers.mobile.checks.content import run as content
from backend.analyzers.mobile.checks.cta import run as cta
from backend.analyzers.mobile.checks.forms import run as forms
from backend.analyzers.mobile.checks.images import run as images
from backend.analyzers.mobile.checks.layout import run as layout
from backend.analyzers.mobile.checks.media import run as media
from backend.analyzers.mobile.checks.navigation import run as navigation
from backend.analyzers.mobile.checks.overflow import run as overflow
from backend.analyzers.mobile.checks.overlays import run as overlays
from backend.analyzers.mobile.checks.spacing import run as spacing
from backend.analyzers.mobile.checks.sticky_elements import run as sticky_elements
from backend.analyzers.mobile.checks.tables import run as tables
from backend.analyzers.mobile.checks.touch_targets import run as touch_targets
from backend.analyzers.mobile.checks.typography import run as typography
from backend.analyzers.mobile.checks.viewport import run as viewport

CHECK_RUNNERS = (
    viewport,
    overflow,
    layout,
    navigation,
    typography,
    touch_targets,
    forms,
    images,
    tables,
    media,
    sticky_elements,
    overlays,
    content,
    cta,
    spacing,
)

__all__ = ["CHECK_RUNNERS"]
