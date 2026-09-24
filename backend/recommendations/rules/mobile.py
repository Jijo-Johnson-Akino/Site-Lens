from backend.recommendations.registry import rule

RULES = [
    rule(
        "mobile.fix_horizontal_overflow",
        "Mobile",
        "Fix mobile horizontal overflow",
        "Prevent content from extending beyond the mobile viewport.",
        "Horizontal overflow on a mobile viewport forces sideways scrolling and can hide content. Related overflowing images are included when they contribute to the same layout issue.",
        (
            "Inspect overflowing elements at the scanned mobile viewport.",
            "Allow containers and images to shrink or wrap instead of expanding page width.",
            "Recheck the page after layout changes at the same viewport width.",
        ),
        ("mobile.horizontal_overflow", "mobile.layout.001", "mobile.image.overflow"),
        effort="medium",
        impact="high",
    ),
    rule(
        "mobile.increase_touch_target_size",
        "Mobile",
        "Increase touch target size",
        "Enlarge controls that are smaller than the configured mobile touch-target threshold.",
        "Small tap targets are harder to activate accurately on a touch viewport.",
        (
            "Identify buttons, links, and controls below the configured minimum size.",
            "Increase the tap area, including padding if the visible icon must stay small.",
            "Keep adjacent targets spaced so they do not overlap.",
        ),
        ("mobile.touch_target.small", "mobile.touch.002", "mobile.touch.003"),
        effort="medium",
        impact="high",
    ),
    rule(
        "mobile.improve_mobile_text",
        "Mobile",
        "Increase mobile text size",
        "Increase text that is below the configured mobile font-size threshold.",
        "Very small text is harder to read on a mobile viewport. This is a measured size observation.",
        (
            "Identify text below the configured minimum size.",
            "Increase body and control text on the mobile layout.",
            "Recheck wrapping so larger text does not introduce overflow.",
        ),
        ("mobile.type.001",),
        effort="small",
        impact="medium",
    ),
    rule(
        "mobile.review_mobile_overlays",
        "Mobile",
        "Review mobile overlays",
        "Reduce overlays that cover a substantial portion of the initial mobile viewport.",
        "Promotional or consent overlays can hide primary content on small screens. Coverage is measured on the initial viewport.",
        (
            "Identify overlays whose coverage exceeds the configured threshold.",
            "Ensure the overlay does not hide primary content or navigation on first paint.",
            "Provide a clear way to dismiss the overlay without covering the whole viewport.",
        ),
        ("mobile.overlay.001",),
        effort="medium",
        impact="medium",
    ),
]
