"""Basic RDFa detection and property extraction. Not a full RDF reasoner."""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.analyzers.structured_data.config import DEFAULT_SCORING, SchemaScoringConfig
from backend.analyzers.structured_data.models import RdfaItem, SchemaEntity, SchemaRelationship


def _type_name(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text or None


def parse_rdfa(
    html_source: str,
    *,
    config: SchemaScoringConfig = DEFAULT_SCORING,
) -> tuple[list[RdfaItem], list[SchemaEntity], list[SchemaRelationship], bool]:
    soup = BeautifulSoup(html_source or "", "html.parser")
    items: list[RdfaItem] = []
    entities: list[SchemaEntity] = []
    relationships: list[SchemaRelationship] = []
    truncated = False
    seq = 0
    for tag in soup.find_all(attrs={"typeof": True}):
        if not isinstance(tag, Tag):
            continue
        if tag.find_parent(attrs={"typeof": True}):
            continue
        if len(entities) >= config.max_entities:
            truncated = True
            break
        seq += 1
        raw_type = tag.get("typeof")
        if isinstance(raw_type, list):
            raw_type = " ".join(str(part) for part in raw_type)
        types = []
        for part in str(raw_type or "").split():
            name = _type_name(part)
            if name:
                types.append(name)
        resource = tag.get("resource") or tag.get("about")
        if isinstance(resource, list):
            resource = resource[0] if resource else None
        resource = str(resource).strip() if isinstance(resource, str) and resource.strip() else None
        props: dict[str, str] = {}
        for child in tag.find_all(attrs={"property": True}):
            if not isinstance(child, Tag):
                continue
            prop = child.get("property")
            if isinstance(prop, list):
                prop = prop[0] if prop else None
            if not isinstance(prop, str):
                continue
            value = child.get("content") or child.get("href") or child.get("src") or child.get_text(" ", strip=True)
            if isinstance(value, str) and value.strip() and len(props) < config.max_properties:
                key = prop.strip().rsplit(":", 1)[-1][:40]
                props[key] = value.strip()[:120]
        name = props.get("name") or props.get("headline")
        items.append(RdfaItem(types=types, resource=resource, properties=props))
        entities.append(
            SchemaEntity(internal_id=f"rdfa:{seq}", id=resource, types=types, name=name, source="rdfa", properties=props)
        )
    return items, entities, relationships, truncated
