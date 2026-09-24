from __future__ import annotations

from backend.analyzers.uiux.checks._util import ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    images = [item for item in (snapshot.images or []) if item.get("visible") or item.get("broken")]
    broken = [item for item in images if item.get("broken")]
    overflow = [item for item in images if item.get("overflow") and item.get("visible")]
    distorted = [item for item in images if item.get("distorted") and item.get("visible") and not item.get("broken")]
    name = viewport_name(snapshot)
    checks: list[CheckResult] = []

    if not images:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-001",
                name="Images load",
                group="images",
                status="not_applicable",
                severity="high",
                message="No images were present to evaluate.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-002",
                name="Images stay in layout",
                group="images",
                status="not_applicable",
                severity="medium",
                message="Image overflow was not evaluated because no images were present.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-003",
                name="Images are not severely distorted",
                group="images",
                status="not_applicable",
                severity="low",
                message="Image dimensions were not evaluated because no images were present.",
            )
        )
        return checks

    if broken:
        first = broken[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-001",
                name="Images load",
                group="images",
                status="fail",
                severity="high",
                message="A broken image was detected.",
                recommendation="Fix the image URL or provide a valid fallback so the asset loads.",
                detected=f"broken={len(broken)} viewport={name}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-001",
                name="Images load",
                group="images",
                status="pass",
                severity="high",
                message="Visible images loaded successfully.",
                detected=str(len(images)),
            )
        )

    if overflow:
        first = overflow[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-002",
                name="Images stay in layout",
                group="images",
                status="warning",
                severity="medium",
                message="An image extends outside its container or the viewport.",
                recommendation="Constrain the image with max-width so it remains inside its layout.",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-002",
                name="Images stay in layout",
                group="images",
                status="pass",
                severity="medium",
                message="Images stay inside their containers and the viewport.",
            )
        )

    if distorted:
        first = distorted[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-003",
                name="Images are not severely distorted",
                group="images",
                status="warning",
                severity="low",
                message="An image appears severely distorted compared with its natural dimensions.",
                recommendation="Preserve the image aspect ratio when setting width and height.",
                detected=f"rendered={round(first.get('width') or 0)}x{round(first.get('height') or 0)} natural={first.get('natural_width')}x{first.get('natural_height')}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-IMG-003",
                name="Images are not severely distorted",
                group="images",
                status="pass",
                severity="low",
                message="No severely distorted images were detected.",
            )
        )
    return checks
