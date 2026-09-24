from backend.analyzers.trust.checks import about, authorship, business_info, consistency, contact, credentials
from backend.analyzers.trust.checks import identity, policies, security_signals, social_proof, transparency

SITE_RUNNERS = (
    identity.run_site,
    contact.run_site,
    about.run_site,
    policies.run_site,
    authorship.run_site,
    social_proof.run_site,
    credentials.run_site,
    business_info.run_site,
    security_signals.run_site,
    transparency.run_site,
    consistency.run_site,
)

PAGE_RUNNERS = (
    contact.run_page,
    authorship.run_page,
    security_signals.run_page,
)
