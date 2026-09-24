from __future__ import annotations

from backend.analyzers.aeo.checks._util import extracted_names, first_description, name_tokens, page_url, primary_name, types_present
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check
from backend.parser.structured_data import IDENTITY_TYPES


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    return [_brand_name(ctx, page), _org_schema(ctx, page), _description(ctx, page), _consistency(ctx, page)]


def _brand_name(ctx: AeoContext, page: str) -> CheckResult:
    why = "Answer systems need a stable name to associate the page with an organization, brand, or product. The extracted string is not assumed to be a legal company name."
    name = primary_name(ctx)
    names = extracted_names(ctx)
    if name and name_tokens(name):
        sources = ", ".join(f"{key}={value}" for key, value in names.items())
        return make_check(
            check_id="AEO-ENTITY-001",
            name="Organization identity is clearly defined",
            group="entity_understanding",
            status="pass",
            severity="medium",
            message="The page clearly identifies the organization, brand, or site name.",
            why=why,
            detected=sources,
            page_url=page,
        )
    return make_check(
        check_id="AEO-ENTITY-001",
        name="Organization identity is clearly defined",
        group="entity_understanding",
        status="fail",
        severity="medium",
        message="The page does not clearly identify the organization.",
        recommendation="Clearly state the organization or brand name and what it does.",
        why=why,
        detected="No usable name was found in the title, H1, header, or identity schema.",
        page_url=page,
    )


def _org_schema(ctx: AeoContext, page: str) -> CheckResult:
    why = "Organization, LocalBusiness, Corporation, Person, or WebSite JSON-LD can make the entity explicit. Absence is not treated as a critical failure."
    present = IDENTITY_TYPES.intersection(types_present(ctx))
    if present:
        return make_check(
            check_id="AEO-ENTITY-002",
            name="Organization schema",
            group="entity_understanding",
            status="pass",
            severity="medium",
            message="Identity-related structured data was found.",
            why=why,
            detected=", ".join(sorted(present)),
            page_url=page,
        )
    return make_check(
        check_id="AEO-ENTITY-002",
        name="Organization schema",
        group="entity_understanding",
        status="warning",
        severity="medium",
        message="No Organization, LocalBusiness, Corporation, Person, or WebSite JSON-LD was found.",
        recommendation="Add Organization or WebSite JSON-LD if you want the entity to be explicit for machine readers.",
        why=why,
        detected="No identity schema types detected.",
        page_url=page,
    )


def _description(ctx: AeoContext, page: str) -> CheckResult:
    why = "A concise description of what the organization or product does is an observable content signal. It is not a ranking prediction."
    description = first_description(ctx)
    if description and len(description) >= 40:
        return make_check(
            check_id="AEO-ENTITY-003",
            name="Clear entity description",
            group="entity_understanding",
            status="pass",
            severity="medium",
            message="The homepage contains a concise description of what the site or organization does.",
            why=why,
            detected=description[:240],
            page_url=page,
        )
    return make_check(
        check_id="AEO-ENTITY-003",
        name="Clear entity description",
        group="entity_understanding",
        status="fail",
        severity="medium",
        message="The page does not include a concise description of the organization or product.",
        recommendation="Add a short statement of what the organization or product does, near the top of the page or in Organization schema.",
        why=why,
        detected="No description of at least 40 characters was found in schema, meta description, or introductory copy.",
        page_url=page,
    )


def _consistency(ctx: AeoContext, page: str) -> CheckResult:
    why = "Large mismatches between the title, H1, and identity schema can make the entity harder to resolve. Minor capitalization differences are ignored."
    names = extracted_names(ctx)
    if len(names) < 2:
        return make_check(
            check_id="AEO-ENTITY-004",
            name="Brand consistency",
            group="entity_understanding",
            status="not_applicable",
            severity="low",
            message="Brand consistency was not evaluated because fewer than two name sources were found.",
            why=why,
            page_url=page,
        )
    token_sets = {key: name_tokens(value) for key, value in names.items() if name_tokens(value)}
    keys = list(token_sets)
    mismatches = []
    for index, left in enumerate(keys):
        for right in keys[index + 1 :]:
            if token_sets[left].isdisjoint(token_sets[right]):
                mismatches.append(f"{left} vs {right}")
    if mismatches:
        detected = "; ".join(f"{key}={names[key]}" for key in names)
        return make_check(
            check_id="AEO-ENTITY-004",
            name="Brand consistency",
            group="entity_understanding",
            status="warning",
            severity="low",
            message="Extracted names do not share obvious tokens across title, heading, and schema sources.",
            recommendation="Use a consistent brand or site name across the title, H1, and identity schema where practical.",
            why=why,
            detected=detected + f". Mismatches: {', '.join(mismatches)}",
            page_url=page,
        )
    return make_check(
        check_id="AEO-ENTITY-004",
        name="Brand consistency",
        group="entity_understanding",
        status="pass",
        severity="low",
        message="Extracted names are consistent enough across the available sources.",
        why=why,
        detected="; ".join(f"{key}={value}" for key, value in names.items()),
        page_url=page,
    )
