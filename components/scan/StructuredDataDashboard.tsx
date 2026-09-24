"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getStructuredData,
  ScanApiError,
  type SchemaCheck,
  type SchemaCheckStatus,
  type SchemaEntity,
  type SchemaResultResponse,
  type SeoSeverity,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["detection", "Detection"],
  ["syntax", "Syntax"],
  ["schema_types", "Schema types"],
  ["identity", "Identity"],
  ["properties", "Properties"],
  ["relationships", "Relationships"],
  ["consistency", "Consistency"],
  ["alignment", "Alignment"],
  ["social", "Social metadata"],
] as const;

const STATUS_FILTERS: Array<{ id: "all" | "fail" | "warning" | "pass" | "info"; label: string }> = [
  { id: "all", label: "All" },
  { id: "fail", label: "Failed" },
  { id: "warning", label: "Warnings" },
  { id: "pass", label: "Passed" },
  { id: "info", label: "Info" },
];

const SEVERITY_FILTERS: Array<{ id: "all" | SeoSeverity; label: string }> = [
  { id: "all", label: "All severity" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
];

export function StructuredDataDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [schema, setSchema] = useState<SchemaResultResponse | null>(null);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [openBlocks, setOpenBlocks] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getStructuredData(scanId)
      .then((result) => {
        if (!cancelled) {
          setSchema(result);
          setSchemaError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setSchemaError(caught instanceof ScanApiError ? caught.message : "Structured data analysis not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = schema?.findings?.length ? schema.findings : schema?.checks || [];
  const selected = findings.find((check) => check.check_id === selectedId) ?? null;
  const selectedEntity = (schema?.entities || []).find((entity) => (entity.id || entity.internal_id) === selectedEntityId) ?? null;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((check) => {
      if (statusFilter !== "all" && check.status !== statusFilter) return false;
      if (severityFilter !== "all" && check.severity !== severityFilter) return false;
      if (!needle) return true;
      const hay = `${check.name} ${check.group} ${check.message} ${check.detected || ""} ${check.schema_type || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [findings, statusFilter, severityFilter, query]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const og = schema?.open_graph?.properties || {};
  const twitter = schema?.twitter?.properties || {};

  return (
    <ScanShell scanId={scanId} current="structured-data">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Structured data analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running structured data analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : schemaError ? (
          <StateCard title="Structured data analysis not available." body={schemaError} />
        ) : !schema ? (
          <StateCard title="Loading structured data results" body="Fetching JSON-LD, Microdata, RDFa, and social metadata measurements." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Structured Data</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Schema.org & metadata analysis</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Automated analysis of structured data and machine-readable page metadata.
              </p>
              <p className="mt-4 text-5xl font-semibold tracking-tight text-foreground">
                {schema.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Detection summary</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                <MiniStat label="JSON-LD" value={`${schema.summary.jsonld_blocks ?? schema.json_ld?.length ?? 0} blocks`} />
                <MiniStat label="Schema entities" value={String(schema.summary.entities ?? schema.entities?.length ?? 0)} />
                <MiniStat label="Schema types" value={String((schema.summary.schema_types || []).length)} />
                <MiniStat label="Microdata" value={String(schema.summary.microdata_items ?? 0)} />
                <MiniStat label="RDFa" value={String(schema.summary.rdfa_items ?? 0)} />
              </dl>
              <p className="mt-4 text-xs text-muted-foreground">JSON-LD, Microdata, and RDFa are reported separately from Open Graph and Twitter/X metadata.</p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Schema types</h2>
              {(schema.summary.schema_types || []).length ? (
                <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                  {(schema.summary.schema_types || []).map((typeName) => {
                    const count = (schema.entities || []).filter((entity) => entity.types.includes(typeName)).length;
                    const related = findings.filter((check) => check.schema_type === typeName && check.status !== "pass");
                    return (
                      <li key={typeName} className="rounded-xl border border-border bg-muted/40 px-4 py-3">
                        <p className="font-medium text-foreground">{typeName}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {count} entit{count === 1 ? "y" : "ies"}
                          {related.length ? ` · ${related.length} finding(s)` : " · no issues"}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No Schema.org types were detected.</p>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Entity explorer</h2>
              {(schema.entities || []).length ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[40rem] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                        <th className="py-2 pr-3 font-medium">Type</th>
                        <th className="py-2 pr-3 font-medium">Name</th>
                        <th className="py-2 pr-3 font-medium">ID</th>
                        <th className="py-2 font-medium">Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(schema.entities || []).map((entity) => {
                        const key = entity.id || entity.internal_id;
                        return (
                          <tr
                            key={entity.internal_id}
                            className={cn("cursor-pointer border-b border-border/80 last:border-0 hover:bg-muted/40", selectedEntityId === key && "bg-muted/60")}
                            onClick={() => setSelectedEntityId(key)}
                          >
                            <td className="py-3 pr-3">{entity.types.join(", ") || "—"}</td>
                            <td className="py-3 pr-3">{entity.name || "—"}</td>
                            <td className="py-3 pr-3 font-mono text-xs break-all">{entity.id || "—"}</td>
                            <td className="py-3 capitalize">{entity.source}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No structured entities were extracted.</p>
              )}
              {selectedEntity ? <EntityDetail entity={selectedEntity} relationships={schema.relationships || []} /> : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Schema graph</h2>
              {(schema.relationships || []).length ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {(schema.relationships || []).slice(0, 40).map((rel, index) => (
                    <li key={`${rel.source_id}-${rel.predicate}-${index}`} className="rounded-xl border border-border bg-muted/40 px-4 py-3">
                      <span className="font-mono text-xs">{rel.source_id}</span>
                      <span className="mx-2 text-muted-foreground">→ {rel.predicate} →</span>
                      <span className="font-mono text-xs">{rel.target_id || rel.target_value || "—"}</span>
                      {rel.broken ? <span className="ml-2 text-warn">broken</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No entity relationships were present in the markup.</p>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">JSON-LD blocks</h2>
              {(schema.json_ld || []).length ? (
                <ul className="mt-4 space-y-2">
                  {(schema.json_ld || []).map((block) => (
                    <li key={block.index} className="rounded-xl border border-border bg-muted/40">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm"
                        onClick={() => setOpenBlocks((current) => ({ ...current, [block.index]: !current[block.index] }))}
                      >
                        <span>Block {block.index + 1}</span>
                        <span className={block.valid ? "text-pass" : "text-critical"}>{block.valid ? "Valid" : "Invalid"}</span>
                      </button>
                      {openBlocks[block.index] ? (
                        <pre className="max-h-64 overflow-auto border-t border-border px-4 py-3 font-mono text-xs whitespace-pre-wrap">
                          {block.valid ? JSON.stringify(block.preview, null, 2) : block.error || "Malformed JSON-LD."}
                        </pre>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No JSON-LD scripts were found.</p>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <MiniStat key={key} label={label} value={schema.categories?.[key] == null ? "—" : String(schema.categories[key])} />
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Schema findings</h2>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name, type, evidence, message"
                  className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm lg:max-w-sm"
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {STATUS_FILTERS.map((item) => (
                  <FilterChip key={item.id} active={statusFilter === item.id} onClick={() => setStatusFilter(item.id)} label={item.label} />
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {SEVERITY_FILTERS.map((item) => (
                  <FilterChip key={item.id} active={severityFilter === item.id} onClick={() => setSeverityFilter(item.id)} label={item.label} />
                ))}
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[48rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Check</th>
                      <th className="py-2 pr-3 font-medium">Category</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 pr-3 font-medium">Severity</th>
                      <th className="py-2 font-medium">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((check) => (
                      <tr
                        key={check.check_id}
                        className={cn("cursor-pointer border-b border-border/80 last:border-0 hover:bg-muted/40", selectedId === check.check_id && "bg-muted/60")}
                        onClick={() => setSelectedId(check.check_id)}
                      >
                        <td className="py-3 pr-3 text-foreground">{check.name}</td>
                        <td className="py-3 pr-3 capitalize text-muted-foreground">{check.group.replace("_", " ")}</td>
                        <td className="py-3 pr-3">
                          <StatusMark status={check.status} />
                        </td>
                        <td className="py-3 pr-3 text-muted-foreground">{check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)}</td>
                        <td className="py-3 text-muted-foreground">{check.detected || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">No findings match these filters.</p> : null}
              </div>
            </section>

            {selected ? <CheckDetail check={selected} /> : null}

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Open Graph</h2>
              <p className="mt-1 text-xs text-muted-foreground">Social/share metadata. This is not Schema.org structured data.</p>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <MiniStat label="Title" value={og["og:title"] || "—"} />
                <MiniStat label="Description" value={og["og:description"] || "—"} />
                <MiniStat label="Image" value={og["og:image"] || "—"} />
                <MiniStat label="URL" value={og["og:url"] || "—"} />
                <MiniStat label="Type" value={og["og:type"] || "—"} />
                <MiniStat label="Site name" value={og["og:site_name"] || "—"} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Twitter/X metadata</h2>
              <p className="mt-1 text-xs text-muted-foreground">Social/share metadata. This is not Schema.org structured data.</p>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <MiniStat label="Card" value={twitter["twitter:card"] || "—"} />
                <MiniStat label="Title" value={twitter["twitter:title"] || "—"} />
                <MiniStat label="Description" value={twitter["twitter:description"] || "—"} />
                <MiniStat label="Image" value={twitter["twitter:image"] || "—"} />
                <MiniStat label="Site" value={twitter["twitter:site"] || "—"} />
              </dl>
            </section>

            {schema.limitations?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
                  {schema.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </>
        )}
      </div>
    </ScanShell>
  );
}

function EntityDetail({
  entity,
  relationships,
}: {
  entity: SchemaEntity;
  relationships: NonNullable<SchemaResultResponse["relationships"]>;
}) {
  const related = relationships.filter((rel) => rel.source_id === entity.internal_id || rel.target_id === entity.internal_id);
  return (
    <div className="mt-4 rounded-xl border border-border bg-background px-4 py-4 text-sm">
      <h3 className="text-base font-semibold text-foreground">{entity.types.join(", ") || "Entity"}</h3>
      <dl className="mt-3 space-y-2">
        <Detail label="ID" value={entity.id || "—"} />
        <Detail label="Name" value={entity.name || "—"} />
        <Detail label="Source" value={entity.source} />
      </dl>
      <h4 className="mt-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Properties</h4>
      <ul className="mt-2 space-y-1">
        {Object.entries(entity.properties || {}).map(([key, value]) => (
          <li key={key}>
            <span className="text-muted-foreground">{key}:</span> {value}
          </li>
        ))}
        {!Object.keys(entity.properties || {}).length ? <li className="text-muted-foreground">No properties extracted.</li> : null}
      </ul>
      <h4 className="mt-4 text-xs font-medium tracking-wide text-muted-foreground uppercase">Relationships</h4>
      <ul className="mt-2 space-y-1">
        {related.map((rel, index) => (
          <li key={`${rel.predicate}-${index}`}>
            {rel.predicate} → {rel.target_id || rel.target_value || "—"}
          </li>
        ))}
        {!related.length ? <li className="text-muted-foreground">No relationships for this entity.</li> : null}
      </ul>
    </div>
  );
}

function CheckDetail({ check }: { check: SchemaCheck }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail label="Category" value={capitalize(check.group.replace("_", " "))} />
        <Detail label="Severity" value={check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)} />
        <Detail label="Source" value={check.source || "—"} />
        <Detail label="Schema type" value={check.schema_type || "—"} />
        <Detail label="Evidence" value={check.detected || "—"} />
        <Detail label="Why it matters" value={check.why || check.message} />
        {check.recommendation ? <Detail label="Recommendation" value={check.recommendation} /> : null}
      </dl>
    </section>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium",
        active ? "border-foreground/15 bg-foreground text-background" : "border-border bg-background text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

function StatusMark({ status }: { status: SchemaCheckStatus }) {
  if (status === "pass") return <span className="font-medium text-pass">✓ Pass</span>;
  if (status === "warning") return <span className="font-medium text-warn">⚠ Warning</span>;
  if (status === "fail") return <span className="font-medium text-critical">✕ Fail</span>;
  if (status === "info") return <span className="font-medium text-muted-foreground">ℹ Info</span>;
  return <span className="font-medium text-muted-foreground">— N/A</span>;
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/50 px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold break-all text-foreground">{value}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-foreground">{value}</dd>
    </div>
  );
}

function statusLabel(status: SchemaCheckStatus) {
  if (status === "pass") return "Passed";
  if (status === "warning") return "Warning";
  if (status === "fail") return "Failed";
  if (status === "info") return "Info";
  return "Not applicable";
}

function capitalize(value: string) {
  return value.slice(0, 1).toUpperCase() + value.slice(1);
}
