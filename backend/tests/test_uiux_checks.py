from __future__ import annotations

from backend.analyzers.uiux.analyzer import analyze_snapshots
from backend.tests.uiux_helpers import analyze_one, by_id, snapshot_from_parts


def test_responsive_overflow_and_fixed_width() -> None:
    clean = analyze_one(snapshot_from_parts("mobile"))
    assert by_id(clean, "UX-RESP-001", "mobile").status == "pass"
    assert by_id(clean, "UX-RESP-002", "mobile").status == "pass"

    overflow = analyze_one(
        snapshot_from_parts(
            "mobile",
            overflow=True,
            overflow_px=46,
            overflowing=[{"selector": ".hero-container", "overflow_px": 46, "width": 436}],
            fixed_width=[{"selector": ".wide", "width": 1200}],
        )
    )
    assert by_id(overflow, "UX-RESP-001", "mobile").status == "fail"
    assert "46px" in (by_id(overflow, "UX-RESP-001", "mobile").detected or "")
    assert by_id(overflow, "UX-RESP-002", "mobile").status == "fail"
    assert by_id(overflow, "UX-RESP-002", "mobile").affected_element == ".hero-container"
    assert by_id(overflow, "UX-RESP-003", "mobile").status == "warning"
    assert by_id(analyze_one(snapshot_from_parts("desktop")), "UX-RESP-003", "desktop").status == "not_applicable"


def test_off_screen_and_overlap() -> None:
    overlap = analyze_one(
        snapshot_from_parts(
            "desktop",
            overlapping=[{"a": "p.block-a", "b": "p.block-b", "intersection_px": 8000}],
        )
    )
    assert by_id(overlap, "UX-LAYOUT-002", "desktop").status == "warning"
    none = analyze_one(snapshot_from_parts("desktop"))
    assert by_id(none, "UX-LAYOUT-002", "desktop").status == "pass"

    off = analyze_one(snapshot_from_parts("mobile", offscreen=[{"selector": "h1", "left": -640}]))
    assert by_id(off, "UX-LAYOUT-003", "mobile").status == "fail"


def test_navigation_exists_missing_and_overflow() -> None:
    present = analyze_one(snapshot_from_parts("desktop"))
    assert by_id(present, "UX-NAV-001", "desktop").status == "pass"
    assert by_id(present, "UX-NAV-002", "desktop").status == "pass"
    assert by_id(present, "UX-NAV-003", "desktop").status == "pass"

    missing = analyze_one(snapshot_from_parts("mobile", nav_exists=False, nav_visible=False, nav_links=0, logo={"exists": False}))
    assert by_id(missing, "UX-NAV-001", "mobile").status == "fail"
    assert by_id(missing, "UX-NAV-002", "mobile").status == "not_applicable"
    assert by_id(missing, "UX-NAV-004", "mobile").status == "not_applicable"

    overflowing = analyze_one(snapshot_from_parts("mobile", nav_overflow=True, menu_button=None))
    assert by_id(overflowing, "UX-NAV-003", "mobile").status == "fail"
    with_menu = analyze_one(snapshot_from_parts("mobile", nav_visible=False, menu_button="button.menu"))
    assert by_id(with_menu, "UX-NAV-002", "mobile").status == "pass"
    assert by_id(with_menu, "UX-RESP-004", "mobile").status in {"pass", "warning"}


def test_buttons_visible_empty_clipped() -> None:
    visible = analyze_one(snapshot_from_parts("desktop"))
    assert by_id(visible, "UX-INTERACT-001", "desktop").status == "pass"
    assert by_id(visible, "UX-CTA-002", "desktop").status == "pass"
    assert by_id(visible, "UX-CTA-003", "desktop").status == "pass"

    empty = analyze_one(
        snapshot_from_parts(
            "mobile",
            buttons=[{"selector": "button.empty", "text": "", "empty": True, "disabled": False, "visible": True, "in_viewport": True, "clipped": False, "pointer_events": "auto", "width": 80, "height": 32}],
            cta={"exists": False, "visible": False, "clipped": False},
        )
    )
    assert by_id(empty, "UX-CTA-004", "mobile").status == "fail"
    assert by_id(empty, "UX-CTA-001", "mobile").status == "warning"

    clipped = analyze_one(
        snapshot_from_parts(
            "mobile",
            cta={"exists": True, "selector": "a.cta", "text": "Get Started", "visible": True, "in_viewport": True, "clipped": True, "overflow_px": 28},
        )
    )
    assert by_id(clipped, "UX-CTA-003", "mobile").status == "fail"


def test_images_loaded_broken_overflow_distorted() -> None:
    loaded = analyze_one(
        snapshot_from_parts(
            "desktop",
            images=[{"selector": "img.ok", "visible": True, "broken": False, "overflow": False, "distorted": False, "width": 40, "height": 40, "natural_width": 40, "natural_height": 40}],
        )
    )
    assert by_id(loaded, "UX-IMG-001", "desktop").status == "pass"
    assert by_id(loaded, "UX-IMG-002", "desktop").status == "pass"
    assert by_id(loaded, "UX-IMG-003", "desktop").status == "pass"

    broken = analyze_one(
        snapshot_from_parts(
            "mobile",
            images=[{"selector": "img#broken", "visible": True, "broken": True, "overflow": False, "distorted": False, "width": 24, "height": 24, "natural_width": 0, "natural_height": 0}],
        )
    )
    assert by_id(broken, "UX-IMG-001", "mobile").status == "fail"

    overflow = analyze_one(
        snapshot_from_parts(
            "mobile",
            images=[{"selector": "img.wide", "visible": True, "broken": False, "overflow": True, "distorted": False, "width": 900, "height": 200, "natural_width": 900, "natural_height": 200}],
        )
    )
    assert by_id(overflow, "UX-IMG-002", "mobile").status == "warning"

    distorted = analyze_one(
        snapshot_from_parts(
            "desktop",
            images=[{"selector": "img.stretch", "visible": True, "broken": False, "overflow": False, "distorted": True, "width": 400, "height": 40, "natural_width": 200, "natural_height": 200}],
        )
    )
    assert by_id(distorted, "UX-IMG-003", "desktop").status == "warning"


def test_forms_exist_and_submit() -> None:
    missing = analyze_one(snapshot_from_parts("desktop"))
    assert by_id(missing, "UX-FORM-001", "desktop").status == "not_applicable"
    assert by_id(missing, "UX-FORM-003", "desktop").status == "not_applicable"

    present = analyze_one(
        snapshot_from_parts(
            "desktop",
            forms=[{"selector": "form", "visible": True, "fields": 1, "labeled": 1, "has_submit": True}],
        )
    )
    assert by_id(present, "UX-FORM-001", "desktop").status == "pass"
    assert by_id(present, "UX-FORM-002", "desktop").status == "pass"
    assert by_id(present, "UX-FORM-003", "desktop").status == "pass"

    no_submit = analyze_one(
        snapshot_from_parts(
            "mobile",
            forms=[{"selector": "form", "visible": True, "fields": 2, "labeled": 0, "has_submit": False}],
        )
    )
    assert by_id(no_submit, "UX-FORM-002", "mobile").status == "warning"
    assert by_id(no_submit, "UX-FORM-003", "mobile").status == "fail"


def test_overlay_is_observational() -> None:
    overlay = analyze_one(
        snapshot_from_parts(
            "desktop",
            overlays=[{"selector": "div.cookie", "coverage": 0.82, "keywords": True, "text": "cookie privacy"}],
        )
    )
    check = by_id(overlay, "UX-CONTENT-003", "desktop")
    assert check.status == "warning"
    assert "overlay" in check.message.lower()


def test_three_viewports_emit_checks() -> None:
    result = analyze_snapshots(
        [
            snapshot_from_parts("desktop"),
            snapshot_from_parts("tablet"),
            snapshot_from_parts("mobile"),
        ]
    )
    viewports = {check.viewport for check in result.checks}
    assert viewports == {"desktop", "tablet", "mobile"}
    assert len(result.checks) >= 90
    ids = {check.check_id for check in result.checks}
    assert "UX-RESP-001" in ids
    assert "UX-NAV-001" in ids
    assert "UX-LAYOUT-001" in ids
    assert all("beautiful" not in check.message.lower() for check in result.checks)
    assert all("ugly" not in check.message.lower() for check in result.checks)
