export type ScanStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ScanStepStatus = "pending" | "active" | "completed" | "failed";

export type ScanErrorPayload = {
  code: string;
  message: string;
};

export type ScanCreateResponse = {
  scan_id: string;
  status: ScanStatus;
};

export type SeoCheckStatus = "pass" | "warning" | "fail" | "not_applicable";
export type SeoSeverity = "critical" | "high" | "medium" | "low" | "info";

export type SeoCheck = {
  check_id: string;
  category: string;
  group: string;
  name: string;
  status: SeoCheckStatus;
  severity: SeoSeverity;
  score: number | null;
  message: string;
  recommendation: string | null;
  why: string | null;
  detected: string | null;
  page_url: string;
};

export type SeoIssue = {
  check_id: string;
  name: string;
  status: SeoCheckStatus;
  severity: SeoSeverity;
  message: string;
  recommendation: string | null;
};

export type SeoResultResponse = {
  scan_id: string;
  score: number;
  summary: {
    passed: number;
    warnings: number;
    failed: number;
    not_applicable: number;
  };
  narrative: string;
  categories: Record<string, number | null>;
  checks: SeoCheck[];
  issues: SeoIssue[];
  page: {
    analyzed_url: string;
    final_url: string;
    status_code: number | null;
    title: string | null;
    h1: string | null;
    language?: string | null;
  } | null;
  indexable?: {
    indexable: boolean;
    reason: string | null;
  } | null;
  insight?: string;
};

export type AeoResultResponse = SeoResultResponse;

export type UiuxCheck = SeoCheck & {
  viewport: string;
  affected_element?: string | null;
};

export type UiuxScreenshot = {
  viewport: string;
  width: number;
  height: number;
  url: string;
  created_at: string;
};

export type UiuxViewportResult = {
  score: number;
  width: number;
  height: number;
  summary: SeoResultResponse["summary"];
  layout?: {
    scroll_width?: number;
    viewport_width?: number;
    horizontal_overflow?: boolean;
    overflow_px?: number;
  };
  navigation?: {
    exists?: boolean;
    visible?: boolean;
    links?: number;
  };
  content?: {
    h1?: number;
    h1_visible?: boolean;
    paragraphs?: number;
  };
  interactive?: {
    buttons?: number;
    links?: number;
    forms?: number;
  };
};

export type UiuxResultResponse = {
  scan_id: string;
  score: number;
  summary: SeoResultResponse["summary"];
  narrative?: string;
  categories: Record<string, number | null>;
  viewports: Record<string, UiuxViewportResult>;
  screenshots: UiuxScreenshot[];
  checks: UiuxCheck[];
  issues: Array<
    SeoIssue & {
      viewport: string;
      page_url?: string;
      affected_element?: string | null;
      detected?: string | null;
    }
  >;
  page: {
    analyzed_url: string;
    final_url: string;
  } | null;
};

export type A11yCheck = SeoCheck & {
  selector?: string | null;
  affected_element?: string | null;
  affected_element_count?: number;
  wcag_reference?: string | null;
  source?: "axe" | "sitebench" | "manual-review";
  help_url?: string | null;
  axe_rule_id?: string | null;
  manual_review?: boolean;
  details?: Record<string, unknown>;
};

export type A11yResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number;
  summary: SeoResultResponse["summary"] & { manual_review?: number };
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: Array<{ id: string; name: string; score: number | null; finding_count: number }>;
  checks: A11yCheck[];
  findings?: A11yCheck[];
  issues: Array<
    SeoIssue & {
      selector?: string | null;
      affected_element_count?: number;
      wcag_reference?: string | null;
      source?: string;
      manual_review?: boolean;
    }
  >;
  page: { analyzed_url: string; final_url: string } | null;
  tool?: {
    name: string;
    version?: string | null;
    automated?: boolean;
    tags?: string[];
    standard?: string;
    automated_only?: boolean;
    axe_violations?: number;
    axe_incomplete?: number;
    axe_passes?: number;
    axe_inapplicable?: number;
  };
  standard?: { name: string; version?: string; automated_only?: boolean };
  limitations?: string[];
  severity_counts?: Record<string, number>;
  screenshots?: UiuxScreenshot[];
};

export type PerfVital = {
  value: number | null;
  status: "good" | "needs_improvement" | "poor" | "unavailable";
  unit?: string | null;
  reason?: string | null;
};

export type PerfCheck = SeoCheck & {
  resource_url?: string | null;
  affected_element_count?: number;
  details?: Record<string, unknown>;
};

export type PerfResourceRow = {
  url: string;
  domain?: string | null;
  type: string;
  initiator?: string | null;
  transfer_bytes?: number | null;
  encoded_bytes?: number | null;
  decoded_bytes?: number | null;
  duration_ms?: number | null;
  status?: number | null;
  content_type?: string | null;
  first_party: boolean;
  cache_control?: string | null;
  content_encoding?: string | null;
  etag?: boolean;
  last_modified?: boolean;
  expires?: string | null;
};

export type PerfResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number;
  summary: SeoResultResponse["summary"];
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: Array<{ id: string; name: string; score: number | null; finding_count: number }>;
  checks: PerfCheck[];
  findings?: PerfCheck[];
  issues: Array<SeoIssue & { resource_url?: string | null; detected?: string | null; affected_element_count?: number }>;
  page: { analyzed_url: string; final_url: string } | null;
  environment?: {
    browser: string;
    browser_version?: string | null;
    viewport?: { width?: number; height?: number };
    viewport_name?: string;
    network_profile?: string;
    cpu_throttling?: boolean;
    cache_enabled?: boolean;
    cache_mode?: string;
  };
  timing?: {
    ttfb_ms?: number | null;
    dns_ms?: number | null;
    connection_ms?: number | null;
    tls_ms?: number | null;
    dom_content_loaded_ms?: number | null;
    load_event_ms?: number | null;
    redirect_ms?: number | null;
    redirect_count?: number | null;
  };
  vitals?: {
    lcp: PerfVital;
    cls: PerfVital;
    inp: PerfVital;
  };
  resources?: {
    total_requests: number;
    transfer_bytes: number;
    html_bytes: number;
    css_bytes: number;
    js_bytes: number;
    image_bytes: number;
    font_bytes: number;
    third_party_bytes: number;
    percentages?: Record<string, number>;
  };
  resource_table?: PerfResourceRow[];
  limitations?: string[];
  severity_counts?: Record<string, number>;
};

export type ContentCheck = SeoCheck & {
  selector?: string | null;
  affected_element_count?: number;
  details?: Record<string, unknown>;
};

export type ContentResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number;
  summary: SeoResultResponse["summary"];
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: Array<{ id: string; name: string; score: number | null; finding_count: number }>;
  checks: ContentCheck[];
  findings?: ContentCheck[];
  issues: SeoIssue[];
  page: { analyzed_url: string; final_url: string; title?: string | null; language?: string | null } | null;
  page_type?: { type: string; confidence: number; reasons?: string[] };
  metrics?: {
    word_count: number;
    main_word_count?: number;
    character_count?: number;
    paragraph_count: number;
    heading_count: number;
    section_count: number;
    list_count: number;
    table_count: number;
    h1_count?: number;
    h2_count?: number;
    h3_count?: number;
    internal_content_links?: number;
  };
  readability?: {
    language?: string | null;
    supported?: boolean;
    flesch_reading_ease?: number | null;
    flesch_kincaid_grade?: number | null;
    label?: string | null;
    reason?: string | null;
  };
  signals?: {
    main_content_detected?: boolean;
    thin_content?: boolean;
    repeated_content?: boolean;
    duplicate_content?: boolean;
    author_detected?: boolean;
    publication_date_detected?: boolean;
    cta_detected?: boolean;
    boilerplate_ratio?: number;
    repeated_content_ratio?: number;
  };
  structure?: Record<string, number | boolean | null>;
  duplicates?: Array<{ url: string; similarity: number; kind: "exact" | "near" }>;
  limitations?: string[];
  severity_counts?: Record<string, number>;
  truncated?: boolean;
};

export type SchemaCheckStatus = SeoCheckStatus | "info";

export type SchemaCheck = Omit<SeoCheck, "status"> & {
  status: SchemaCheckStatus;
  selector?: string | null;
  source?: string | null;
  schema_type?: string | null;
  property?: string | null;
  affected_entity?: string | null;
  affected_element_count?: number;
  details?: Record<string, unknown>;
};

export type SchemaEntity = {
  internal_id: string;
  id?: string | null;
  types: string[];
  name?: string | null;
  source: string;
  block_index?: number | null;
  properties?: Record<string, string>;
  findings?: string[];
};

export type SchemaResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number;
  summary: SeoResultResponse["summary"] & {
    info?: number;
    jsonld_blocks?: number;
    microdata_items?: number;
    rdfa_items?: number;
    entities?: number;
    schema_types?: string[];
  };
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: Array<{ id: string; name: string; score: number | null; finding_count: number }>;
  checks: SchemaCheck[];
  findings?: SchemaCheck[];
  issues: SeoIssue[];
  page: { analyzed_url: string; final_url: string; title?: string | null } | null;
  json_ld?: Array<{
    index: number;
    valid: boolean;
    error?: string | null;
    truncated?: boolean;
    context?: string | null;
    types?: string[];
    entity_count?: number;
    preview?: unknown;
  }>;
  microdata?: Array<{ types: string[]; id?: string | null; properties?: Record<string, string> }>;
  rdfa?: Array<{ types: string[]; resource?: string | null; properties?: Record<string, string> }>;
  entities?: SchemaEntity[];
  relationships?: Array<{
    source_id: string;
    predicate: string;
    target_id?: string | null;
    target_value?: string | null;
    inline?: boolean;
    broken?: boolean;
  }>;
  open_graph?: { properties?: Record<string, string>; duplicates?: string[]; empty?: string[] };
  twitter?: { properties?: Record<string, string>; duplicates?: string[]; empty?: string[] };
  consistency?: Record<string, number>;
  limitations?: string[];
  severity_counts?: Record<string, number>;
  truncated?: boolean;
  page_type?: { type: string; confidence: number };
};

export type MobileCheck = SeoCheck & {
  selector?: string | null;
  affected_element?: string | null;
  affected_element_count?: number;
  viewport?: string;
  measured_value?: string | number | null;
  expected_value?: string | number | null;
  details?: Record<string, unknown>;
};

export type MobileScreenshot = UiuxScreenshot & {
  kind?: string;
};

export type MobileResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number;
  summary: SeoResultResponse["summary"];
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: Array<{ id: string; name: string; score: number | null; finding_count: number; status?: string | null }>;
  checks: MobileCheck[];
  findings?: MobileCheck[];
  issues: Array<SeoIssue & { selector?: string | null; viewport?: string; measured_value?: string | number | null; expected_value?: string | number | null }>;
  page: { analyzed_url: string; final_url: string } | null;
  environment?: {
    browser: string;
    browser_version?: string | null;
    device_profile?: string;
    viewport?: { width?: number; height?: number };
    touch_enabled?: boolean | null;
    device_scale_factor?: number | null;
    user_agent_category?: string;
    is_mobile_emulation?: boolean;
  };
  viewport?: {
    width?: number;
    height?: number;
    document_width?: number | null;
    horizontal_overflow?: boolean;
    overflow_px?: number | null;
    meta?: Record<string, unknown>;
  };
  navigation?: {
    mobile_navigation_detected?: boolean;
    mobile_menu_detected?: boolean;
    menu_button_detected?: boolean;
    mobile_menu_opened?: boolean;
    menu_tested?: boolean;
    visible?: boolean;
    overflow?: boolean;
  };
  layout?: Record<string, unknown>;
  typography?: { small_text_elements?: number; clipped_text?: number; overflowing_headings?: number };
  touch_targets?: { interactive_elements?: number; below_baseline?: number; very_small?: number };
  forms?: { forms?: number; overflowing_forms?: number; controls_outside_viewport?: number };
  images?: { images?: number; overflowing?: number; oversized?: number };
  tables?: { tables?: number; overflowing?: number; responsive?: number };
  media?: { items?: number; overflowing?: number };
  overlays?: { count?: number; max_coverage?: number };
  sticky_elements?: { count?: number; max_coverage?: number };
  screenshots?: MobileScreenshot[];
  limitations?: string[];
  severity_counts?: Record<string, number>;
  comparison?: Record<string, unknown> | null;
  overview?: Record<string, { status?: string; warnings?: number; failed?: number; passed?: number }>;
};

export type IssuePriority = "critical" | "high" | "medium" | "low";
export type IssueLifecycle = "open" | "resolved" | "ignored";
export type AnalyzerRunStatus = "completed" | "failed" | "missing";

export type ScreenshotCaptureStatus = "pending" | "running" | "completed" | "skipped";

export type ScreenshotCaptureSummary = {
  status: ScreenshotCaptureStatus;
  captured: number;
  visual: number;
  note?: string | null;
};

export type IssueMediaFields = {
  screenshot_url?: string | null;
  screenshot_caption?: string | null;
  highlighted_selector?: string | null;
  viewport_type?: "desktop" | "mobile" | null;
  snippet?: string | null;
  snippet_language?: string | null;
  snippet_highlight_line?: number | null;
  screenshot_unavailable?: boolean;
  screenshot_unavailable_reason?: string | null;
  visual_kind?: "screenshot" | "snippet" | "none" | null;
  whats_wrong?: string | null;
  why_it_matters?: string | null;
  how_to_fix?: string | null;
};

export type IssueListItem = {
  issue_id: string;
  issue_key: string;
  title: string;
  description: string;
  source: string;
  analyzer: string;
  category: string;
  subcategory?: string | null;
  check_id: string;
  status: IssueLifecycle;
  check_status: SeoCheckStatus | "info";
  severity: SeoSeverity;
  priority: IssuePriority;
  priority_score: number;
  page_url?: string | null;
  affected_page_count: number;
  affected_element_count: number;
  occurrence_count: number;
  recommendation?: string | null;
  source_href?: string | null;
  related_issue_ids: string[];
} & IssueMediaFields;

export type IssueSummary = {
  total: number;
  occurrences: number;
  issue_types: number;
  failures: number;
  warnings: number;
  info: number;
  passed?: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  by_severity: Record<string, number>;
  by_source: Record<string, number>;
  by_page: Record<string, number>;
};

export type IssuesListResponse = {
  scan_id: string;
  items: IssueListItem[];
  pagination: { page: number; page_size: number; total: number; pages: number };
  summary: IssueSummary;
  analyzer_status: Record<string, AnalyzerRunStatus>;
  truncated?: boolean;
  screenshot_capture?: ScreenshotCaptureSummary;
};

export type IssuesSummaryResponse = {
  scan_id: string;
  truncated?: boolean;
  analyzer_status: Record<string, AnalyzerRunStatus>;
  summary: IssueSummary;
  groups?: Record<string, Record<string, number>>;
  screenshot_capture?: ScreenshotCaptureSummary;
};

export type IssueOccurrence = {
  occurrence_id: string;
  finding_ids: string[];
  page_url: string;
  selector?: string | null;
  resource_url?: string | null;
  schema_entity_id?: string | null;
  viewport?: string | null;
  affected_element_count: number;
  evidence: Record<string, unknown>;
  check_status: SeoCheckStatus | "info";
  severity: SeoSeverity;
  message: string;
  recommendation?: string | null;
  wcag_reference?: string | null;
  affected_elements?: Array<{
    selector?: string | null;
    resource_url?: string | null;
    schema_entity_id?: string | null;
    viewport?: string | null;
    snippet?: string | null;
    width?: number | null;
  }>;
};

export type UnifiedIssueDetail = {
  issue_id: string;
  issue_key: string;
  source: string;
  analyzer: string;
  category: string;
  subcategory?: string | null;
  check_id: string;
  title: string;
  description: string;
  recommendation?: string | null;
  status: IssueLifecycle;
  check_status: SeoCheckStatus | "info";
  severity: SeoSeverity;
  source_severity?: string | null;
  priority: IssuePriority;
  priority_score: number;
  score?: number | null;
  page_url?: string | null;
  selector?: string | null;
  resource_url?: string | null;
  schema_entity_id?: string | null;
  viewport?: string | null;
  affected_page_count: number;
  affected_element_count: number;
  pages: string[];
  evidence: Record<string, unknown>;
  wcag_reference?: string | null;
  related_issue_ids: string[];
  occurrences: IssueOccurrence[];
  source_href?: string | null;
  related_issues?: Array<{
    issue_id: string;
    issue_key: string;
    title: string;
    source: string;
    category: string;
    priority: IssuePriority;
    severity: SeoSeverity;
  }>;
  original_finding?: {
    check_id: string;
    source: string;
    finding_ids: string[];
    source_severity?: string | null;
    score?: number | null;
  };
  details?: Record<string, unknown>;
} & IssueMediaFields;

export type IssueDetailResponse = {
  scan_id: string;
  issue: UnifiedIssueDetail;
  screenshot_capture?: ScreenshotCaptureSummary;
};

export type CrawlStatus = "discovered" | "queued" | "crawling" | "crawled" | "failed" | "skipped";

export type PagesSummary = {
  discovered: number;
  crawled: number;
  failed: number;
  skipped: number;
  queued?: number;
  internal_pages?: number;
  external_links_discovered?: number;
  max_depth_reached?: number;
  max_pages: number;
  max_depth: number;
  page_limit_reached?: boolean;
  depth_limit_reached?: boolean;
};

export type PageListItem = {
  id: string;
  url: string;
  normalized_url: string;
  final_url?: string | null;
  page_type?: string | null;
  page_type_label?: string | null;
  crawl_status: CrawlStatus;
  http_status?: number | null;
  title?: string | null;
  meta_description?: string | null;
  h1?: string | null;
  canonical_url?: string | null;
  indexable?: boolean | null;
  word_count?: number | null;
  depth?: number;
  response_time_ms?: number | null;
  issue_count: number;
  severity_counts?: Record<string, number>;
  available_analyzers: string[];
  seo?: number | null;
  aeo?: number | null;
  uiux?: number | null;
  accessibility?: number | null;
  performance?: number | null;
  content?: number | null;
  structured_data?: number | null;
  mobile?: number | null;
  cro?: number | null;
  trust?: number | null;
  skip_reason?: string | null;
  failure_reason?: string | null;
  is_seed?: boolean;
};

export type PageAnalyzerCard = {
  id: string;
  label: string;
  available: boolean;
  score?: number | null;
  href?: string | null;
  link_label?: string | null;
  note?: string | null;
  site_href?: string | null;
};

export type PageRelatedIssue = {
  issue_id: string;
  issue_key: string;
  title: string;
  severity: SeoSeverity;
  priority: IssuePriority;
  status: IssueLifecycle;
  source: string;
  category: string;
  check_status: SeoCheckStatus | "info";
};

export type PageDetail = PageListItem & {
  discovered_from?: string | null;
  discovery_method?: string | null;
  content_type?: string | null;
  response_size_bytes?: number | null;
  h1_count?: number | null;
  h2_count?: number | null;
  robots_directive?: string | null;
  language?: string | null;
  internal_link_count?: number | null;
  external_link_count?: number | null;
  image_count?: number | null;
  paragraph_count?: number | null;
  list_count?: number | null;
  schema_types?: string[];
  headings?: Array<{ level: number; text?: string | null }>;
  analyzers?: PageAnalyzerCard[];
  issues?: PageRelatedIssue[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type PagesListResponse = {
  scan_id: string;
  status?: string;
  in_progress?: boolean;
  items: PageListItem[];
  pagination: { page: number; page_size: number; total: number; pages: number; total_pages?: number };
  summary: PagesSummary;
  limits?: { max_pages?: number; max_depth?: number };
};

export type PagesSummaryResponse = {
  scan_id: string;
  status?: string;
  in_progress?: boolean;
  summary: PagesSummary;
  limits?: { max_pages?: number; max_depth?: number };
};

export type PageDetailResponse = {
  scan_id: string;
  status?: string;
  summary?: PagesSummary;
  limits?: { max_pages?: number; max_depth?: number };
  page: PageDetail;
};

export type PageQuery = {
  search?: string;
  page?: number;
  page_size?: number;
  page_type?: string;
  crawl_status?: string;
  http_status?: string;
  indexable?: string;
  has_issues?: string;
  sort?: string;
  order?: string;
};

export type ScanStatusResponse = {
  scan_id: string;
  url: string;
  normalized_url: string;
  status: ScanStatus;
  progress: number;
  current_step: string;
  created_at?: string | null;
  completed_at?: string | null;
  error: ScanErrorPayload | null;
  result?: {
    website?: { url: string; final_url: string };
    http?: { status_code: number };
    html?: { title: string | null; h1?: string | null };
    seo?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    aeo?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
      insight?: string;
    };
    uiux?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    accessibility?: {
      score: number;
      summary: SeoResultResponse["summary"] & { manual_review?: number };
      narrative?: string;
    };
    performance?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    content?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    structured_data?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    mobile?: {
      score: number;
      summary: SeoResultResponse["summary"];
      narrative?: string;
    };
    cro?: {
      score: number | null;
      summary?: {
        pages_analyzed?: number;
        open_findings?: number;
        cta_issues?: number;
        form_issues?: number;
        conversion_path_issues?: number;
        mobile_issues?: number;
      };
      narrative?: string;
    };
    cro_error?: { code?: string; message?: string };
    trust?: {
      score: number | null;
      summary?: {
        pages_analyzed?: number;
        identity_signals?: number;
        contact_signals?: number;
        policy_signals?: number;
        authorship_signals?: number;
        social_proof_signals?: number;
        open_findings?: number;
      };
      narrative?: string;
    };
    trust_error?: { code?: string; message?: string };
    health?: {
      overall?: {
        score: number | null;
        status?: string;
        coverage_percent?: number | null;
        coverage_status?: string;
        available_categories?: number;
        configured_categories?: number;
      };
      coverage?: { coverage_percent?: number | null; status?: string };
      score_note?: string;
    };
    health_error?: { code?: string; message?: string };
    issues?: {
      summary?: IssueSummary;
      analyzer_status?: Record<string, AnalyzerRunStatus>;
      truncated?: boolean;
    };
    recommendations?: {
      summary?: {
        total?: number;
        open?: number;
        high_priority?: number;
        in_progress?: number;
        completed?: number;
      };
      analyzer_status?: Record<string, AnalyzerRunStatus>;
      methodology?: string;
    };
    recommendations_error?: { code?: string; message?: string };
    pages?: {
      summary?: PagesSummary;
      limits?: { max_pages?: number; max_depth?: number };
      in_progress?: boolean;
    };
  } | null;
};

export class ScanApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function readError(response: Response): Promise<ScanApiError> {
  try {
    const body = (await response.json()) as { error?: ScanErrorPayload };
    if (body.error?.message) {
      return new ScanApiError(body.error.code, body.error.message);
    }
  } catch {
    /* ignore non-JSON */
  }
  if (response.status >= 500) {
    return new ScanApiError("ENGINE_UNAVAILABLE", "Unable to start the scan engine. Try again in a moment.");
  }
  return new ScanApiError("UNKNOWN", "Unable to analyze this website.");
}

export async function createScan(url: string): Promise<ScanCreateResponse> {
  let response: Response;
  try {
    response = await fetch("/api/scans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to start the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ScanCreateResponse;
}

export async function getScan(scanId: string, signal?: AbortSignal): Promise<ScanStatusResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}`, {
      cache: "no-store",
      signal,
    });
  } catch (caught) {
    if (signal?.aborted) {
      throw caught;
    }
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ScanStatusResponse;
}

export async function getSeo(scanId: string): Promise<SeoResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/seo`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as SeoResultResponse;
}

export async function getAeo(scanId: string): Promise<AeoResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/aeo`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as AeoResultResponse;
}

export async function getUiux(scanId: string): Promise<UiuxResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/uiux`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as UiuxResultResponse;
}

export async function getAccessibility(scanId: string): Promise<A11yResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/accessibility`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as A11yResultResponse;
}

export async function getPerformance(scanId: string): Promise<PerfResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/performance`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as PerfResultResponse;
}

export async function getContent(scanId: string): Promise<ContentResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/content`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ContentResultResponse;
}

export async function getStructuredData(scanId: string): Promise<SchemaResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/structured-data`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as SchemaResultResponse;
}

export async function getMobile(scanId: string): Promise<MobileResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/mobile`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as MobileResultResponse;
}

export type CroCheck = SeoCheck & {
  group?: string;
  page_id?: string | null;
  viewport?: string | null;
  selector?: string | null;
  evidence?: Record<string, unknown>;
  details?: Record<string, unknown>;
};

export type CroCategoryCard = { id: string; name: string; score: number | null; finding_count: number };

export type CroPageRow = {
  page_id?: string | null;
  url: string;
  page_type: string;
  score: number | null;
  available?: boolean;
  cta_status?: string | null;
  forms_status?: string | null;
  conversion_path_status?: string | null;
  issue_count: number;
};

export type CroCtaRow = {
  text: string;
  page_url: string;
  page_id?: string | null;
  kind: string;
  visibility: string;
  destination: string;
  status: string;
  primary?: boolean;
  selector?: string | null;
};

export type CroFormRow = {
  page_url: string;
  page_id?: string | null;
  purpose: string;
  fields: number;
  submit_text?: string | null;
  mobile_status?: string | null;
  issue_count: number;
  selector?: string | null;
};

export type CroPath = {
  nodes: Array<{ url: string; title?: string | null; page_type?: string | null }>;
  message?: string | null;
};

export type CroResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number | null;
  summary: SeoResultResponse["summary"] & {
    pages_analyzed?: number;
    cta_issues?: number;
    form_issues?: number;
    conversion_path_issues?: number;
    mobile_issues?: number;
    open_findings?: number;
  };
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: CroCategoryCard[];
  checks: CroCheck[];
  findings?: CroCheck[];
  issues: SeoIssue[];
  pages?: CroPageRow[];
  ctas?: CroCtaRow[];
  forms?: CroFormRow[];
  conversion_paths?: CroPath[];
  methodology?: string;
  limitations?: string[];
  screenshots?: UiuxScreenshot[];
  score_note?: string;
  crawl_note?: string;
  viewports?: Record<string, { width?: number; height?: number }>;
};

export type CroPageDetailResponse = {
  scan_id: string;
  page: CroPageRow;
  checks: CroCheck[];
  ctas: CroCtaRow[];
  forms: CroFormRow[];
  conversion_paths: CroPath[];
  methodology?: string;
  limitations?: string[];
};

export async function getCro(scanId: string): Promise<CroResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/cro`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as CroResultResponse;
}

export async function getCroPage(scanId: string, pageId: string): Promise<CroPageDetailResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/cro/pages/${encodeURIComponent(pageId)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as CroPageDetailResponse;
}

export type TrustCheck = SeoCheck & {
  group?: string;
  page_id?: string | null;
  selector?: string | null;
  evidence?: Record<string, unknown>;
  details?: Record<string, unknown>;
};

export type TrustCategoryCard = { id: string; name: string; score: number | null; finding_count: number; coverage_label?: string };

export type TrustPageRow = {
  page_id?: string | null;
  url: string;
  page_type: string;
  score: number | null;
  available?: boolean;
  identity_status?: string | null;
  contact_status?: string | null;
  authorship_status?: string | null;
  issue_count: number;
};

export type TrustSignalRow = {
  signal: string;
  category: string;
  page_url: string;
  page_id?: string | null;
  evidence: string;
  status: string;
};

export type TrustPolicyRow = {
  policy: string;
  detected: boolean;
  page_url?: string | null;
  note: string;
};

export type TrustAuthorRow = {
  page_url: string;
  page_id?: string | null;
  title?: string | null;
  author?: string | null;
  publication_date?: string | null;
  modified_date?: string | null;
  author_schema?: string | null;
  available?: boolean;
};

export type TrustSocialProofRow = {
  kind: string;
  page_url: string;
  evidence: string;
  detected: boolean;
  potential?: boolean;
};

export type TrustConsistencyRow = {
  field: string;
  visible?: string | null;
  schema_value?: string | null;
  footer?: string | null;
  about?: string | null;
  status: string;
};

export type TrustSecurityRow = {
  signal: string;
  detected: boolean;
  evidence: string;
};

export type TrustResultResponse = {
  scan_id: string;
  status?: string;
  url?: string;
  score: number | null;
  summary: SeoResultResponse["summary"] & {
    pages_analyzed?: number;
    identity_signals?: number;
    contact_signals?: number;
    policy_signals?: number;
    authorship_signals?: number;
    social_proof_signals?: number;
    open_findings?: number;
  };
  narrative?: string;
  categories: Record<string, number | null>;
  category_cards?: TrustCategoryCard[];
  checks: TrustCheck[];
  findings?: TrustCheck[];
  issues: SeoIssue[];
  pages?: TrustPageRow[];
  signals?: TrustSignalRow[];
  gaps?: TrustSignalRow[];
  policies?: TrustPolicyRow[];
  authors?: TrustAuthorRow[];
  social_proof?: TrustSocialProofRow[];
  consistency?: TrustConsistencyRow[];
  security?: TrustSecurityRow[];
  methodology?: string;
  limitations?: string[];
  score_note?: string;
  crawl_note?: string;
};

export type TrustPageDetailResponse = {
  scan_id: string;
  page: TrustPageRow;
  checks: TrustCheck[];
  signals: TrustSignalRow[];
  gaps: TrustSignalRow[];
  authors: TrustAuthorRow[];
  social_proof: TrustSocialProofRow[];
  consistency: TrustConsistencyRow[];
  security: TrustSecurityRow[];
  policies: TrustPolicyRow[];
  methodology?: string;
  limitations?: string[];
  score_note?: string;
  crawl_note?: string;
};

export async function getTrust(scanId: string): Promise<TrustResultResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/trust`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as TrustResultResponse;
}

export async function getTrustPage(scanId: string, pageId: string): Promise<TrustPageDetailResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/trust/pages/${encodeURIComponent(pageId)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as TrustPageDetailResponse;
}

export type HealthIssueCounts = {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
};

export type HealthCategoryScore = {
  category: string;
  name: string;
  score: number | null;
  raw_score?: number | null;
  weight: number;
  effective_weight?: number | null;
  weighted_contribution?: number | null;
  available: boolean;
  status: "available" | "partial" | "unavailable" | "failed";
  href: string;
  finding_count: number;
  issue_count: number;
  issue_summary?: HealthIssueCounts;
  page_count?: number | null;
  reason?: string | null;
};

export type HealthScoreResponse = {
  scan_id?: string;
  calculation_version: string;
  calculated_at?: string;
  overall: {
    score: number | null;
    status: string;
    band?: string | null;
    coverage_percent?: number | null;
    coverage_status: "complete" | "partial" | "limited" | "unavailable";
    available_categories: number;
    configured_categories: number;
  };
  coverage: {
    configured_weight: number;
    available_weight: number;
    coverage_percent: number | null;
    status: "complete" | "partial" | "limited" | "unavailable";
    available_categories: number;
    configured_categories: number;
    explanation: string;
  };
  categories: HealthCategoryScore[];
  architecture?: {
    name: string;
    status: string;
    included_in_score: boolean;
    href: string;
    note: string;
  };
  issue_summary: HealthIssueCounts;
  page_summary?: {
    pages_analyzed?: number | null;
    pages_with_issues?: number | null;
    pages_without_issues?: number | null;
  };
  methodology: {
    calculation_version: string;
    weights: Record<string, number>;
    formula: string;
    score_range: number[];
    unavailable_behavior: string;
    rounding: string;
    bands: Record<string, string>;
    coverage_rules: Record<string, string>;
  };
  limitations: string[];
  score_note: string;
  coverage_note: string;
  partial_notice?: string | null;
};

export type HealthMethodologyResponse = {
  scan_id?: string;
  calculation_version: string;
  weights: Record<string, number>;
  formula: string;
  score_range: number[];
  unavailable_behavior: string;
  rounding: string;
  bands: Record<string, string>;
  coverage_rules: Record<string, string>;
  limitations?: string[];
  score_note?: string | null;
};

export async function getHealthScore(scanId: string): Promise<HealthScoreResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/score`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as HealthScoreResponse;
}

export async function getHealthScoreMethodology(scanId: string): Promise<HealthMethodologyResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/score/methodology`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as HealthMethodologyResponse;
}

export type ReportStatus = "ready" | "partial" | "unavailable";

export type ReportFinding = {
  issue_id: string;
  title: string;
  description?: string;
  category: string;
  severity: string;
  priority: string;
  page_url?: string | null;
  recommendation?: string | null;
  affected_page_count?: number;
  href: string;
  screenshot_url?: string | null;
  screenshot_caption?: string | null;
  snippet?: string | null;
  snippet_language?: string | null;
  snippet_highlight_line?: number | null;
  screenshot_unavailable?: boolean;
  screenshot_unavailable_reason?: string | null;
  visual_kind?: "screenshot" | "snippet" | "none" | null;
  whats_wrong?: string | null;
  why_it_matters?: string | null;
  how_to_fix?: string | null;
};

export type ReportRecommendation = {
  id: string;
  title: string;
  summary?: string;
  action_summary?: string | null;
  category: string;
  priority: string;
  effort: string;
  impact: string;
  affected_page_count: number;
  issue_count: number;
  href: string;
};

export type ReportAnalyzerSection = {
  available: boolean;
  status: string;
  name: string;
  score: number | null;
  summary?: Record<string, unknown> | null;
  narrative?: string | null;
  categories?: Record<string, number | null>;
  issues?: Array<{
    title?: string | null;
    severity?: string | null;
    status?: string | null;
    message?: string | null;
    recommendation?: string | null;
    page_url?: string | null;
  }>;
  href: string;
  detail_label: string;
  message?: string | null;
  note?: string | null;
  limitation?: string | null;
  limitations?: string[];
  insight?: string | null;
  indexable?: { indexable?: boolean; reason?: string | null } | null;
  page?: Record<string, unknown> | null;
  viewports?: Array<{ viewport: string; score: number | null; width?: number; height?: number }>;
  screenshots?: Array<{ viewport: string; url: string; width?: number; height?: number; alt?: string }>;
  environment?: Record<string, unknown> | null;
  timing?: Record<string, number | null> | null;
  vitals?: Record<string, { value?: number | null; status?: string | null; unit?: string | null; reason?: string | null }>;
  resources?: Record<string, number | null> | null;
  long_tasks?: number | null;
  metrics?: Record<string, number | null> | null;
  readability?: Record<string, unknown> | null;
  signals?: Record<string, unknown> | null;
  page_type?: Record<string, unknown> | null;
  open_graph?: { property_count?: number; properties?: string[] } | null;
  twitter?: { property_count?: number; properties?: string[] } | null;
  schema_types?: string[];
  tool?: Record<string, unknown> | null;
  score_note?: string | null;
  crawl_note?: string | null;
  methodology?: string | null;
  cta_count?: number | null;
  form_count?: number | null;
  conversion_paths?: string[];
  policies?: Array<{ policy?: string; detected?: boolean; page_url?: string | null; note?: string | null }>;
  signal_counts?: { detected?: number | null; gaps?: number | null };
  security?: Array<{ signal?: string; detected?: boolean; evidence?: string | null }>;
  overview?: Record<string, unknown> | null;
  viewport?: Record<string, unknown> | null;
  severity_counts?: Record<string, number> | null;
};

export type ScanReportResponse = {
  report_version: string;
  report_status: ReportStatus;
  generated_at: string;
  scan: {
    scan_id: string;
    website: string;
    url: string;
    normalized_url: string;
    final_url?: string | null;
    status: string;
    created_at?: string | null;
    started_at?: string | null;
    completed_at?: string | null;
    generated_at: string;
    analyzed_at?: string | null;
    viewport?: string | null;
  };
  overview: {
    overall_score: number | null;
    score_status?: string | null;
    score_band?: string | null;
    score_coverage: number | null;
    coverage_status: string;
    categories_analyzed: number;
    categories_configured: number;
    pages_analyzed: number | null;
    pages_discovered: number | null;
    issues_detected: number | null;
    recommendations: number | null;
  };
  score: HealthScoreResponse | null;
  categories: Array<{
    category: string;
    name: string;
    score: number | null;
    weight: number;
    status: string;
    available: boolean;
    issue_count: number | null;
    href: string;
    reason?: string | null;
  }>;
  architecture_note?: {
    name: string;
    status: string;
    included_in_score: boolean;
    href: string;
    note: string;
  };
  issues: {
    total: number;
    by_severity: Record<string, number>;
    by_priority?: Record<string, number>;
    truncated?: boolean;
    empty_message?: string | null;
    href: string;
    priority_issues: ReportFinding[];
    priority_note?: string;
    key_findings: Array<{ severity: string; items: ReportFinding[] }>;
    screenshot_capture?: ScreenshotCaptureSummary | null;
  };
  priority_issues: ReportFinding[];
  key_findings: Array<{ severity: string; items: ReportFinding[] }>;
  recommendations: {
    total: number;
    by_priority: Record<string, number>;
    by_category?: Record<string, number>;
    action_plan_preview: Array<{ priority: string; count: number }>;
    items: ReportRecommendation[];
    empty_message?: string | null;
    href: string;
    action_plan_href?: string;
    preview_note?: string;
  };
  pages: {
    available: boolean;
    summary?: {
      discovered?: number;
      crawled?: number;
      failed?: number;
      skipped?: number;
      page_limit_reached?: boolean;
      depth_limit_reached?: boolean;
    } | null;
    pages_with_issues?: number;
    pages_without_issues?: number;
    distribution?: {
      healthy?: number;
      have_issues?: number;
      broken?: number;
      redirects?: number;
      blocked?: number;
    };
    indexability?: {
      pages_with_indexability: number;
      indexable: number;
      not_indexable: number;
      unknown: number;
    } | null;
    page_types?: Array<{ label: string; count: number }>;
    top_affected_pages?: Array<{
      page_id: string;
      url: string;
      path: string;
      title?: string | null;
      issue_count: number;
      page_type?: string | null;
      href: string;
    }>;
    top_affected_note?: string;
    empty_message?: string | null;
    href: string;
  };
  architecture: {
    available: boolean;
    summary?: {
      page_count?: number;
      internal_link_count?: number;
      potential_orphan_count?: number;
      dead_end_count?: number;
      terminal_page_count?: number;
      links_recorded?: boolean;
      external_links_discovered?: number;
      max_crawl_depth?: number | null;
      average_crawl_depth?: number | null;
    } | null;
    depth_distribution?: Array<{ depth: number; page_count: number }>;
    page_type_distribution?: Array<{ page_type: string; label: string; page_count: number }>;
    insights?: Array<{ id?: string; text: string }>;
    notes?: string[];
    orphan_note?: string;
    orphan_wording?: string;
    empty_message?: string | null;
    href?: string | null;
  };
  seo: ReportAnalyzerSection;
  aeo: ReportAnalyzerSection;
  uiux: ReportAnalyzerSection;
  accessibility: ReportAnalyzerSection;
  performance: ReportAnalyzerSection;
  content: ReportAnalyzerSection;
  structured_data: ReportAnalyzerSection;
  mobile: ReportAnalyzerSection;
  cro: ReportAnalyzerSection;
  trust: ReportAnalyzerSection;
  screenshots: {
    available: boolean;
    items: Array<{ viewport: string; url: string; width?: number; height?: number; alt?: string }>;
    empty_message?: string | null;
  };
  competitors: {
    included: boolean;
    competitor_count: number;
    empty_message?: string | null;
    primary?: { label?: string; url?: string; completed_at?: string | null };
    competitors?: Array<{ label?: string; url?: string; completed_at?: string | null; status?: string }>;
    columns?: Array<{ id: string; label: string; url?: string; status?: string; completed_at?: string | null }>;
    categories?: Array<{
      id: string;
      label: string;
      values: Array<{ column_id: string; available: boolean; score: number | null }>;
    }>;
    metrics?: Array<{
      id?: string;
      label: string;
      values: Array<{ column_id: string; available: boolean; display?: string | null; value?: number | null }>;
    }>;
    warnings?: string[];
    note?: string;
  };
  limitations: string[];
  methodology: {
    report_version: string;
    calculation_version?: string;
    paragraphs: string[];
    score?: HealthMethodologyResponse;
  };
};

export async function getScanReport(scanId: string): Promise<ScanReportResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/report`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ScanReportResponse;
}

export async function downloadScanReportPdf(scanId: string, filenameHint?: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/report.pdf`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  const blob = await response.blob();
  const filename = filenameFromDisposition(response.headers.get("Content-Disposition")) || filenameHint || "SiteLens-report.pdf";
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.rel = "noopener";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) {
    return null;
  }
  const utf = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(header);
  if (utf?.[1]) {
    try {
      return decodeURIComponent(utf[1].trim().replace(/^"+|"+$/g, ""));
    } catch {
      return utf[1].trim().replace(/^"+|"+$/g, "");
    }
  }
  const ascii = /filename="?([^";]+)"?/i.exec(header);
  return ascii?.[1]?.trim() ?? null;
}

export type IssueQuery = {
  status?: string;
  severity?: string;
  priority?: string;
  category?: string;
  source?: string;
  check_status?: string;
  page?: number;
  page_size?: number;
  page_url?: string;
  search?: string;
  sort?: string;
  order?: string;
  include_all?: boolean;
  issue_key?: string;
  issue_ids?: string;
};

function issuesQuery(params: IssueQuery = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "" || value === "all") {
      continue;
    }
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export async function getIssues(scanId: string, params: IssueQuery = {}): Promise<IssuesListResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/issues${issuesQuery(params)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as IssuesListResponse;
}

export async function getIssuesSummary(scanId: string): Promise<IssuesSummaryResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/issues/summary`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as IssuesSummaryResponse;
}

export async function getIssue(scanId: string, issueId: string): Promise<IssueDetailResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/issues/${encodeURIComponent(issueId)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as IssueDetailResponse;
}

export type RecommendationPriority = "critical" | "high" | "medium" | "low" | "info";
export type RecommendationImpact = "high" | "medium" | "low";
export type RecommendationEffort = "small" | "medium" | "large";
export type RecommendationStatus = "open" | "in_progress" | "completed" | "dismissed";

export type RecommendationListItem = {
  id: string;
  recommendation_key: string;
  title: string;
  summary: string;
  category: string;
  priority: RecommendationPriority;
  impact: RecommendationImpact;
  effort: RecommendationEffort;
  status: RecommendationStatus;
  affected_page_count: number;
  affected_element_count: number;
  issue_count: number;
  issue_keys: string[];
  issue_ids?: string[];
  page_ids?: string[];
  action_steps?: string[];
  source_kind: string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type RecommendationSummary = {
  total: number;
  open: number;
  in_progress: number;
  completed: number;
  dismissed: number;
  high_priority: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  high_priority_by_category: Record<string, number>;
};

export type RecommendationAffectedPage = {
  page_id: string | null;
  url: string;
  title?: string | null;
  page_type?: string | null;
  page_type_label?: string | null;
  issue_count?: number | null;
  crawl_status?: string | null;
};

export type RecommendationDetail = RecommendationListItem & {
  scan_id: string;
  grouping_key: string;
  scope: string;
  scope_identifier: string;
  rationale: string;
  action_steps: string[];
  evidence: Record<string, unknown>;
  issue_ids: string[];
  page_ids: string[];
  page_urls: string[];
  depends_on_recommendation_ids: string[];
  depends_on_recommendation_keys: string[];
  related_recommendations?: Array<{
    id: string;
    recommendation_key: string;
    title: string;
    category: string;
    priority: RecommendationPriority;
    status: RecommendationStatus;
  }>;
  affected_pages?: RecommendationAffectedPage[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type RecommendationsListResponse = {
  scan_id: string;
  items: RecommendationListItem[];
  pagination: { page: number; page_size: number; total: number; pages: number };
  summary: RecommendationSummary;
  analyzer_status: Record<string, AnalyzerRunStatus>;
  methodology: string;
  truncated?: boolean;
};

export type RecommendationDetailResponse = {
  scan_id: string;
  recommendation: RecommendationDetail;
  methodology?: string;
  analyzer_status?: Record<string, AnalyzerRunStatus>;
};

export type RecommendationQuery = {
  category?: string;
  priority?: string;
  impact?: string;
  effort?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort?: string;
  order?: string;
};

function recommendationQuery(params: RecommendationQuery = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "" || value === "all") {
      continue;
    }
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export async function getRecommendations(
  scanId: string,
  params: RecommendationQuery = {},
): Promise<RecommendationsListResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/recommendations${recommendationQuery(params)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as RecommendationsListResponse;
}

export async function getRecommendation(
  scanId: string,
  recommendationId: string,
): Promise<RecommendationDetailResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/recommendations/${encodeURIComponent(recommendationId)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as RecommendationDetailResponse;
}

export async function patchRecommendationStatus(
  scanId: string,
  recommendationId: string,
  status: RecommendationStatus,
): Promise<RecommendationDetailResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/recommendations/${encodeURIComponent(recommendationId)}`,
      {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as RecommendationDetailResponse;
}

function pagesQuery(params: PageQuery = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "" || value === "all") {
      continue;
    }
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export async function getPages(scanId: string, params: PageQuery = {}): Promise<PagesListResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/pages${pagesQuery(params)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as PagesListResponse;
}

export async function getPagesSummary(scanId: string): Promise<PagesSummaryResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/pages/summary`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as PagesSummaryResponse;
}

export async function getPage(scanId: string, pageId: string): Promise<PageDetailResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/pages/${encodeURIComponent(pageId)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as PageDetailResponse;
}

export type ArchitectureSummary = {
  page_count: number;
  internal_link_count: number;
  max_crawl_depth: number | null;
  average_crawl_depth: number | null;
  potential_orphan_count: number;
  dead_end_count: number;
  terminal_page_count?: number;
  no_outbound_count?: number;
  links_recorded?: boolean;
  external_links_discovered?: number;
};

export type ArchitectureNode = {
  id: string;
  page_id: string;
  scan_id?: string;
  url: string;
  normalized_url: string;
  final_url?: string | null;
  path: string;
  title?: string | null;
  h1?: string | null;
  page_type?: string | null;
  page_type_label?: string | null;
  depth: number;
  url_path_depth: number;
  crawl_status: CrawlStatus;
  http_status?: number | null;
  indexable?: boolean | null;
  canonical_url?: string | null;
  word_count?: number | null;
  issue_count: number;
  severity_counts?: Record<string, number>;
  inbound_link_count: number;
  outbound_link_count: number;
  potential_orphan: boolean;
  terminal_page: boolean;
  dead_end: boolean;
  is_seed?: boolean;
  skip_reason?: string | null;
  failure_reason?: string | null;
};

export type ArchitectureEdge = {
  id: string;
  source: string;
  target: string;
  source_page_id: string;
  destination_page_id: string;
  link_count: number;
  anchors?: string[];
};

export type ArchitectureLinkRow = {
  id: string;
  source_page_id: string;
  destination_page_id: string;
  source_url: string;
  destination_url: string;
  source_title?: string | null;
  destination_title?: string | null;
  source_path?: string;
  destination_path?: string;
  anchor_text?: string | null;
  rel?: string | null;
  destination_type?: string | null;
  destination_type_label?: string | null;
};

export type ArchitectureNeighbor = {
  id: string;
  source_page_id: string;
  destination_page_id: string;
  source_url: string;
  destination_url: string;
  anchor_text?: string | null;
  rel?: string | null;
  page_id: string;
  title?: string | null;
  path?: string;
  page_type?: string | null;
  page_type_label?: string | null;
};

export type ArchitectureResponse = {
  scan_id: string;
  status?: string;
  in_progress?: boolean;
  summary: ArchitectureSummary;
  graph: {
    shown: number;
    matching: number;
    total_pages: number;
    limited: boolean;
    limit: number;
    message?: string | null;
  };
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  items: ArchitectureNode[];
  pagination: { page: number; page_size: number; total: number; pages: number; total_pages?: number };
  depth_distribution: Array<{ depth: number; page_count: number }>;
  page_type_distribution: Array<{ page_type: string; label: string; page_count: number }>;
  url_path_structure: {
    groups: Array<{ path: string; url_path_depth: number; page_count: number; sample_title?: string | null }>;
    truncated?: boolean;
    note?: string;
  };
  insights: Array<{ id: string; text: string }>;
  notes: string[];
  limits?: { max_pages?: number; max_depth?: number; max_graph_nodes?: number };
};

export type ArchitecturePageResponse = {
  scan_id: string;
  status?: string;
  page: ArchitectureNode & { inbound_truncated?: boolean; outbound_truncated?: boolean };
  architecture: {
    crawl_depth: number;
    url_path_depth: number;
    inbound_internal_links: number;
    outbound_internal_links: number;
    potential_orphan: boolean;
    terminal_page: boolean;
    dead_end: boolean;
  };
  inbound_links: ArchitectureNeighbor[];
  outbound_links: ArchitectureNeighbor[];
  notes?: string[];
};

export type ArchitectureLinksResponse = {
  scan_id: string;
  status?: string;
  items: ArchitectureLinkRow[];
  pagination: { page: number; page_size: number; total: number; pages: number; total_pages?: number };
};

export type ArchitectureQuery = {
  search?: string;
  page?: number;
  page_size?: number;
  page_type?: string;
  crawl_status?: string;
  depth?: string;
  has_issues?: string;
  orphan?: string;
  terminal?: string;
  sort?: string;
  order?: string;
  graph_limit?: number;
  focus?: string;
};

export type ArchitectureLinksQuery = {
  search?: string;
  page?: number;
  page_size?: number;
  source?: string;
  destination?: string;
  sort?: string;
  order?: string;
};

function encodeQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "" || value === "all") {
      continue;
    }
    search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export async function getArchitecture(scanId: string, params: ArchitectureQuery = {}): Promise<ArchitectureResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/architecture${encodeQuery(params)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ArchitectureResponse;
}

export async function getArchitecturePage(scanId: string, pageId: string): Promise<ArchitecturePageResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/architecture/pages/${encodeURIComponent(pageId)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ArchitecturePageResponse;
}

export async function getArchitectureLinks(
  scanId: string,
  params: ArchitectureLinksQuery = {},
): Promise<ArchitectureLinksResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/architecture/links${encodeQuery(params)}`, {
      cache: "no-store",
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ArchitectureLinksResponse;
}

export type CompetitorStatus = "queued" | "scanning" | "completed" | "failed" | "cancelled";

export type CompetitorCard = {
  id: string;
  scan_id: string;
  name: string;
  url: string;
  normalized_url: string;
  competitor_scan_id: string;
  status: CompetitorStatus | ScanStatus;
  progress?: number | null;
  current_step?: string | null;
  pages_crawled?: number | null;
  pages_discovered?: number | null;
  issue_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
  error?: ScanErrorPayload | null;
};

export type CompetitorListResponse = {
  scan_id: string;
  primary: {
    url: string;
    status: ScanStatus;
    completed_at?: string | null;
    created_at?: string | null;
  };
  competitors: CompetitorCard[];
  max_competitors: number;
  limit_note: string;
  remaining: number;
};

export type ComparisonCell = {
  column_id: string;
  available: boolean;
  value?: number | string | null;
  display?: string | null;
  status?: string;
  score?: number | null;
  analyzed_pages?: number | null;
  available_checks?: number | null;
  issue_count?: number | null;
};

export type ComparisonMetric = {
  id: string;
  label: string;
  group: string;
  direction?: string;
  unit?: string | null;
  values: ComparisonCell[];
  differences?: Array<{ column_id: string; value: number; display: string }>;
};

export type ComparisonResponse = {
  primary: {
    column_id: string;
    label: string;
    scan_id: string;
    url: string;
    status: string;
    completed_at?: string | null;
    created_at?: string | null;
  };
  competitors: Array<{
    column_id: string;
    label: string;
    scan_id: string;
    competitor_scan_id: string;
    url: string;
    status: string;
    progress?: number | null;
    current_step?: string | null;
    completed_at?: string | null;
    created_at?: string | null;
    stale?: string | null;
    error?: ScanErrorPayload | null;
  }>;
  columns: Array<{ id: string; label: string; role: string; scan_id: string; url: string; status: string; completed_at?: string | null; created_at?: string | null }>;
  categories: Array<{ id: string; label: string; kind: string; values: ComparisonCell[] }>;
  metrics: ComparisonMetric[];
  issues: Array<{ issue_key: string; label: string; category: string; values: ComparisonCell[] }>;
  severity: Array<{ id: string; label: string; values: ComparisonCell[] }>;
  observations: Array<{ id: string; text: string }>;
  warnings: string[];
  methodology: {
    version: string;
    text: string;
    limitations: string;
    scope: string;
    max_pages: number;
    max_depth: number;
    viewports: Record<string, { width: number; height: number }>;
  };
  incomplete?: boolean;
};

export type CompetitorDetailResponse = {
  competitor: CompetitorCard;
  primary_scan_id: string;
  snapshot: {
    categories: Record<string, { available: boolean; score?: number | null; status?: string; issue_count?: number | null }>;
    issues?: { available: boolean; total?: number | null };
    pages?: { available: boolean; crawled?: number | null };
    architecture?: Record<string, unknown>;
    performance?: Record<string, unknown>;
    screenshots?: Array<{ viewport?: string; url?: string; width?: number; height?: number }>;
    completed_at?: string | null;
    error?: ScanErrorPayload | null;
  } | null;
  max_competitors: number;
  limit_note: string;
};

export type PageComparisonResponse = {
  primary_page?: Record<string, unknown>;
  competitor_page?: Record<string, unknown>;
  metrics?: Array<{ id: string; label: string; primary: unknown; competitor: unknown; primary_available?: boolean; competitor_available?: boolean }>;
  suggestions: Array<{ page_id: string; url: string; title?: string | null; page_type?: string | null; label: string; reasons: string[] }>;
};

export async function getCompetitors(scanId: string): Promise<CompetitorListResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/competitors`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as CompetitorListResponse;
}

export async function addCompetitor(scanId: string, name: string, url: string): Promise<{ competitor: CompetitorCard }> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/competitors`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, url }),
    });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as { competitor: CompetitorCard };
}

export async function getCompetitorComparison(scanId: string): Promise<ComparisonResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/scans/${encodeURIComponent(scanId)}/competitors/comparison`, { cache: "no-store" });
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as ComparisonResponse;
}

export async function getCompetitor(scanId: string, competitorId: string): Promise<CompetitorDetailResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/competitors/${encodeURIComponent(competitorId)}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as CompetitorDetailResponse;
}

export async function deleteCompetitor(scanId: string, competitorId: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/competitors/${encodeURIComponent(competitorId)}`,
      { method: "DELETE" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
}

export async function rescanCompetitor(scanId: string, competitorId: string): Promise<{ competitor: CompetitorCard }> {
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/competitors/${encodeURIComponent(competitorId)}/rescan`,
      { method: "POST" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as { competitor: CompetitorCard };
}

export async function getPageComparison(
  scanId: string,
  params: { primary_page_id: string; competitor_id: string; competitor_page_id?: string },
): Promise<PageComparisonResponse> {
  const search = new URLSearchParams();
  search.set("primary_page_id", params.primary_page_id);
  search.set("competitor_id", params.competitor_id);
  if (params.competitor_page_id) {
    search.set("competitor_page_id", params.competitor_page_id);
  }
  let response: Response;
  try {
    response = await fetch(
      `/api/scans/${encodeURIComponent(scanId)}/competitors/page-comparison?${search.toString()}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ScanApiError("ENGINE_UNAVAILABLE", "Unable to reach the scan engine. Try again in a moment.");
  }
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as PageComparisonResponse;
}
