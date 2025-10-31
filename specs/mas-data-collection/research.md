# Research & Design Decisions: MAS AML/CFT Document Crawler

**Date**: 2025-11-01 | **Feature**: feat-mas-data-collection | **Phase**: 0 (Research)

---

## Overview

This document consolidates research findings and design decisions to resolve all clarifications and technical unknowns identified during specification. All items marked as "NEEDS CLARIFICATION" in the spec have been addressed through user input and best-practices analysis.

---

## 1. Retry & Resilience Policy

**Decision**: Implement 3 retries with exponential backoff (1s, 2s, 4s) for failed PDF downloads.

**Rationale**:
- Exponential backoff is industry-standard for transient network failures (503s, timeouts).
- 3 retries balances resilience against excessive delays and server load.
- Prevents hammering the MAS server while recovering from temporary network glitches.
- Total retry time: 1+2+4 = 7 seconds per failed download before marking as permanently failed.
- Aligns with production best practices (e.g., AWS SDK, Requests library with Tenacity).

**Alternatives Considered**:
- No retries: Risk losing documents due to transient network issues; spec requires SC-008 (no single failure halts crawl).
- Linear backoff (2s each): Simpler but less effective for cascade failures; exponential is more forgiving.
- Adaptive retry (error-type dependent): More complex; exponential backoff works well across 4xx, 5xx, timeout cases.
- Very high retries (5+): Diminishing returns; 3 is sufficient for most real-world scenarios.

**Implementation Details**:
- Applies to both page fetches and PDF downloads.
- Logged separately: each retry attempt recorded with timestamp and error code.
- Timeout per attempt: configurable (default 30s for pages, 60s for large PDFs).

---

## 2. Website Authentication & robots.txt Compliance

**Decision**: No authentication needed; crawler MUST respect robots.txt rules and include descriptive user-agent header.

**Rationale**:
- MAS website (www.mas.gov.sg) provides public access to News, Circulars, Regulation pages without authentication (confirmed by spec assumption).
- Respecting robots.txt is both legally/ethically sound and practical:
  - Avoids IP blocks and legal friction with MAS.
  - Demonstrates responsible scraping behavior toward institutional websites.
  - Standard practice for regulated-sector data collection.
- User-agent header identifies the crawler (e.g., `Mozilla/5.0 (+AML Crawler/1.0; compliance-audit)`) for transparency and debugging.
- Rate limiting via `robots.txt` directives (e.g., crawl delay) is easier than implementing adaptive throttling logic.

**Alternatives Considered**:
- Ignore robots.txt: High risk of IP blocking; violates web scraping etiquette; not recommended for institutional sites.
- Implement custom rate limiting (1 req/2s): Overkill if robots.txt already specifies rules; adds complexity.
- Handle authentication (OAuth, Basic Auth): Not needed per spec assumption; adds unnecessary complexity.

**Implementation Details**:
- Parse robots.txt at start of crawl; cache for duration of session.
- Skip any URLs listed under `Disallow` for user-agent `*` or `mas-crawler-bot`.
- User-agent header: `Mozilla/5.0 (compatible; MASAMLCrawler/1.0; +https://yourorg/mas-crawler-policy)`
- Log any robots.txt directives found (e.g., crawl-delay, request-rate) for audit trail.

---

## 3. Duplicate Detection Strategy

**Decision**: Hybrid approach using normalized URL for initial detection, then file hash (MD5 or SHA-256) validation.

**Rationale**:
- **Normalized URL** (remove query params, fragments) catches most duplicates efficiently (O(1) hash table lookup).
- **File hash** validates true content duplicates even when URLs differ (e.g., same PDF hosted at different URLs, or content redistributed).
- Hybrid approach is production-grade for compliance scenarios where document integrity matters:
  - Fast initial check avoids re-downloading obvious duplicates.
  - Deep content check prevents false positives (same content, different URL = should skip).
  - Maintains audit trail of why a document was skipped (URL already seen? Content hash already seen?).

**Alternatives Considered**:
- Exact URL match only: Misses content duplicates at different URLs; insufficient for compliance use case.
- Content hash only: Slow (requires download before checking); defeats purpose of deduplication.
- Fuzzy URL matching (Levenshtein): Adds complexity; normalized URL is sufficient for 95% of cases.

**Implementation Details**:
- **Normalized URL**: `urllib.parse.urlparse()` + remove query string and fragment; use as dictionary key.
- **File hash**: SHA-256 of PDF file (not expensive; standard practice); compute after download validation.
- **Storage**: Maintain deduplication database (in-memory dict for single crawl, optional persistent JSON for multi-crawl sessions).
- **Log entry**: Record which rule triggered skip (e.g., "Skipped: normalized URL already seen"; "Skipped: SHA-256 hash matches previous download").

---

## 4. Data Quality Thresholds

**Decision**: Pragmatic approach—return documents even with missing required fields; mark missing fields as `null` or `"unknown"`.

**Rationale**:
- Downstream LLM needs maximum data to work with; excluding partially complete documents loses valuable regulatory info.
- Explicit `null`/`"unknown"` values signal to downstream systems (LLM) that data is incomplete, enabling confidence scoring.
- Aligns with spec clarification (Q4) and edge case handling: don't silently drop data; mark it clearly.
- Enables compliance officers to review what was discoverable vs. what was unavailable.

**Alternatives Considered**:
- Strict mode (exclude docs with missing fields): Loses potentially important documents; not suitable for regulatory compliance.
- Inferring missing fields (extract date from URL): Fragile; if inference fails, harder to debug.
- Scoring confidence per document: More complex; pragmatic approach with null handling is sufficient.

**Implementation Details**:
- **Required fields**: title, publication_date, category, source_url, downloaded_pdf_path.
- **Missing field value**: `null` in JSON (not string `"null"`); optional fields set to `null` if not discovered.
- **Data quality metadata** (optional): Add `_data_quality_notes` field to each document listing which fields are `null` and why (e.g., "publication_date: not found in HTML"; "downloaded_pdf_path: download failed").
- **Validation**: Pydantic model allows optional fields; downstream LLM handles `null` gracefully.

---

## 5. "Recent" Documents Definition

**Decision**: 90-day window; documents published in the last 90 days are considered "recent".

**Rationale**:
- 90 days aligns with quarterly regulatory cycles (Q1, Q2, Q3, Q4) and MAS guidance release patterns.
- Captures "fresh" compliance guidance without being overly restrictive (30 days might miss important circulars).
- Broad enough for sustainable compliance monitoring without excessive historical archive burden.
- Matches common regulatory reporting periods and AML risk reassessment windows.

**Alternatives Considered**:
- 30 days: Too restrictive; risks missing important quarterly circulars.
- 1 year: Too broad; maintenance overhead; not "recent" enough for active compliance teams.
- No cutoff (all documents): Eliminates concept of "recent"; less useful for actively monitoring new guidance.
- Variable window (config param): Adds flexibility but also complexity; fixed 90-day window is simpler and sufficient.

**Implementation Details**:
- **Cutoff calculation**: `datetime.now() - timedelta(days=90)`.
- **Filter logic**: Exclude documents with `publication_date < cutoff_date`.
- **Configurable** (optional): Allow override via `--days-back` CLI parameter for specific use cases.
- **Logging**: Record cutoff date at start of crawl; log how many documents were filtered out (outside 90-day window).

---

## Technology Stack Decisions

### Web Scraping: requests + BeautifulSoup4

**Decision**: Use `requests` for HTTP + `BeautifulSoup4` for HTML parsing.

**Rationale**:
- Industry-standard for regulatory web scraping; widely tested and documented.
- `requests` handles retries, timeouts, user-agent headers, cookies seamlessly.
- `BeautifulSoup4` is lightweight, Pythonic, and sufficient for static HTML parsing (MAS pages don't require JavaScript rendering).
- Alternative (Selenium, Puppeteer): Overkill for static pages; slower and heavier.

### Data Validation: Pydantic v2

**Decision**: Use Pydantic v2 for schema validation and JSON serialization.

**Rationale**:
- Ensures JSON output is structurally correct (required for downstream LLM parsing).
- Automatic validation of data types (dates, URLs, file paths).
- Built-in JSON schema generation (useful for API documentation and type hints).
- Aligns with FastAPI standard practice (Phase 2 integration).

### Hashing: hashlib (SHA-256)

**Decision**: Use Python standard library `hashlib.sha256()` for file deduplication.

**Rationale**:
- SHA-256 is cryptographically secure and standard for file integrity checks.
- No external dependency required.
- Fast enough for typical PDF file sizes (even 50+ MB files hash in <1 second).

### Testing: pytest

**Decision**: Use pytest for all test automation (unit, integration, contract).

**Rationale**:
- Pythonic, flexible, industry-standard.
- Supports fixtures for mocking MAS responses.
- Easy integration with CI/CD (GitHub Actions, etc.).
- Coverage reporting via `pytest-cov`.

---

## Logging & Observability

**Decision**: Structured JSON logging with compliance audit trail.

**Rationale**:
- Compliance audit trails require structured, immutable logs (not free-form text).
- JSON format enables downstream parsing for monitoring dashboards and compliance reviews.
- Constitution Principle III (Audit Trail & Compliance First) mandates comprehensive decision logging.

**Log Schema** (per log entry):
```json
{
  "timestamp": "2025-11-01T14:35:42.123Z",
  "event": "document_discovered",
  "document_url": "https://www.mas.gov.sg/news/..."
  "document_title": "Notice on AML/CFT Requirements",
  "publication_date": "2025-10-15",
  "category": "News",
  "status": "success",
  "details": {}
}
```

**Log Levels**:
- INFO: Document discovery, PDF download start/success, crawl start/end.
- WARNING: Retry attempt, missing field, broken link.
- ERROR: Permanent download failure, robots.txt violation, parse error.

---

## Error Handling & Graceful Degradation

**Decision**: Log errors and continue (don't halt entire crawl on single failure).

**Rationale**:
- Spec requirement SC-008: "Crawler continues operation when encountering individual failures; no single broken link or network timeout halts the entire crawl process."
- Pragmatic: A 10% failure rate is better than 100% data loss.
- Enables compliance teams to review partial results and remediate incomplete documents later.

**Failure Modes** (and handling):
1. **HTTP 404/410 (page not found)**: Log warning; skip page.
2. **HTTP 5xx (server error)**: Retry (3x exponential backoff); if all retries fail, log error; move to next document.
3. **Timeout (page fetch)**: Retry (3x exponential backoff); log error after final failure.
4. **PDF broken link**: Log warning; mark `downloaded_pdf_path` as `null`; continue.
5. **PDF non-PDF content**: Log warning; reject download; mark as `null`.
6. **PDF too large (>50MB)**: Log warning; skip; mark as `null` (configurable size limit).
7. **Missing publication_date**: Log info; set to `null`; return document (per data quality decision).
8. **robots.txt disallows URL**: Log info; skip URL entirely; increment `documents_skipped` counter.

---

## API Contract & FastAPI Integration (Phase 2)

**Decision**: Design `crawl()` function for easy FastAPI wrapping; create OpenAPI schema as artifact.

**Rationale**:
- Spec requirement: "structure the code so it can later integrate with a FastAPI endpoint."
- Clean separation: core library functions are testable independently; FastAPI wrapper is thin.

**Core Function Signature** (to be exposed via FastAPI):
```python
def crawl(
    days_back: int = 90,
    output_format: str = "json",
    include_pdfs: bool = True,
    download_dir: str = "./downloads"
) -> dict:
    """Execute full crawl: fetch documents, download PDFs, deduplicate, return JSON."""
    pass
```

**FastAPI Endpoint** (Phase 2):
```python
@app.post("/api/v1/crawl")
async def crawl_endpoint(
    days_back: int = Query(90, ge=1, le=365),
    include_pdfs: bool = Query(True),
    download_dir: str = Query("./downloads")
) -> CrawlResult:
    """Trigger MAS document crawl. Returns JSON with document metadata and download paths."""
    pass
```

**OpenAPI Contract** (Phase 1): Generated via `pydantic.json_schema()` and documented in `contracts/openapi.yaml`.

---

## Assumptions & Constraints (Confirmed)

### Confirmed Assumptions:
1. ✅ MAS website HTML structure is consistent (at least within 90-day update window).
2. ✅ Publication dates are present and ISO-8601 compatible (or easily parseable).
3. ✅ PDF links are direct URLs (no JavaScript rendering needed).
4. ✅ No authentication required for public pages.
5. ✅ Local filesystem storage available and writable.
6. ✅ Network connectivity is generally reliable (temporary timeouts expected and retried).
7. ✅ Crawler runs on-demand or scheduled (not continuously).
8. ✅ robots.txt rules are published and crawl-delay/request-rate discoverable.

### Confirmed Constraints:
1. ✅ No external databases required (output is JSON file + local PDFs).
2. ✅ No user authentication for crawler itself (FastAPI auth is Phase 2).
3. ✅ No multi-language support (English-language documents only, initially).
4. ✅ No real-time monitoring (batch/scheduled execution).
5. ✅ PDF size limit: configurable; default 50MB (skip oversized files).

---

## Design Patterns & Best Practices

### 1. Separation of Concerns
- **scraper.py**: Page fetching and HTML parsing only.
- **pdf_downloader.py**: PDF download, validation, retry logic.
- **deduplicator.py**: Duplicate detection (URL + hash).
- **logger.py**: Structured logging.
- **models.py**: Data validation and serialization.

### 2. Dependency Injection
- Configuration (timeouts, download dir, API keys) passed to functions; not global state.
- Enables testability and reusability in different environments.

### 3. Error Handling
- Custom exception classes (e.g., `PDFDownloadError`, `RobotsViolation`) for clear error semantics.
- Graceful degradation: log errors, continue processing.

### 4. Testing Strategy
- **Unit tests**: Mock `requests` responses; test each module independently.
- **Integration tests**: Full crawl with mocked MAS HTML; validate JSON output schema.
- **Contract tests** (Phase 2): FastAPI endpoint validates request/response schema.

---

## Success Metrics & Validation

All success criteria from spec are measurable and testable:

| Criterion | Validation Method |
|-----------|-------------------|
| SC-001: 10+ documents in 90-day window | Assertion on `len(results)` >= 10 |
| SC-002: All fields present (null if missing) | JSON schema validation; no document without required keys |
| SC-003: 90% PDF download rate | Assertion on `downloaded_count / total_pdf_links >= 0.9` |
| SC-004: Zero duplicates on re-run | Compare results of run #1 vs. run #2; assert zero overlap |
| SC-005: Full crawl <5 minutes | Measure `end_time - start_time`; assert <300s |
| SC-006: LLM parseable JSON | Validate against Pydantic schema; attempt LLM parsing (mock) |
| SC-007: Error logging complete | Inspect JSON logs; verify all failures logged with timestamp + reason |
| SC-008: Crawler doesn't crash on failure | Run with mocked 100% failure rate for one component; assert crawl continues |

---

## Next Steps (Phase 1 Deliverables)

1. **data-model.md**: Detailed Pydantic models, field definitions, validation rules.
2. **contracts/openapi.yaml**: OpenAPI 3.0 schema for FastAPI endpoint (Phase 2 reference).
3. **quickstart.md**: Developer setup, running first crawl, configuring options.
4. **Update agent context**: Run `.specify/scripts/bash/update-agent-context.sh` to register crawler in agent memory.

---

**Research Complete ✅** All clarifications resolved. Ready for Phase 1 (Design).
