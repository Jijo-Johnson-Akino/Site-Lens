from backend.analyzers.aeo.checks.answers import run as answers
from backend.analyzers.aeo.checks.ai_accessibility import run as ai_accessibility
from backend.analyzers.aeo.checks.author import run as authorship
from backend.analyzers.aeo.checks.content_structure import run as content_structure
from backend.analyzers.aeo.checks.entity import run as entity
from backend.analyzers.aeo.checks.extractability import run as extractability
from backend.analyzers.aeo.checks.faq import run as faq
from backend.analyzers.aeo.checks.organization import run as organization
from backend.analyzers.aeo.checks.semantic import run as semantic
from backend.analyzers.aeo.checks.structured_data import run as structured_data

CHECK_RUNNERS = (
    entity,
    answers,
    faq,
    content_structure,
    semantic,
    authorship,
    organization,
    structured_data,
    extractability,
    ai_accessibility,
)

__all__ = ["CHECK_RUNNERS"]
