from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    media = snapshot.media or []
    if not media:
        return [
            a11y_check(snapshot, check_id="A11Y-MEDIA-001", name="Media elements expose controls", group="media", status="not_applicable", severity="low", message="No audio or video elements were present."),
            a11y_check(snapshot, check_id="A11Y-MEDIA-002", name="Video caption track", group="media", status="not_applicable", severity="low", message="Caption tracks were not evaluated because no media was present."),
        ]
    missing_controls = [item for item in media if not item.get("controls")]
    videos = [item for item in media if item.get("kind") == "video"]
    missing_tracks = [item for item in videos if int(item.get("tracks") or 0) == 0]
    control_status = "warning" if missing_controls else "pass"
    checks = [
        a11y_check(snapshot, check_id="A11Y-MEDIA-001", name="Media elements expose controls", group="media", status=control_status, severity="low", message="A media element does not expose controls." if missing_controls else "Media elements expose controls.", selector=(missing_controls[0].get("selector") if missing_controls else None), affected_element_count=len(missing_controls)),
    ]
    if not videos:
        checks.append(a11y_check(snapshot, check_id="A11Y-MEDIA-002", name="Video caption track", group="media", status="not_applicable", severity="low", message="No video elements were present."))
    elif missing_tracks:
        checks.append(a11y_check(snapshot, check_id="A11Y-MEDIA-002", name="Video caption track", group="media", status="warning", severity="medium", message="A video has no track element. Caption quality cannot be verified automatically.", recommendation="Provide captions where the video includes speech. A track element does not prove captions are correct.", source="manual-review", manual_review=True, selector=missing_tracks[0].get("selector"), affected_element_count=len(missing_tracks), wcag_reference="WCAG 1.2.2"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-MEDIA-002", name="Video caption track", group="media", status="warning", severity="low", message="A track element is present. Whether captions are accurate still requires manual review.", source="manual-review", manual_review=True))
    return checks
