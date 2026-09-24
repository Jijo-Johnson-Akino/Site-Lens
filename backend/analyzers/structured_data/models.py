from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable", "info"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "detection",
    "syntax",
    "schema_types",
    "identity",
    "properties",
    "relationships",
    "urls",
    "consistency",
    "alignment",
    "social",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Structured Data"
    group: CheckGroup
    name: str
    status: CheckStatus
    severity: Severity
    score: float | None
    weight: int = 0
    message: str
    recommendation: str | None = None
    why: str | None = None
    detected: str | None = None
    page_url: str
    selector: str | None = None
    source: str | None = None
    schema_type: str | None = None
    property: str | None = None
    affected_entity: str | None = None
    affected_element: str | None = None
    affected_element_count: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class SchemaSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int
    info: int = 0
    jsonld_blocks: int = 0
    microdata_items: int = 0
    rdfa_items: int = 0
    entities: int = 0
    schema_types: list[str] = Field(default_factory=list)


class SchemaIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    page_url: str
    detected: str | None = None
    source: str | None = None
    schema_type: str | None = None
    affected_entity: str | None = None


class SchemaPageInfo(BaseModel):
    analyzed_url: str
    final_url: str
    title: str | None = None


class SchemaEntity(BaseModel):
    internal_id: str
    id: str | None = None
    types: list[str] = Field(default_factory=list)
    name: str | None = None
    source: str
    block_index: int | None = None
    properties: dict[str, str] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)


class SchemaRelationship(BaseModel):
    source_id: str
    predicate: str
    target_id: str | None = None
    target_value: str | None = None
    inline: bool = False
    broken: bool = False


class JsonLdBlock(BaseModel):
    index: int
    valid: bool
    error: str | None = None
    truncated: bool = False
    context: str | None = None
    types: list[str] = Field(default_factory=list)
    entity_count: int = 0
    preview: Any = None


class MicrodataItem(BaseModel):
    types: list[str] = Field(default_factory=list)
    id: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)


class RdfaItem(BaseModel):
    types: list[str] = Field(default_factory=list)
    resource: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)


class SocialMeta(BaseModel):
    properties: dict[str, str] = Field(default_factory=dict)
    duplicates: list[str] = Field(default_factory=list)
    empty: list[str] = Field(default_factory=list)


class SchemaCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0


class SchemaResult(BaseModel):
    score: int
    summary: SchemaSummary
    narrative: str
    categories: dict[str, int | None]
    category_cards: list[SchemaCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult]
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[SchemaIssue]
    page: SchemaPageInfo
    json_ld: list[JsonLdBlock] = Field(default_factory=list)
    microdata: list[MicrodataItem] = Field(default_factory=list)
    rdfa: list[RdfaItem] = Field(default_factory=list)
    entities: list[SchemaEntity] = Field(default_factory=list)
    relationships: list[SchemaRelationship] = Field(default_factory=list)
    open_graph: SocialMeta = Field(default_factory=SocialMeta)
    twitter: SocialMeta = Field(default_factory=SocialMeta)
    consistency: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    truncated: bool = False
    page_type: dict[str, Any] | None = None


def make_check(
    *,
    check_id: str,
    name: str,
    group: CheckGroup,
    status: CheckStatus,
    severity: Severity,
    message: str,
    page_url: str,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    selector: str | None = None,
    source: str | None = None,
    schema_type: str | None = None,
    property: str | None = None,
    affected_entity: str | None = None,
    affected_element_count: int = 0,
    details: dict[str, Any] | None = None,
) -> CheckResult:
    if status == "pass":
        earned: float | None = 1.0
    elif status == "info":
        earned = 0.85
    elif status == "warning":
        earned = 0.5
    elif status == "fail":
        earned = 0.0
    else:
        earned = None
    return CheckResult(
        check_id=check_id,
        group=group,
        name=name,
        status=status,
        severity=severity,
        score=earned,
        message=message,
        recommendation=recommendation,
        why=why,
        detected=detected,
        page_url=page_url,
        selector=selector,
        source=source,
        schema_type=schema_type,
        property=property,
        affected_entity=affected_entity,
        affected_element=selector,
        affected_element_count=affected_element_count,
        details=details or {},
    )
