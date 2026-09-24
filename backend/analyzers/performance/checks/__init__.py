from backend.analyzers.performance.checks.blocking import run as blocking
from backend.analyzers.performance.checks.caching import run as caching
from backend.analyzers.performance.checks.compression import run as compression
from backend.analyzers.performance.checks.css import run as css
from backend.analyzers.performance.checks.fonts import run as fonts
from backend.analyzers.performance.checks.images import run as images
from backend.analyzers.performance.checks.javascript import run as javascript
from backend.analyzers.performance.checks.navigation import run as navigation
from backend.analyzers.performance.checks.redirects import run as redirects
from backend.analyzers.performance.checks.resources import run as resources
from backend.analyzers.performance.checks.structure import run as structure
from backend.analyzers.performance.checks.third_party import run as third_party
from backend.analyzers.performance.checks.vitals import run as vitals

CHECK_RUNNERS = (
    vitals,
    navigation,
    redirects,
    javascript,
    css,
    images,
    fonts,
    third_party,
    caching,
    compression,
    blocking,
    structure,
    resources,
)

__all__ = ["CHECK_RUNNERS"]
