"""Page URL identity. Re-exports the shared normalizer."""

from backend.services.url_identity import normalize_page_url

__all__ = ["normalize_page_url"]
