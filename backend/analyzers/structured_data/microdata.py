"""Microdata extraction. No extra HTTP."""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.analyzers.structured_data.config import DEFAULT_SCORING, SchemaScoringConfig
from backend.analyzers.structured_data.jsonld import serialize_prop
from backend.analyzers.structured_data.models import MicrodataItem, SchemaEntity, SchemaRelationship
from backend.parser.structured_data import node_text


def _type_name(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text or None


def parse_microdata(
    html_source: str,
    *,
    config: SchemaScoringConfig = DEFAULT_SCORING,
) -> tuple[list[MicrodataItem], list[SchemaEntity], list[SchemaRelationship], bool]:
    soup = BeautifulSoup(html_source or "", "html.parser")
    items: list[MicrodataItem] = []
    entities: list[SchemaEntity] = []
    relationships: list[SchemaRelationship] = []
    truncated = False
    seq = 0

    roots = [tag for tag in soup.find_all(attrs={"itemscope": True}) if isinstance(tag, Tag) and not tag.find_parent(attrs={"itemscope": True})]
    for tag in roots:
        if len(entities) >= config.max_entities:
            truncated = True
            break
        seq += 1
        entity, item = _read_item(tag, f"microdata:{seq}", config)
        items.append(item)
        entities.append(entity)
    return items, entities, relationships, truncated


def _read_item(tag: Tag, internal_id: str, config: SchemaScoringConfig) -> tuple[SchemaEntity, MicrodataItem]:
    raw_type = tag.get("itemtype")
    if isinstance(raw_type, list):
        raw_type = " ".join(str(part) for part in raw_type)
    types = []
    for part in str(raw_type or "").split():
        name = _type_name(part)
        if name:
            types.append(name)
    item_id = tag.get("itemid")
    if isinstance(item_id, list):
        item_id = item_id[0] if item_id else None
    item_id = str(item_id).strip() if isinstance(item_id, str) and item_id.strip() else None
    props: dict[str, str] = {}
    for child in tag.find_all(attrs={"itemprop": True}):
        if not isinstance(child, Tag):
            continue
        if child is not tag and child.find_parent(attrs={"itemscope": True}) not in {tag, None} and child.find_parent(attrs={"itemscope": True}) is not tag:
            continue
        name = child.get("itemprop")
        if isinstance(name, list):
            name = name[0] if name else None
        if not isinstance(name, str) or not name.strip():
            continue
        if child.get("itemscope") is not None and child is not tag:
            nested_type = _type_name(str(child.get("itemtype") or ""))
            value = nested_type or node_text(child.get("itemid")) or child.get_text(" ", strip=True)
        else:
            value = child.get("content") or child.get("href") or child.get("src") or child.get("datetime") or child.get_text(" ", strip=True)
        serialized = serialize_prop(value) if not isinstance(value, str) else value.strip()[:120]
        if serialized and len(props) < config.max_properties:
            props[name.strip()[:40]] = serialized
    name = props.get("name") or props.get("headline")
    entity = SchemaEntity(internal_id=internal_id, id=item_id, types=types, name=name, source="microdata", properties=props)
    item = MicrodataItem(types=types, id=item_id, properties=props)
    return entity, item
