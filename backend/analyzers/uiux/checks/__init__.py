from backend.analyzers.uiux.checks.buttons import run as buttons
from backend.analyzers.uiux.checks.content import run as content
from backend.analyzers.uiux.checks.forms import run as forms
from backend.analyzers.uiux.checks.images import run as images
from backend.analyzers.uiux.checks.interactions import run as interactions
from backend.analyzers.uiux.checks.layout import run as layout
from backend.analyzers.uiux.checks.navigation import run as navigation
from backend.analyzers.uiux.checks.responsive import run as responsive
from backend.analyzers.uiux.checks.typography import run as typography

CHECK_RUNNERS = (
    responsive,
    navigation,
    buttons,
    typography,
    content,
    interactions,
    forms,
    images,
    layout,
)

__all__ = ["CHECK_RUNNERS"]
