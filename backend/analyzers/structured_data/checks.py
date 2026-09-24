from __future__ import annotations

from backend.analyzers.content.models import ContentPageType
from backend.analyzers.structured_data.config import KNOWN_TYPES, PAGE_TYPE_HINTS, TYPE_PARENT, TYPE_RULES
from backend.analyzers.structured_data.consistency import author_mismatch, date_mismatch, first_h1, name_mismatch, price_mismatch
from backend.analyzers.structured_data.entities import conflicting_values, duplicate_groups, index_ids
from backend.analyzers.structured_data.models import CheckResult, JsonLdBlock, SchemaEntity, SchemaRelationship, SocialMeta, make_check
from backend.analyzers.structured_data.validation import context_kind, invalid_urls, same_as_issues
from backend.analyzers.uiux.sanitizer import sanitize_text


def schema_check(page_url: str, **kwargs) -> CheckResult:
    return make_check(page_url=page_url, **kwargs)


def _prop(entity: SchemaEntity, key: str) -> str | None:
    if key == "name":
        return entity.name or entity.properties.get("name") or entity.properties.get("headline")
    if key == "headline":
        return entity.properties.get("headline") or entity.name
    return entity.properties.get(key)


def _rules(type_name: str) -> tuple[list[str], list[str]]:
    core: list[str] = []
    recommended: list[str] = []
    seen: set[str] = set()
    current: str | None = type_name
    while current and current not in seen:
        seen.add(current)
        spec = TYPE_RULES.get(current)
        if spec:
            for item in spec.get("core") or ():
                if item not in core:
                    core.append(item)
            for item in spec.get("recommended") or ():
                if item not in recommended and item not in core:
                    recommended.append(item)
        current = TYPE_PARENT.get(current)
    return core, recommended


def run_detection(page_url: str, jsonld_count: int, micro_count: int, rdfa_count: int, page_type: ContentPageType) -> list[CheckResult]:
    why = "Structured data can provide machine-readable information about page entities. This is not a ranking claim."
    checks = []
    if jsonld_count:
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-001", name="JSON-LD detected", group="detection", status="pass", severity="low", message="JSON-LD structured data was detected.", detected=f"{jsonld_count} block(s)", source="json-ld", why=why, selector='script[type="application/ld+json"]'))
    else:
        status = "info"
        message = "No Schema.org JSON-LD structured data detected."
        if page_type.type in PAGE_TYPE_HINTS:
            message = "No Schema.org JSON-LD structured data detected. This is not an automatic failure."
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-001", name="JSON-LD detected", group="detection", status=status, severity="info", message=message, source="json-ld", why=why))
    if micro_count:
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-002", name="Microdata detected", group="detection", status="pass", severity="info", message="Microdata itemscope markup was detected.", detected=str(micro_count), source="microdata"))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-002", name="Microdata detected", group="detection", status="info", severity="info", message="No Microdata itemscope markup was detected.", source="microdata"))
    if rdfa_count:
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-003", name="RDFa detected", group="detection", status="pass", severity="info", message="RDFa typeof markup was detected.", detected=str(rdfa_count), source="rdfa"))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-DETECT-003", name="RDFa detected", group="detection", status="info", severity="info", message="No RDFa typeof markup was detected.", source="rdfa"))
    return checks


def run_syntax(page_url: str, blocks: list[JsonLdBlock]) -> list[CheckResult]:
    if not blocks:
        return [schema_check(page_url, check_id="SCHEMA-SYNTAX-001", name="JSON-LD syntax", group="syntax", status="not_applicable", severity="low", message="JSON-LD syntax was not evaluated because no JSON-LD scripts were found.")]
    invalid = [block for block in blocks if not block.valid]
    if invalid and len(invalid) == len(blocks):
        return [schema_check(page_url, check_id="SCHEMA-SYNTAX-001", name="JSON-LD syntax", group="syntax", status="fail", severity="high", message="JSON-LD script tags were found, but none could be parsed as JSON.", detected=f"{len(invalid)} invalid block(s)", source="json-ld", selector='script[type="application/ld+json"]')]
    if invalid:
        return [schema_check(page_url, check_id="SCHEMA-SYNTAX-001", name="JSON-LD syntax", group="syntax", status="fail", severity="medium", message=f"{len(invalid)} of {len(blocks)} JSON-LD blocks could not be parsed. Valid blocks were still analyzed.", detected=f"invalid indexes: {', '.join(str(block.index) for block in invalid)}", source="json-ld")]
    return [schema_check(page_url, check_id="SCHEMA-SYNTAX-001", name="JSON-LD syntax", group="syntax", status="pass", severity="low", message="JSON-LD blocks parsed as JSON.", detected=f"{len(blocks)} valid block(s)", source="json-ld")]


def run_context(page_url: str, blocks: list[JsonLdBlock]) -> list[CheckResult]:
    valid = [block for block in blocks if block.valid]
    if not valid:
        return [schema_check(page_url, check_id="SCHEMA-CONTEXT-001", name="Schema.org context", group="syntax", status="not_applicable", severity="low", message="@context was not evaluated because no valid JSON-LD block was parsed.")]
    kinds = [context_kind(block) for block in valid]
    if all(kind == "missing" for kind in kinds):
        return [schema_check(page_url, check_id="SCHEMA-CONTEXT-001", name="Schema.org context", group="syntax", status="warning", severity="medium", message="JSON-LD @context was not detected.", recommendation="Declare @context as https://schema.org when using Schema.org types.", source="json-ld")]
    if any(kind == "other" for kind in kinds) and not any(kind in {"schema", "http"} for kind in kinds):
        return [schema_check(page_url, check_id="SCHEMA-CONTEXT-001", name="Schema.org context", group="syntax", status="warning", severity="low", message="JSON-LD uses a context other than schema.org. The block was still analyzed.", detected=valid[0].context, source="json-ld")]
    if any(kind == "http" for kind in kinds):
        return [schema_check(page_url, check_id="SCHEMA-CONTEXT-001", name="Schema.org context", group="syntax", status="info", severity="info", message="JSON-LD uses http://schema.org. This is accepted; https://schema.org is the usual form.", detected=next(block.context for block in valid if context_kind(block) == "http"), source="json-ld")]
    return [schema_check(page_url, check_id="SCHEMA-CONTEXT-001", name="Schema.org context", group="syntax", status="pass", severity="low", message="Schema.org @context was detected.", detected=next((block.context for block in valid if block.context), None), source="json-ld")]


def run_types(page_url: str, entities: list[SchemaEntity], page_type: ContentPageType) -> list[CheckResult]:
    types = []
    seen: set[str] = set()
    for entity in entities:
        for name in entity.types:
            if name not in seen:
                seen.add(name)
                types.append(name)
    if not types:
        return [
            schema_check(page_url, check_id="SCHEMA-TYPE-001", name="Schema types", group="schema_types", status="not_applicable", severity="low", message="No schema types were present to evaluate."),
            schema_check(page_url, check_id="SCHEMA-TYPE-002", name="Relevant schema opportunity", group="schema_types", status="info" if page_type.type in PAGE_TYPE_HINTS else "not_applicable", severity="info", message="Potential structured-data opportunity." if page_type.type in PAGE_TYPE_HINTS else "Page type did not suggest a required schema type.", detected=f"page type {page_type.type}"),
        ]
    unknown = [name for name in types if name not in KNOWN_TYPES]
    if unknown:
        type_check = schema_check(page_url, check_id="SCHEMA-TYPE-001", name="Schema types", group="schema_types", status="info", severity="info", message="Unknown/unrecognized schema type detected. The type was preserved, not discarded.", detected=", ".join(unknown[:8]), schema_type=unknown[0])
    else:
        type_check = schema_check(page_url, check_id="SCHEMA-TYPE-001", name="Schema types", group="schema_types", status="pass", severity="low", message="Detected schema types were recognized.", detected=", ".join(types[:12]))
    expected = PAGE_TYPE_HINTS.get(page_type.type, ())
    if expected and not any(name in seen for name in expected):
        opportunity = schema_check(page_url, check_id="SCHEMA-TYPE-002", name="Relevant schema opportunity", group="schema_types", status="info", severity="info", message="Potential structured-data opportunity.", detected=f"{page_type.type} pages often include {', '.join(expected)}", recommendation="This is an observation, not a requirement and not a search-eligibility claim.")
    else:
        opportunity = schema_check(page_url, check_id="SCHEMA-TYPE-002", name="Relevant schema opportunity", group="schema_types", status="pass" if expected else "not_applicable", severity="low", message="Observed schema types include types commonly associated with this page type." if expected else "No additional type was required for this page.")
    return [type_check, opportunity]


def run_identity(page_url: str, entities: list[SchemaEntity], base_url: str) -> list[CheckResult]:
    if not entities:
        return [
            schema_check(page_url, check_id="SCHEMA-ID-001", name="Duplicate entity ID", group="identity", status="not_applicable", severity="low", message="No entities were present."),
            schema_check(page_url, check_id="SCHEMA-ID-002", name="Conflicting entity values", group="consistency", status="not_applicable", severity="low", message="No entities were present."),
            schema_check(page_url, check_id="SCHEMA-ID-003", name="Entity @id", group="identity", status="not_applicable", severity="info", message="Missing @id was not evaluated."),
        ]
    checks: list[CheckResult] = []
    groups = duplicate_groups(entities, base_url)
    id_dupes = [group for group in groups if len({entity.id for entity in group if entity.id}) == 1 and any(entity.id for entity in group)]
    if id_dupes:
        sample = id_dupes[0][0]
        checks.append(schema_check(page_url, check_id="SCHEMA-ID-001", name="Duplicate entity ID", group="identity", status="warning", severity="medium", message="Duplicate entity ID detected.", detected=sample.id, affected_entity=sample.id, source=sample.source))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-ID-001", name="Duplicate entity ID", group="identity", status="pass", severity="low", message="No duplicate @id values were detected among structured entities."))

    conflicts: list[tuple[str, str, str]] = []
    for key, bucket in index_ids(entities, base_url).items():
        if len(bucket) < 2:
            continue
        for field, shown, _ids in conflicting_values(bucket):
            conflicts.append((key, field, shown))
    if conflicts:
        key, field, shown = conflicts[0]
        checks.append(schema_check(page_url, check_id="SCHEMA-ID-002", name="Conflicting entity values", group="consistency", status="warning", severity="high", message="Conflicting values detected for the same structured-data entity.", detected=f"{field}: {shown}", affected_entity=key, recommendation="SiteLens does not determine which value is correct."))
    else:
        name_groups = [group for group in groups if not all(entity.id for entity in group)]
        if name_groups:
            checks.append(schema_check(page_url, check_id="SCHEMA-ID-002", name="Conflicting entity values", group="consistency", status="info", severity="info", message="Multiple Organization entities may represent the same organization.", detected=name_groups[0][0].name, recommendation="Multiple entities can be legitimate."))
        else:
            checks.append(schema_check(page_url, check_id="SCHEMA-ID-002", name="Conflicting entity values", group="consistency", status="pass", severity="low", message="No conflicting values were detected for shared entity IDs."))

    missing_id = [entity for entity in entities if entity.source == "json-ld" and not entity.id and entity.types]
    if missing_id:
        checks.append(schema_check(page_url, check_id="SCHEMA-ID-003", name="Entity @id", group="identity", status="info", severity="info", message="One or more JSON-LD entities have no @id. A simple schema block can still be valid without @id.", detected=str(len(missing_id)), schema_type=missing_id[0].types[0] if missing_id[0].types else None))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-ID-003", name="Entity @id", group="identity", status="pass", severity="info", message="JSON-LD entities include @id where present, or no typed JSON-LD entities were missing one."))
    return checks


def run_properties(page_url: str, entities: list[SchemaEntity]) -> list[CheckResult]:
    typed = [entity for entity in entities if entity.types]
    if not typed:
        return [
            schema_check(page_url, check_id="SCHEMA-CORE-001", name="Core properties", group="properties", status="not_applicable", severity="low", message="Core properties were not evaluated because no typed entities were found."),
            schema_check(page_url, check_id="SCHEMA-REC-001", name="Recommended properties", group="properties", status="not_applicable", severity="low", message="Recommended properties were not evaluated."),
            schema_check(page_url, check_id="SCHEMA-ORG-001", name="Organization name", group="properties", status="not_applicable", severity="low", message="Organization schema was not detected."),
            schema_check(page_url, check_id="SCHEMA-ARTICLE-001", name="Article author", group="properties", status="not_applicable", severity="low", message="Article schema was not detected."),
            schema_check(page_url, check_id="SCHEMA-PRODUCT-001", name="Product name", group="properties", status="not_applicable", severity="low", message="Product schema was not detected."),
            schema_check(page_url, check_id="SCHEMA-OFFER-001", name="Offer price", group="properties", status="not_applicable", severity="low", message="Offer schema was not detected."),
        ]
    checks: list[CheckResult] = []
    missing_core: list[str] = []
    missing_rec: list[str] = []
    for entity in typed:
        for type_name in entity.types:
            core, recommended = _rules(type_name)
            for field in core:
                if not _prop(entity, field):
                    missing_core.append(f"{type_name}.{field}")
            for field in recommended:
                if not _prop(entity, field):
                    missing_rec.append(f"{type_name}.{field}")

    def _by_type(prefix: str) -> list[SchemaEntity]:
        return [entity for entity in typed if prefix in entity.types]

    orgs = _by_type("Organization") + _by_type("Corporation")
    if orgs:
        if any(_prop(entity, "name") for entity in orgs):
            sample = next(entity for entity in orgs if _prop(entity, "name"))
            checks.append(schema_check(page_url, check_id="SCHEMA-ORG-001", name="Organization name", group="properties", status="pass", severity="low", message="Organization structured data was detected and contains a name.", detected=_prop(sample, "name"), schema_type="Organization", property="name", source=sample.source, affected_entity=sample.id or sample.internal_id))
        else:
            checks.append(schema_check(page_url, check_id="SCHEMA-ORG-001", name="Organization name", group="properties", status="warning", severity="high", message="Organization schema missing name.", schema_type="Organization", property="name", recommendation="This is a SiteLens core-property check, not a claim that the markup is invalid Schema.org."))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-ORG-001", name="Organization name", group="properties", status="not_applicable", severity="low", message="Organization schema was not detected."))

    articles = [entity for entity in typed if set(entity.types) & {"Article", "BlogPosting", "NewsArticle"}]
    if articles:
        if any(_prop(entity, "author") for entity in articles):
            checks.append(schema_check(page_url, check_id="SCHEMA-ARTICLE-001", name="Article author", group="properties", status="pass", severity="low", message="Article structured data includes an author.", schema_type=articles[0].types[0], property="author"))
        else:
            checks.append(schema_check(page_url, check_id="SCHEMA-ARTICLE-001", name="Article author", group="properties", status="warning", severity="medium", message="Article schema missing author.", schema_type=articles[0].types[0], property="author", recommendation="Recommended property not detected."))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-ARTICLE-001", name="Article author", group="properties", status="not_applicable", severity="low", message="Article schema was not detected."))

    products = _by_type("Product")
    if products:
        if any(_prop(entity, "name") for entity in products):
            checks.append(schema_check(page_url, check_id="SCHEMA-PRODUCT-001", name="Product name", group="properties", status="pass", severity="low", message="Product structured data was detected and contains name.", detected=_prop(products[0], "name"), schema_type="Product", property="name"))
        else:
            checks.append(schema_check(page_url, check_id="SCHEMA-PRODUCT-001", name="Product name", group="properties", status="warning", severity="high", message="Product schema missing name.", schema_type="Product", property="name"))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-PRODUCT-001", name="Product name", group="properties", status="not_applicable", severity="low", message="Product schema was not detected."))

    offers = _by_type("Offer")
    if offers:
        if any(_prop(entity, "price") for entity in offers):
            sample = next(entity for entity in offers if _prop(entity, "price"))
            extra = " and offers." if products else "."
            checks.append(schema_check(page_url, check_id="SCHEMA-OFFER-001", name="Offer price", group="properties", status="pass", severity="low", message="Offer structured data contains a price" + (" and is linked from a Product" if products else "") + ".", detected=_prop(sample, "price"), schema_type="Offer", property="price"))
        else:
            checks.append(schema_check(page_url, check_id="SCHEMA-OFFER-001", name="Offer price", group="properties", status="warning", severity="medium", message="Offer schema missing price.", schema_type="Offer", property="price", recommendation="Recommended/core offer property not detected. This is not a Google-requirement claim."))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-OFFER-001", name="Offer price", group="properties", status="not_applicable", severity="low", message="Offer schema was not detected."))

    if missing_core:
        checks.append(schema_check(page_url, check_id="SCHEMA-CORE-001", name="Core properties", group="properties", status="warning", severity="medium", message="A commonly expected core property was not detected on one or more entities.", detected="; ".join(missing_core[:8]), recommendation="These are SiteLens analysis rules, not a full Schema.org validity failure."))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-CORE-001", name="Core properties", group="properties", status="pass", severity="low", message="Detected entities include SiteLens core properties for their types."))

    if missing_rec:
        checks.append(schema_check(page_url, check_id="SCHEMA-REC-001", name="Recommended properties", group="properties", status="warning", severity="low", message="Recommended property not detected.", detected="; ".join(missing_rec[:8]), recommendation="Missing recommended properties are not reported as invalid schema."))
    else:
        checks.append(schema_check(page_url, check_id="SCHEMA-REC-001", name="Recommended properties", group="properties", status="pass", severity="info", message="No missing recommended properties were flagged for detected types."))
    return checks


def run_relationships(page_url: str, relationships: list[SchemaRelationship], entities: list[SchemaEntity]) -> list[CheckResult]:
    if not entities:
        return [schema_check(page_url, check_id="SCHEMA-REL-001", name="Entity references", group="relationships", status="not_applicable", severity="low", message="Relationships were not evaluated because no entities were found.")]
    broken = [rel for rel in relationships if rel.broken]
    if broken:
        sample = broken[0]
        return [schema_check(page_url, check_id="SCHEMA-REL-001", name="Entity references", group="relationships", status="warning", severity="medium", message="Broken entity reference.", detected=f"{sample.predicate} → {sample.target_value}", source="json-ld")]
    if relationships:
        return [schema_check(page_url, check_id="SCHEMA-REL-001", name="Entity references", group="relationships", status="pass", severity="low", message="Referenced entities are inline objects, @id values, or literals present in the graph.", detected=f"{len(relationships)} relationship(s)")]
    return [schema_check(page_url, check_id="SCHEMA-REL-001", name="Entity references", group="relationships", status="info", severity="info", message="No publisher/author/offers-style relationships were present on detected entities.")]


def run_urls(page_url: str, entities: list[SchemaEntity], base_url: str) -> list[CheckResult]:
    if not entities:
        return [
            schema_check(page_url, check_id="SCHEMA-URL-001", name="URL and ID format", group="urls", status="not_applicable", severity="low", message="URL format was not evaluated."),
            schema_check(page_url, check_id="SCHEMA-SAMEAS-001", name="sameAs values", group="urls", status="not_applicable", severity="low", message="sameAs was not present."),
            schema_check(page_url, check_id="SCHEMA-ID-004", name="Invalid @id format", group="urls", status="not_applicable", severity="low", message="@id format was not evaluated."),
        ]
    bad = []
    same_issues = []
    bad_ids = []
    for entity in entities:
        for field, value in invalid_urls(entity, base_url):
            bad.append(f"{field}={sanitize_text(value, 80)}")
            if field == "@id":
                bad_ids.append(value)
        same_issues.extend(same_as_issues(entity))
    if bad_ids:
        id_check = schema_check(page_url, check_id="SCHEMA-ID-004", name="Invalid @id format", group="urls", status="warning", severity="low", message="An @id value does not look like a URL, fragment, or blank node.", detected=sanitize_text(bad_ids[0], 80))
    else:
        id_check = schema_check(page_url, check_id="SCHEMA-ID-004", name="Invalid @id format", group="urls", status="pass", severity="info", message="@id values are fragments, relative references, or absolute URLs where present.")
    url_check = schema_check(
        page_url,
        check_id="SCHEMA-URL-001",
        name="URL and ID format",
        group="urls",
        status="warning" if bad else "pass",
        severity="low",
        message="One or more url/image/logo/@id values do not look like URLs." if bad else "URL-like properties use acceptable URL or fragment forms. Values were not fetched.",
        detected="; ".join(bad[:6]) if bad else None,
        recommendation="SiteLens does not request these URLs.",
    )
    if any(entity.properties.get("sameAs") for entity in entities):
        same_check = schema_check(page_url, check_id="SCHEMA-SAMEAS-001", name="sameAs values", group="urls", status="warning" if same_issues else "pass", severity="low", message="sameAs contains duplicate or non-URL values." if same_issues else "sameAs values look like URLs. Profiles were not verified.", detected="; ".join(same_issues[:4]) if same_issues else None)
    else:
        same_check = schema_check(page_url, check_id="SCHEMA-SAMEAS-001", name="sameAs values", group="urls", status="not_applicable", severity="info", message="No sameAs values were present.")
    return [url_check, same_check, id_check]


def run_alignment(page_url: str, entities: list[SchemaEntity], html: dict) -> list[CheckResult]:
    if not entities:
        return [
            schema_check(page_url, check_id="SCHEMA-CONSIST-001", name="Name alignment", group="alignment", status="not_applicable", severity="low", message="Visible-content alignment was not evaluated because no entities were found."),
            schema_check(page_url, check_id="SCHEMA-CONSIST-002", name="Author alignment", group="alignment", status="not_applicable", severity="low", message="Author alignment was not evaluated."),
            schema_check(page_url, check_id="SCHEMA-CONSIST-003", name="Date alignment", group="alignment", status="not_applicable", severity="low", message="Date alignment was not evaluated."),
            schema_check(page_url, check_id="SCHEMA-CONSIST-004", name="Price alignment", group="alignment", status="not_applicable", severity="low", message="Price alignment was not evaluated."),
        ]
    named = [entity for entity in entities if entity.name or entity.properties.get("headline")]
    mismatch = [entity for entity in named if name_mismatch(entity, html) is False]
    if mismatch:
        name_check = schema_check(page_url, check_id="SCHEMA-CONSIST-001", name="Name alignment", group="alignment", status="warning", severity="medium", message="Structured data does not match visible page information.", detected=f"schema {mismatch[0].name!s} vs visible {html.get('title') or first_h1(html)}", schema_type=mismatch[0].types[0] if mismatch[0].types else None, recommendation="Names are compared with normalized text, not editorial judgment.")
    elif named:
        name_check = schema_check(page_url, check_id="SCHEMA-CONSIST-001", name="Name alignment", group="alignment", status="pass", severity="low", message="Schema name/headline is consistent with visible title or heading where compared.")
    else:
        name_check = schema_check(page_url, check_id="SCHEMA-CONSIST-001", name="Name alignment", group="alignment", status="not_applicable", severity="low", message="No schema name was available to compare.")

    articles = [entity for entity in entities if set(entity.types) & {"Article", "BlogPosting", "NewsArticle"}]
    author_flags = [entity for entity in articles if author_mismatch(entity, html) is False]
    if not articles:
        author_check = schema_check(page_url, check_id="SCHEMA-CONSIST-002", name="Author alignment", group="alignment", status="not_applicable", severity="low", message="Author alignment applies to Article-like schema.")
    elif not html.get("byline") and not html.get("author_rel"):
        author_check = schema_check(page_url, check_id="SCHEMA-CONSIST-002", name="Author alignment", group="alignment", status="not_applicable", severity="low", message="No visible byline was available to compare.")
    elif author_flags:
        author_check = schema_check(page_url, check_id="SCHEMA-CONSIST-002", name="Author alignment", group="alignment", status="warning", severity="medium", message="Article schema author does not match the visible byline.", recommendation="This is not a claim of false authorship.")
    else:
        author_check = schema_check(page_url, check_id="SCHEMA-CONSIST-002", name="Author alignment", group="alignment", status="pass", severity="low", message="Article schema author is consistent with the visible byline where compared.")

    dated = [entity for entity in entities if entity.properties.get("datePublished") or entity.properties.get("dateModified")]
    date_flags = [entity for entity in dated if date_mismatch(entity, html) is False]
    if not dated or not (html.get("time_values") or []):
        date_check = schema_check(page_url, check_id="SCHEMA-CONSIST-003", name="Date alignment", group="alignment", status="not_applicable", severity="low", message="Publication dates were not compared because schema or visible dates were missing.")
    elif date_flags:
        date_check = schema_check(page_url, check_id="SCHEMA-CONSIST-003", name="Date alignment", group="alignment", status="warning", severity="low", message="Structured data dates differ from visible page dates.", recommendation="SiteLens does not infer the correct date.")
    else:
        date_check = schema_check(page_url, check_id="SCHEMA-CONSIST-003", name="Date alignment", group="alignment", status="pass", severity="low", message="Schema dates are consistent with visible dates where both were present.")

    priced = [entity for entity in entities if entity.properties.get("price")]
    price_flags = [entity for entity in priced if price_mismatch(entity, html) is False]
    if not priced:
        price_check = schema_check(page_url, check_id="SCHEMA-CONSIST-004", name="Price alignment", group="alignment", status="not_applicable", severity="low", message="No schema price was present to compare.")
    elif price_flags:
        price_check = schema_check(page_url, check_id="SCHEMA-CONSIST-004", name="Price alignment", group="alignment", status="warning", severity="medium", message="Offer price in structured data differs from visible price text.", recommendation="No currency conversion was attempted. This is not a claim of price manipulation.")
    else:
        price_check = schema_check(page_url, check_id="SCHEMA-CONSIST-004", name="Price alignment", group="alignment", status="pass", severity="low", message="Schema price matches a visible price string, or no conflicting visible price was found.")
    return [name_check, author_check, date_check, price_check]


def run_social(page_url: str, og: SocialMeta, twitter: SocialMeta) -> list[CheckResult]:
    og_core = ("og:title", "og:description", "og:image", "og:url", "og:type")
    missing_og = [key for key in og_core if key not in og.properties]
    if og.properties:
        if missing_og and "og:title" not in og.properties:
            og_check = schema_check(page_url, check_id="SCHEMA-OG-001", name="Open Graph title", group="social", status="warning", severity="low", message="Open Graph title missing.", detected=", ".join(missing_og), source="open-graph", property="og:title")
        elif og.empty or og.duplicates:
            og_check = schema_check(page_url, check_id="SCHEMA-OG-001", name="Open Graph metadata", group="social", status="warning", severity="low", message="Open Graph metadata detected with empty or duplicate properties.", detected=f"empty={','.join(og.empty) or 'none'}; duplicates={','.join(og.duplicates) or 'none'}", source="open-graph")
        else:
            og_check = schema_check(page_url, check_id="SCHEMA-OG-001", name="Open Graph metadata", group="social", status="pass", severity="low", message="Open Graph metadata detected.", detected=f"{len(og.properties)} properties", source="open-graph")
    else:
        og_check = schema_check(page_url, check_id="SCHEMA-OG-001", name="Open Graph metadata", group="social", status="info", severity="info", message="No Open Graph metadata was detected. Open Graph is social/share metadata, not Schema.org.", source="open-graph")

    if twitter.properties:
        if "twitter:card" not in twitter.properties:
            tw_check = schema_check(page_url, check_id="SCHEMA-TW-001", name="Twitter/X card", group="social", status="warning", severity="low", message="Twitter/X card metadata missing.", source="twitter", property="twitter:card")
        else:
            tw_check = schema_check(page_url, check_id="SCHEMA-TW-001", name="Twitter/X metadata", group="social", status="pass", severity="info", message="Twitter/X metadata detected.", detected=f"{len(twitter.properties)} properties", source="twitter")
    else:
        tw_check = schema_check(page_url, check_id="SCHEMA-TW-001", name="Twitter/X metadata", group="social", status="not_applicable", severity="info", message="Twitter/X metadata is not required for every site.")
    return [og_check, tw_check]
