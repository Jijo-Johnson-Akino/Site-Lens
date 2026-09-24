from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from backend.analyzers.uiux.checks._util import page_url, ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def _logo_href_ok(href: str, final_url: str) -> bool:
    raw = (href or "").strip()
    if not raw or raw.lower().startswith("javascript:") or raw == "#":
        return False
    resolved = urljoin(final_url, raw)
    current = urlsplit(final_url)
    target = urlsplit(resolved)
    if target.scheme not in {"http", "https"}:
        return False
    if target.netloc.lower() != current.netloc.lower():
        return True
    path = target.path or "/"
    return path in {"/", "/index", "/index.html", "/home", "/home/"} or path == (current.path or "/")


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    nav = snapshot.navigation or {}
    name = viewport_name(snapshot)
    exists = bool(nav.get("exists") or nav.get("has_nav_element"))
    visible = bool(nav.get("visible"))
    links = int(nav.get("links") or 0)
    overflow = bool(nav.get("overflow"))
    checks: list[CheckResult] = []

    if exists:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-001",
                name="Primary navigation exists",
                group="navigation",
                status="pass",
                severity="high",
                message="Navigation is present.",
                detected=f"nav_element={bool(nav.get('has_nav_element'))} links={links}",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-001",
                name="Primary navigation exists",
                group="navigation",
                status="fail",
                severity="high",
                message="No primary navigation structure was detected.",
                recommendation="Expose a nav landmark or a visible set of primary destination links.",
                detected="No <nav> landmark and fewer than three header links were found.",
            )
        )

    if not exists:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-002",
                name="Navigation visibility",
                group="navigation",
                status="not_applicable",
                severity="medium",
                message="Navigation visibility was not evaluated because no navigation was detected.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-003",
                name="Navigation stays in viewport",
                group="navigation",
                status="not_applicable",
                severity="medium",
                message="Navigation overflow was not evaluated because no navigation was detected.",
            )
        )
    else:
        if visible:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-NAV-002",
                    name="Navigation visibility",
                    group="navigation",
                    status="pass",
                    severity="medium",
                    message=f"Navigation is visible at the {name} viewport.",
                )
            )
        else:
            menu = nav.get("menu_button")
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-NAV-002",
                    name="Navigation visibility",
                    group="navigation",
                    status="pass" if menu else "fail",
                    severity="high",
                    message=(
                        "Navigation is available through a menu control."
                        if menu
                        else f"Navigation is not visible at the {name} viewport."
                    ),
                    recommendation=None if menu else "Keep primary navigation visible or provide a usable menu control.",
                    detected=f"menu_button={menu or 'none'}",
                )
            )
        if overflow:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-NAV-003",
                    name="Navigation stays in viewport",
                    group="navigation",
                    status="fail",
                    severity="high",
                    message="Navigation items extend outside the viewport.",
                    recommendation="Allow navigation to wrap, scroll, or collapse so items remain inside the viewport.",
                    detected=f"Overflow: {int(nav.get('overflow_px') or 0)}px",
                    affected_element=nav.get("overflow_selector"),
                )
            )
        else:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-NAV-003",
                    name="Navigation stays in viewport",
                    group="navigation",
                    status="pass",
                    severity="medium",
                    message="Navigation items stay inside the viewport.",
                )
            )

    logo = nav.get("logo") if isinstance(nav.get("logo"), dict) else None
    if not logo or not logo.get("exists"):
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-004",
                name="Logo or home link",
                group="navigation",
                status="not_applicable",
                severity="low",
                message="No visible logo or header home link was detected.",
            )
        )
    elif _logo_href_ok(str(logo.get("href") or ""), page_url(snapshot)):
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-004",
                name="Logo or home link",
                group="navigation",
                status="pass",
                severity="low",
                message="A header logo or home link points to a usable destination.",
                detected=f"href={logo.get('href')}",
                affected_element=logo.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-NAV-004",
                name="Logo or home link",
                group="navigation",
                status="warning",
                severity="low",
                message="A logo or header mark is visible but does not point to a usable home destination.",
                recommendation="Point the logo or header identity link to the homepage.",
                detected=f"href={logo.get('href') or 'missing'}",
                affected_element=logo.get("selector"),
            )
        )
    return checks
