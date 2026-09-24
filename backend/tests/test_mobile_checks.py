from __future__ import annotations

from backend.analyzers.mobile.analyzer import analyze_snapshot
from backend.analyzers.mobile.stub import snapshot_from_parts
from backend.tests.mobile_helpers import by_id


def test_responsive_snapshot_passes_core_layout() -> None:
    result = analyze_snapshot(snapshot_from_parts())
    assert by_id(result, "MOBILE-OVERFLOW-001").status == "pass"
    assert by_id(result, "MOBILE-VIEW-001").status == "pass"
    assert by_id(result, "MOBILE-TOUCH-001").status == "pass"


def test_fixed_width_overflow_finding() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            overflow=True,
            overflow_px=184,
            overflowing=[{"selector": ".pricing-table", "overflow_px": 184, "cause": "fixed_width", "isolated_scroll": False}],
        )
    )
    overflow = by_id(result, "MOBILE-OVERFLOW-001")
    assert overflow.status in {"warning", "fail"}
    assert overflow.selector == ".pricing-table"
    assert overflow.measured_value == 184


def test_oversized_image_finding() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            images=[{"selector": "img.wide", "visible": True, "width": 1200, "overflowing": True, "overflow_px": 810, "responsive": False}],
        )
    )
    assert by_id(result, "MOBILE-IMG-001").status == "warning"


def test_responsive_image_passes() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            images=[{"selector": "img", "visible": True, "width": 358, "overflowing": False, "responsive": True, "srcset": False, "max_width": "100%"}],
        )
    )
    assert by_id(result, "MOBILE-IMG-001").status == "pass"


def test_wide_table_page_overflow() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            tables=[{"selector": "table", "width": 840, "overflowing": True, "isolated_scroll": False, "page_wide": True, "overflow_px": 450}],
        )
    )
    assert by_id(result, "MOBILE-TABLE-001").status in {"warning", "fail"}


def test_responsive_table_isolated_scroll() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            tables=[{"selector": "table", "width": 840, "overflowing": True, "isolated_scroll": True, "page_wide": False, "overflow_px": 450}],
        )
    )
    assert by_id(result, "MOBILE-TABLE-001").status == "pass"
    assert by_id(result, "MOBILE-TABLE-002").status == "pass"


def test_mobile_menu_detected() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(menu_button="button#menu", menu_tested=True, menu_opened=True, nav_visible=False),
    )
    assert by_id(result, "MOBILE-NAV-002").status == "pass"


def test_broken_mobile_menu() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(menu_button="button.hamburger", menu_tested=True, menu_opened=False, nav_visible=False),
    )
    assert by_id(result, "MOBILE-NAV-001").status == "fail"


def test_small_buttons() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            interactive_elements=2,
            touch_items=[
                {"selector": "button.tiny", "width": 20, "height": 20, "min_dim": 20, "below_baseline": True, "very_small": True, "in_paragraph": False},
                {"selector": "button.tiny", "width": 20, "height": 20, "min_dim": 20, "below_baseline": True, "very_small": True, "in_paragraph": False},
            ],
        )
    )
    assert by_id(result, "MOBILE-TOUCH-001").status == "warning"
    assert by_id(result, "MOBILE-TOUCH-002").status == "warning"


def test_proper_touch_targets() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            interactive_elements=2,
            touch_items=[
                {"selector": "button", "width": 80, "height": 44, "min_dim": 44, "below_baseline": False, "very_small": False, "in_paragraph": False},
            ],
        )
    )
    assert by_id(result, "MOBILE-TOUCH-001").status == "pass"
    assert by_id(result, "MOBILE-TOUCH-002").status == "pass"


def test_small_text_warning() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(small_text=[{"selector": "p.fine", "font_size": 9, "high": True, "text": "This paragraph is tiny copy."}]),
    )
    assert by_id(result, "MOBILE-TYPE-001").status == "warning"
    assert by_id(result, "MOBILE-TYPE-001").severity == "high"


def test_clipped_heading() -> None:
    result = analyze_snapshot(snapshot_from_parts(h1_clipped=True, overflowing_headings=[{"selector": "h1", "overflow_px": 40}]))
    assert by_id(result, "MOBILE-CONTENT-001").status == "warning"
    assert by_id(result, "MOBILE-TYPE-003").status == "warning"


def test_wide_form() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            forms=[{"selector": "form", "width": 920, "overflowing": True, "isolated_scroll": False, "controls_outside": 1, "controls": []}],
        )
    )
    assert by_id(result, "MOBILE-FORM-001").status == "warning"


def test_forms_na_when_absent() -> None:
    result = analyze_snapshot(snapshot_from_parts(forms=[]))
    assert by_id(result, "MOBILE-FORM-001").status == "not_applicable"


def test_fixed_banner_coverage() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(sticky=[{"selector": "div.banner", "coverage": 0.47, "position": "fixed"}]),
    )
    assert by_id(result, "MOBILE-FIXED-001").status == "warning"


def test_large_overlay() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(overlays=[{"selector": "div.modal", "coverage": 0.9, "keywords": True}]),
    )
    assert by_id(result, "MOBILE-OVERLAY-001").status == "warning"


def test_cta_outside_viewport() -> None:
    result = analyze_snapshot(
        snapshot_from_parts(
            cta={"exists": True, "selector": "a.cta", "text": "Get Started", "visible": True, "in_viewport": False, "clipped": True, "overflow_px": 130, "width": 120, "height": 44, "min_dim": 44},
        )
    )
    assert by_id(result, "MOBILE-CTA-001").status == "warning"


def test_missing_viewport_meta() -> None:
    result = analyze_snapshot(snapshot_from_parts(viewport_present=False, viewport_content=""))
    assert by_id(result, "MOBILE-VIEW-001").status == "fail"


def test_correct_viewport_meta() -> None:
    result = analyze_snapshot(snapshot_from_parts())
    assert by_id(result, "MOBILE-VIEW-001").status == "pass"
    assert by_id(result, "MOBILE-VIEW-002").status == "pass"
