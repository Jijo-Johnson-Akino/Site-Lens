from __future__ import annotations

from backend.tests.a11y_helpers import analyze_dom, by_id, snapshot_with


def test_accessible_snapshot_mostly_passes() -> None:
    result = analyze_dom()
    assert result.summary.failed == 0
    assert by_id(result, "A11Y-DOC-001").status == "pass"
    assert by_id(result, "A11Y-IMG-001").status == "pass"
    assert by_id(result, "A11Y-CTRL-001").status == "pass"
    assert by_id(result, "A11Y-FORM-001").status == "pass"
    assert "WCAG" not in result.narrative or "not guarantee WCAG" in result.narrative.lower() or "does not guarantee" in result.narrative.lower()
    assert any("does not guarantee" in line.lower() or "automated" in line.lower() for line in result.limitations)


def test_missing_html_lang() -> None:
    result = analyze_dom(snapshot_with(document={"lang": "", "lang_present": False, "title": "Home", "dir": "ltr"}))
    assert by_id(result, "A11Y-DOC-001").status == "fail"


def test_empty_lang_is_warning() -> None:
    result = analyze_dom(snapshot_with(document={"lang": "", "lang_present": True, "title": "Home", "dir": "ltr"}))
    assert by_id(result, "A11Y-DOC-001").status == "warning"


def test_non_english_language_is_not_a_failure() -> None:
    result = analyze_dom(snapshot_with(document={"lang": "fr", "lang_present": True, "title": "Accueil", "dir": "ltr"}))
    assert by_id(result, "A11Y-DOC-001").status == "pass"
    assert by_id(result, "A11Y-DOC-003").status == "pass"
    assert "english" not in by_id(result, "A11Y-DOC-001").message.lower() or "not required" in (by_id(result, "A11Y-DOC-001").recommendation or "").lower()


def test_missing_title() -> None:
    result = analyze_dom(snapshot_with(document={"lang": "en", "title": "", "dir": "ltr"}))
    assert by_id(result, "A11Y-DOC-002").status == "fail"


def test_image_without_alt() -> None:
    result = analyze_dom(
        snapshot_with(images=[{"selector": "img", "alt": None, "has_alt": False, "in_link": False, "visible": True}])
    )
    check = by_id(result, "A11Y-IMG-001")
    assert check.status == "fail"
    assert check.affected_element_count == 1


def test_decorative_empty_alt_does_not_fail() -> None:
    result = analyze_dom(
        snapshot_with(images=[{"selector": "img", "alt": "", "has_alt": True, "in_link": False, "visible": True}])
    )
    assert by_id(result, "A11Y-IMG-001").status == "pass"
    assert by_id(result, "A11Y-IMG-002").status == "pass"


def test_empty_button() -> None:
    result = analyze_dom(
        snapshot_with(controls=[{"selector": "button", "name": "", "named": False, "disabled": False, "visible": True}])
    )
    assert by_id(result, "A11Y-CTRL-001").status == "fail"


def test_icon_button_with_aria_label_passes() -> None:
    result = analyze_dom(
        snapshot_with(
            controls=[{"selector": "button", "name": "Close", "named": True, "disabled": False, "visible": True}]
        )
    )
    assert by_id(result, "A11Y-CTRL-001").status == "pass"


def test_input_without_label() -> None:
    result = analyze_dom(
        snapshot_with(fields=[{"selector": "input", "named": False, "required": False, "type": "text"}])
    )
    assert by_id(result, "A11Y-FORM-001").status == "fail"


def test_labeled_form_passes() -> None:
    result = analyze_dom()
    assert by_id(result, "A11Y-FORM-001").status == "pass"


def test_duplicate_ids() -> None:
    result = analyze_dom(snapshot_with(ids={"duplicates": ["menu"]}))
    check = by_id(result, "A11Y-ID-001")
    assert check.status == "fail"
    assert "menu" in (check.detected or check.message)


def test_broken_aria_reference() -> None:
    result = analyze_dom(snapshot_with(aria={"broken_refs": [{"selector": "button", "ref": "missing"}], "hidden_focusable": []}))
    assert by_id(result, "A11Y-ARIA-002").status == "fail"


def test_aria_hidden_focusable() -> None:
    result = analyze_dom(snapshot_with(aria={"broken_refs": [], "hidden_focusable": ["button"]}))
    assert by_id(result, "A11Y-ARIA-003").status == "fail"
    assert by_id(result, "A11Y-FOCUS-002").status == "fail"


def test_unnamed_nav_landmarks() -> None:
    result = analyze_dom(snapshot_with(landmarks={"main": 1, "nav": 2, "header": 1, "footer": 0, "unnamed_navs": 2, "empty": []}))
    assert by_id(result, "A11Y-LAND-003").status == "warning"


def test_duplicate_main_landmarks() -> None:
    result = analyze_dom(snapshot_with(landmarks={"main": 2, "nav": 1, "header": 1, "footer": 0, "unnamed_navs": 0, "empty": []}))
    assert by_id(result, "A11Y-LAND-002").status == "fail"


def test_iframe_without_title() -> None:
    result = analyze_dom(snapshot_with(iframes=[{"selector": "iframe", "title": "", "named": False}]))
    assert by_id(result, "A11Y-IFRAME-001").status == "fail"


def test_iframe_with_title_passes() -> None:
    result = analyze_dom(snapshot_with(iframes=[{"selector": "iframe", "title": "YouTube video", "named": True}]))
    assert by_id(result, "A11Y-IFRAME-001").status == "pass"


def test_generic_link_is_warning_not_fail() -> None:
    result = analyze_dom(
        snapshot_with(links=[{"selector": "a", "href": "/x", "name": "click here", "named": True, "visible": True}])
    )
    assert by_id(result, "A11Y-LINK-001").status == "pass"
    assert by_id(result, "A11Y-LINK-002").status == "warning"
    assert by_id(result, "A11Y-LINK-002").manual_review is True


def test_multiple_h1_is_structural_warning() -> None:
    result = analyze_dom(
        snapshot_with(
            headings=[
                {"level": 1, "selector": "h1", "text": "A", "empty": False, "hidden": False},
                {"level": 1, "selector": "h1.second", "text": "B", "empty": False, "hidden": False},
            ]
        )
    )
    assert by_id(result, "A11Y-HEAD-004").status == "warning"
    assert "not automatically" in by_id(result, "A11Y-HEAD-004").message.lower()


def test_heading_hierarchy_jump_is_warning() -> None:
    result = analyze_dom(
        snapshot_with(
            headings=[
                {"level": 1, "selector": "h1", "text": "A", "empty": False, "hidden": False},
                {"level": 4, "selector": "h4", "text": "B", "empty": False, "hidden": False},
            ]
        )
    )
    assert by_id(result, "A11Y-HEAD-003").status == "warning"


def test_skip_link_warning_when_nav_present() -> None:
    result = analyze_dom(snapshot_with(skip={"exists": False, "selector": None}))
    assert by_id(result, "A11Y-LAND-004").status == "warning"


def test_viewport_zoom_restriction_is_warning() -> None:
    result = analyze_dom(snapshot_with(viewport_meta={"content": "width=device-width, user-scalable=no", "present": True}))
    assert by_id(result, "A11Y-VIEW-001").status == "warning"


def test_tables_without_headers_are_warning() -> None:
    result = analyze_dom(snapshot_with(tables=[{"selector": "table", "headers": 0, "caption": False, "role": ""}]))
    assert by_id(result, "A11Y-TABLE-001").status == "warning"
    assert by_id(result, "A11Y-TABLE-002").status == "pass"


def test_dialog_without_name_fails() -> None:
    result = analyze_dom(snapshot_with(dialogs=[{"selector": "[role=dialog]", "named": False, "open": True}]))
    assert by_id(result, "A11Y-DIALOG-001").status == "fail"


def test_media_without_captions_is_manual_review() -> None:
    result = analyze_dom(snapshot_with(media=[{"selector": "video", "kind": "video", "controls": True, "tracks": 0}]))
    check = by_id(result, "A11Y-MEDIA-002")
    assert check.status == "warning"
    assert check.manual_review is True


def test_focus_trap_from_tab_path() -> None:
    result = analyze_dom(
        snapshot_with(
            focus={
                "tabindex_positive": [],
                "hidden_focusable": [],
                "focusable_count": 4,
                "tab_path": ["button#trap"] * 12,
            }
        )
    )
    assert by_id(result, "A11Y-KEY-001").status == "fail"


def test_manual_review_is_not_a_failure() -> None:
    result = analyze_dom(
        snapshot_with(links=[{"selector": "a", "href": "/", "name": "click here", "named": True, "visible": True}])
    )
    assert by_id(result, "A11Y-LINK-002").status != "fail"
    assert result.summary.manual_review >= 1
