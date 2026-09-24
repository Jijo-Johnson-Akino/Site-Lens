from backend.analyzers.cro.checks import clarity, contact, conversion_paths, cta, forms, friction
from backend.analyzers.cro.checks import mobile, navigation, overlays, pricing, value_proposition

CHECK_RUNNERS = (
    cta.run,
    clarity.run,
    value_proposition.run,
    forms.run,
    conversion_paths.run,
    navigation.run,
    pricing.run,
    contact.run,
    mobile.run,
    overlays.run,
    friction.run,
)
