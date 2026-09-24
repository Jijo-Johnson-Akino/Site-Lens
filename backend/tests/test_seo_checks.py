from __future__ import annotations

from backend.tests.seo_helpers import analyze_html, by_id, load_fixture


def test_title_missing() -> None:
    result = analyze_html(load_fixture("seo_missing_title.html"))
    check = by_id(result, "SEO-TITLE-001")
    assert check.status == "fail"
    assert check.severity == "critical"
    assert by_id(result, "SEO-TITLE-002").status == "not_applicable"
    assert by_id(result, "SEO-TITLE-004").status == "not_applicable"


def test_title_empty() -> None:
    result = analyze_html("<html><head><title>   </title></head><body><h1>Hi</h1></body></html>")
    check = by_id(result, "SEO-TITLE-001")
    assert check.status == "fail"
    assert "empty" in check.message.lower()


def test_title_normal() -> None:
    result = analyze_html(load_fixture("seo_good.html"))
    assert by_id(result, "SEO-TITLE-001").status == "pass"
    assert by_id(result, "SEO-TITLE-002").status == "pass"
    assert by_id(result, "SEO-TITLE-004").status == "pass"


def test_title_very_short() -> None:
    result = analyze_html("<html><head><title>Hi</title></head><body><h1>Hi</h1></body></html>")
    check = by_id(result, "SEO-TITLE-002")
    assert check.status == "warning"
    assert "short" in check.message.lower()
    assert "guideline" in (check.why or "").lower()


def test_title_very_long() -> None:
    title = "A" * 80
    result = analyze_html(f"<html><head><title>{title}</title></head><body><h1>Hi</h1></body></html>")
    check = by_id(result, "SEO-TITLE-002")
    assert check.status == "warning"
    assert "long" in check.message.lower()


def test_title_weak_heuristic() -> None:
    result = analyze_html("<html><head><title>Home</title></head><body><h1>Home</h1></body></html>")
    check = by_id(result, "SEO-TITLE-004")
    assert check.status == "warning"
    assert "generic" in check.message.lower()


def test_duplicate_title_is_not_applicable() -> None:
    result = analyze_html(load_fixture("seo_good.html"))
    check = by_id(result, "SEO-TITLE-003")
    assert check.status == "not_applicable"


def test_meta_missing() -> None:
    result = analyze_html(load_fixture("seo_missing_meta.html"))
    assert by_id(result, "SEO-META-001").status == "fail"
    assert by_id(result, "SEO-META-002").status == "not_applicable"
    assert by_id(result, "SEO-META-003").status == "not_applicable"


def test_meta_empty() -> None:
    html = '<html><head><title>Has a descriptive title</title><meta name="description" content="   "></head><body><h1>Hi</h1></body></html>'
    result = analyze_html(html)
    assert by_id(result, "SEO-META-001").status == "pass"
    assert by_id(result, "SEO-META-002").status == "fail"


def test_meta_normal_short_and_long() -> None:
    normal = analyze_html(load_fixture("seo_good.html"))
    assert by_id(normal, "SEO-META-001").status == "pass"
    assert by_id(normal, "SEO-META-002").status == "pass"
    assert by_id(normal, "SEO-META-003").status == "pass"

    short = analyze_html(
        '<html><head><title>Has a descriptive title</title><meta name="description" content="Too short."></head><body><h1>Hi</h1></body></html>'
    )
    assert by_id(short, "SEO-META-003").status == "warning"
    assert "commonly recommended" in by_id(short, "SEO-META-003").message

    long_text = "A" * 200
    long_result = analyze_html(
        f'<html><head><title>Has a descriptive title</title><meta name="description" content="{long_text}"></head><body><h1>Hi</h1></body></html>'
    )
    assert by_id(long_result, "SEO-META-003").status == "warning"


def test_duplicate_meta_is_not_applicable() -> None:
    result = analyze_html(load_fixture("seo_good.html"))
    assert by_id(result, "SEO-META-004").status == "not_applicable"


def test_h1_none_one_multiple_empty() -> None:
    none = analyze_html("<html><head><title>Has a descriptive title</title></head><body><p>No heading</p></body></html>")
    assert by_id(none, "SEO-H1-001").status == "fail"
    assert by_id(none, "SEO-H1-003").status == "not_applicable"

    one = analyze_html(load_fixture("seo_good.html"))
    assert by_id(one, "SEO-H1-001").status == "pass"
    assert by_id(one, "SEO-H1-002").status == "pass"

    bad = analyze_html(load_fixture("seo_bad_headings.html"))
    assert by_id(bad, "SEO-H1-002").status == "warning"
    assert by_id(bad, "SEO-H1-003").status == "fail"
    assert "not automatically an SEO failure" in (by_id(bad, "SEO-H1-002").why or "")
    assert by_id(bad, "SEO-HEAD-001").status == "warning"
    assert "H1 → H4" in (by_id(bad, "SEO-HEAD-001").detected or "")


def test_canonical_missing_valid_invalid_relative() -> None:
    missing = analyze_html("<html><head><title>Has a descriptive title</title></head><body><h1>Hi</h1></body></html>")
    assert by_id(missing, "SEO-CAN-001").status == "fail"
    assert by_id(missing, "SEO-CAN-002").status == "not_applicable"

    valid = analyze_html(load_fixture("seo_good.html"))
    assert by_id(valid, "SEO-CAN-001").status == "pass"
    assert by_id(valid, "SEO-CAN-002").status == "pass"
    assert by_id(valid, "SEO-CAN-003").status == "pass"

    invalid = analyze_html(
        '<html><head><title>Has a descriptive title</title><link rel="canonical" href="ftp://example.com/"></head><body><h1>Hi</h1></body></html>'
    )
    assert by_id(invalid, "SEO-CAN-002").status == "fail"

    relative = analyze_html(
        '<html><head><title>Has a descriptive title</title><link rel="canonical" href="/page"></head><body><h1>Hi</h1></body></html>'
    )
    assert by_id(relative, "SEO-CAN-002").status == "warning"


def test_robots_meta_and_header() -> None:
    missing = analyze_html("<html><head><title>Has a descriptive title</title></head><body><h1>Hi</h1></body></html>")
    assert by_id(missing, "SEO-INDEX-001").status == "pass"
    assert by_id(missing, "SEO-INDEX-002").status == "pass"
    assert result_indexable(missing)

    noindex = analyze_html(
        '<html><head><title>Has a descriptive title</title><meta name="robots" content="noindex, nofollow"></head><body><h1>Hi</h1></body></html>'
    )
    assert by_id(noindex, "SEO-INDEX-001").status == "warning"
    assert "noindex" in by_id(noindex, "SEO-INDEX-001").message.lower()
    assert noindex.indexable.indexable is False

    xrobots = analyze_html(
        "<html><head><title>Has a descriptive title</title></head><body><h1>Hi</h1></body></html>",
        x_robots_tag="none",
    )
    assert by_id(xrobots, "SEO-INDEX-002").status == "warning"
    assert xrobots.indexable.indexable is False


def result_indexable(result) -> bool:
    assert result.indexable.indexable is True
    return True


def test_images_alt_states() -> None:
    good = analyze_html(load_fixture("seo_good.html"))
    assert by_id(good, "SEO-IMG-001").status == "pass"

    missing = analyze_html(load_fixture("seo_missing_images_alt.html"))
    assert by_id(missing, "SEO-IMG-001").status == "warning"
    assert by_id(missing, "SEO-IMG-002").status == "warning"
    assert by_id(missing, "SEO-IMG-003").status == "warning"
    assert "not a substitute" in (by_id(missing, "SEO-IMG-003").message.lower())

    all_missing = analyze_html(
        '<html><head><title>Has a descriptive title</title></head><body><h1>Hi</h1><img src="/a.png"><img src="/b.png"></body></html>'
    )
    assert by_id(all_missing, "SEO-IMG-001").status == "fail"


def test_links_internal_external_empty_fragment() -> None:
    html = """
    <html><head><title>Has a descriptive title</title></head><body>
      <h1>Links</h1>
      <a href="/about">About the company</a>
      <a href="https://example.net/x">Partner site</a>
      <a href="">Empty</a>
      <a href="#">Click here</a>
    </body></html>
    """
    result = analyze_html(html)
    assert by_id(result, "SEO-LINK-001").status == "pass"
    assert "1" in (by_id(result, "SEO-LINK-002").detected or "")
    assert by_id(result, "SEO-LINK-003").status == "fail"
    assert by_id(result, "SEO-LINK-004").status == "warning"
    assert by_id(result, "SEO-LINK-005").status == "warning"


def test_social_present_and_missing() -> None:
    present = analyze_html(load_fixture("seo_good.html"))
    assert by_id(present, "SEO-SOCIAL-001").status == "pass"
    assert by_id(present, "SEO-SOCIAL-004").status == "pass"

    missing = analyze_html("<html><head><title>Has a descriptive title</title></head><body><h1>Hi</h1></body></html>")
    assert by_id(missing, "SEO-SOCIAL-001").status == "warning"
    assert by_id(missing, "SEO-SOCIAL-002").status == "warning"
    assert by_id(missing, "SEO-SOCIAL-003").status == "warning"
    assert by_id(missing, "SEO-SOCIAL-004").status == "warning"
    assert by_id(missing, "SEO-SOCIAL-004").severity == "low"


def test_https_and_robots_txt_and_sitemap() -> None:
    http_page = analyze_html(
        load_fixture("seo_good.html"),
        page_url="http://example.com/",
        final_url="http://example.com/",
    )
    assert by_id(http_page, "SEO-URL-001").status == "fail"

    missing_robots = analyze_html(
        load_fixture("seo_good.html"),
        robots_txt={"exists": False, "status_code": 404, "body": None},
        sitemap={"exists": False, "status_code": 404, "body": None},
    )
    assert by_id(missing_robots, "SEO-ROBOTS-001").status == "fail"
    assert by_id(missing_robots, "SEO-SITEMAP-001").status == "fail"

    html_robots = analyze_html(
        load_fixture("seo_good.html"),
        robots_txt={"exists": True, "status_code": 200, "body": "<html><title>Not robots</title></html>"},
    )
    assert by_id(html_robots, "SEO-ROBOTS-003").status == "fail"


def test_good_fixture_has_no_hardcoded_score() -> None:
    result = analyze_html(load_fixture("seo_good.html"))
    assert 0 <= result.score <= 100
    assert result.score != 0
    assert result.summary.failed == 0
    ids = {check.check_id for check in result.checks}
    assert len(ids) >= 40
    assert "SEO-TITLE-001" in ids
    assert result.narrative.startswith("SEO Score:")
