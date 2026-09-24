"""Load issue-based recommendation rules once."""

from __future__ import annotations

from backend.recommendations import registry as registry_module

_LOADED = False


def load_rules() -> None:
    global _LOADED
    if _LOADED:
        return
    from backend.recommendations.rules import accessibility as _accessibility
    from backend.recommendations.rules import aeo as _aeo
    from backend.recommendations.rules import content as _content
    from backend.recommendations.rules import cro as _cro
    from backend.recommendations.rules import trust as _trust
    from backend.recommendations.rules import mobile as _mobile
    from backend.recommendations.rules import performance as _performance
    from backend.recommendations.rules import seo as _seo
    from backend.recommendations.rules import structured_data as _structured_data
    from backend.recommendations.rules import uiux as _uiux

    _ = (
        _seo,
        _aeo,
        _uiux,
        _accessibility,
        _performance,
        _content,
        _structured_data,
        _mobile,
        _cro,
        _trust,
    )
    _LOADED = True
