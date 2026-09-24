"""Normalize entities, resolve @id references, and detect duplicates/conflicts."""

from __future__ import annotations

from collections import defaultdict
from urllib.parse import urljoin, urlsplit

from backend.analyzers.aeo.checks._util import normalize_name
from backend.analyzers.structured_data.models import SchemaEntity, SchemaRelationship


def normalize_id(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith("#"):
        parsed = urlsplit(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{text}"
    return urljoin(base_url, text)


def index_ids(entities: list[SchemaEntity], base_url: str) -> dict[str, list[SchemaEntity]]:
    grouped: dict[str, list[SchemaEntity]] = defaultdict(list)
    for entity in entities:
        key = normalize_id(entity.id, base_url)
        if key:
            grouped[key].append(entity)
    return grouped


def mark_broken_relationships(entities: list[SchemaEntity], relationships: list[SchemaRelationship], base_url: str) -> list[SchemaRelationship]:
    known = set()
    for entity in entities:
        if entity.id:
            known.add(entity.id.strip())
            norm = normalize_id(entity.id, base_url)
            if norm:
                known.add(norm)
        known.add(entity.internal_id)
    updated: list[SchemaRelationship] = []
    for rel in relationships:
        if rel.inline or rel.target_id:
            updated.append(rel)
            continue
        target = (rel.target_value or "").strip()
        if not target:
            updated.append(rel)
            continue
        looks_like_ref = target.startswith("#") or target.startswith("http://") or target.startswith("https://")
        if not looks_like_ref:
            updated.append(rel)
            continue
        resolved = normalize_id(target, base_url) or target
        if target in known or resolved in known:
            updated.append(rel.model_copy(update={"target_id": resolved, "broken": False}))
        else:
            updated.append(rel.model_copy(update={"broken": True}))
    return updated


def duplicate_groups(entities: list[SchemaEntity], base_url: str) -> list[list[SchemaEntity]]:
    groups = []
    for bucket in index_ids(entities, base_url).values():
        if len(bucket) >= 2:
            groups.append(bucket)
    by_name: dict[tuple[str, str], list[SchemaEntity]] = defaultdict(list)
    for entity in entities:
        type_name = (entity.types[0] if entity.types else "").lower()
        name = normalize_name(entity.name)
        url = (entity.properties.get("url") or "").strip().lower()
        if type_name in {"organization", "corporation", "localbusiness"} and name:
            by_name[(type_name, name + "|" + url)].append(entity)
    for bucket in by_name.values():
        if len(bucket) >= 2 and bucket not in groups:
            groups.append(bucket)
    return groups


def conflicting_values(entities: list[SchemaEntity]) -> list[tuple[str, str, list[str]]]:
    conflicts = []
    names = {entity.name.strip() for entity in entities if entity.name and entity.name.strip()}
    urls = {entity.properties.get("url", "").strip() for entity in entities if entity.properties.get("url")}
    if len(names) > 1:
        conflicts.append(("name", ", ".join(sorted(names)[:4]), [entity.internal_id for entity in entities]))
    if len(urls) > 1:
        conflicts.append(("url", ", ".join(sorted(urls)[:4]), [entity.internal_id for entity in entities]))
    return conflicts
