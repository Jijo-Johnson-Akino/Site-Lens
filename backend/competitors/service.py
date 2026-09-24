"""Create, list, remove, and rescan competitor benchmarks using the existing scan engine."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.competitors.config import MAX_COMPETITORS, MAX_NAME_LENGTH, MAX_URL_LENGTH
from backend.competitors.models import CompetitorBenchmark, CompetitorListPayload
from backend.competitors.store import load_payload, merge_into_result
from backend.errors import ScanError
from backend.schemas.scan import ScanRecord
from backend.services.url_identity import hostname_of, normalize_page_url


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"comp_{uuid4().hex[:16]}"


def _scan_status(record: ScanRecord | None) -> str:
    if record is None:
        return "failed"
    if record.status == "running":
        return "scanning"
    if record.status in {"queued", "completed", "failed", "cancelled"}:
        return record.status
    return "queued"


def _identity(url: str) -> str:
    host = hostname_of(url)
    normalized = normalize_page_url(url)
    return host or normalized


class CompetitorService:
    def __init__(self, scans) -> None:
        self._scans = scans

    def _record(self, scan_id: str) -> ScanRecord:
        record = self._scans.get(scan_id)
        if record is None:
            raise ScanError("SCAN_NOT_FOUND", "Scan not found.")
        return record

    def _payload(self, record: ScanRecord) -> CompetitorListPayload:
        return load_payload(record.result)

    def _save(self, record: ScanRecord, payload: CompetitorListPayload) -> ScanRecord:
        result = merge_into_result(record.result, payload)
        return self._scans._update(record, result=result)

    def hydrate(self, item: CompetitorBenchmark) -> CompetitorBenchmark:
        scan = self._scans.get(item.competitor_scan_id)
        status = _scan_status(scan)
        if scan is None:
            return item.model_copy(update={"status": "failed", "updated_at": item.updated_at or item.created_at})
        return item.model_copy(update={"status": status, "updated_at": _now() if status != item.status else item.updated_at})

    def list(self, scan_id: str) -> tuple[ScanRecord, list[CompetitorBenchmark]]:
        record = self._record(scan_id)
        items = [self.hydrate(item) for item in self._payload(record).items if item.scan_id == scan_id]
        return record, items

    def get(self, scan_id: str, competitor_id: str) -> tuple[ScanRecord, CompetitorBenchmark, ScanRecord | None]:
        record, items = self.list(scan_id)
        item = next((row for row in items if row.id == competitor_id and row.scan_id == scan_id), None)
        if item is None:
            raise ScanError("COMPETITOR_NOT_FOUND", "Competitor not found.")
        return record, item, self._scans.get(item.competitor_scan_id)

    def add(self, scan_id: str, name: str, url: str) -> tuple[CompetitorBenchmark, ScanRecord]:
        record = self._record(scan_id)
        if record.status != "completed":
            raise ScanError("SCAN_NOT_READY", "Competitors can be added after the primary scan completes.")
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ScanError("INVALID_NAME", "Enter a competitor name.")
        if len(cleaned_name) > MAX_NAME_LENGTH:
            raise ScanError("INVALID_NAME", "Competitor name is too long.")
        cleaned_url = (url or "").strip()
        if not cleaned_url:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        if len(cleaned_url) > MAX_URL_LENGTH:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        payload = self._payload(record)
        if len(payload.items) >= MAX_COMPETITORS:
            raise ScanError("COMPETITOR_LIMIT", f"Up to {MAX_COMPETITORS} competitors can be benchmarked per scan.")
        normalized = self._scans._validator.validate(cleaned_url)
        primary_hosts = {_identity(record.normalized_url), _identity(record.url)}
        final_url = ((record.result or {}).get("website") or {}).get("final_url") if record.result else None
        if final_url:
            primary_hosts.add(_identity(final_url))
        if _identity(normalized) in {host for host in primary_hosts if host}:
            raise ScanError("DUPLICATE_PRIMARY", "The competitor URL cannot be the same as the primary website.")
        existing = {_identity(item.normalized_url) for item in payload.items}
        if _identity(normalized) in existing:
            raise ScanError("DUPLICATE_COMPETITOR", "This website is already added as a competitor.")
        created = self._scans.create(cleaned_url)
        now = _now()
        item = CompetitorBenchmark(
            id=_new_id(),
            scan_id=record.id,
            name=cleaned_name,
            url=cleaned_url,
            normalized_url=created.normalized_url,
            competitor_scan_id=created.id,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        payload.items.append(item)
        self._save(record, payload)
        return item, created

    def remove(self, scan_id: str, competitor_id: str) -> CompetitorBenchmark:
        record = self._record(scan_id)
        payload = self._payload(record)
        item = next((row for row in payload.items if row.id == competitor_id and row.scan_id == scan_id), None)
        if item is None:
            raise ScanError("COMPETITOR_NOT_FOUND", "Competitor not found.")
        payload.items = [row for row in payload.items if row.id != competitor_id]
        self._save(record, payload)
        return item

    def rescan(self, scan_id: str, competitor_id: str) -> tuple[CompetitorBenchmark, ScanRecord]:
        record = self._record(scan_id)
        payload = self._payload(record)
        item = next((row for row in payload.items if row.id == competitor_id and row.scan_id == scan_id), None)
        if item is None:
            raise ScanError("COMPETITOR_NOT_FOUND", "Competitor not found.")
        created = self._scans.create(item.url)
        now = _now()
        updated = item.model_copy(
            update={
                "competitor_scan_id": created.id,
                "normalized_url": created.normalized_url,
                "status": "queued",
                "updated_at": now,
            }
        )
        payload.items = [updated if row.id == item.id else row for row in payload.items]
        self._save(record, payload)
        return updated, created
