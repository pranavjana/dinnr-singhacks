# Implementation Plan: MAS AML/CFT Document Crawler

**Branch**: `feat-mas-data-collection` | **Date**: 2025-11-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/feat-mas-data-collection/spec.md`

**Note**: This plan executes Phase 0 (Research) and Phase 1 (Design) workflows to generate implementation artifacts.

## Summary

Build a Python web scraper for the Monetary Authority of Singapore (MAS) regulatory website that collects AML/CFT-related documents (News, Circulars, Regulation pages) from the last 90 days, downloads associated PDFs, deduplicates by normalized URL + file hash, and returns structured JSON metadata optimized for downstream LLM analysis. The crawler will be architected as reusable Python functions suitable for wrapping in a FastAPI endpoint, with robust error handling (3-attempt exponential backoff), robots.txt compliance, and comprehensive logging for compliance audit trails.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Web scraping: `requests`, `BeautifulSoup4`
- Data validation: `Pydantic` (for schema validation and JSON output)
- API integration: `FastAPI` (for endpoint wrapping in Phase 2)
- Testing: `pytest` with `pytest-cov` for coverage
- Utilities: `python-dateutil` (date parsing), `urllib.parse` (URL normalization), `hashlib` (file hashing)

**Storage**: Local filesystem (PDFs downloaded to configurable directory); JSON output suitable for in-memory processing or file persistence
**Testing**: pytest with fixtures for mocked MAS website responses
**Target Platform**: Linux server (deployment-ready); runs on macOS/Windows for development
**Project Type**: Python library (single project, CLI-ready, FastAPI-wrappable)
**Performance Goals**: Full crawl cycle (News, Circulars, Regulation pages + PDF downloads) within 5 minutes under normal network conditions (SC-005)
**Constraints**:
- No external authentication required for MAS website access
- Respect robots.txt rules and rate limiting (user-agent header)
- Handle up to 50+ MB PDFs with configurable size limits
- Retry failed downloads up to 3 times with exponential backoff (1s, 2s, 4s)
- 90% PDF download success rate minimum (SC-003)

**Scale/Scope**:
- 10–50+ documents per crawl run (90-day window)
- ~2,000–10,000 lines of production code (crawler + tests + API wrapper)
- ~5–10 core modules (scraper, pdf_downloader, deduplicator, json_formatter, error_handler, logger, cli, api)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Alignment with DINNR AML Platform Constitution (v1.1.1)

**Assessment**: This feature is a **data-collection component** feeding into the broader AML agent ecosystem, not a user-facing agent itself. It must align with constitution principles while respecting its narrower scope.

| Principle | Requirement | Status | Justification |
|-----------|-------------|--------|---------------|
| **I. Agentic AI-First Architecture** | Core workflows as stateful multi-turn agents; LangGraph-based | **WAIVED for Phase 1** | This is a data-collection service, not an agentic decision system. LangGraph will be applied in the downstream *compliance rule extraction agent* that consumes this crawler's output. The crawler itself is deterministic, not agentic. |
| **III. Audit Trail & Compliance First** | Every decision logged with timestamp, user, rationale, regulatory reference | **APPROVED** | Crawler logs all fetch attempts, skipped documents, retries, PDF validation failures with timestamps and error codes. No sensitive data in logs (PII-safe). Suitable for compliance review. |
| **IV. Multi-Format Document Handling** | Support PDFs, images, text; OCR, tampering detection | **PARTIAL** | Phase 1 will focus on PDF download validation (file type check, hash verification). OCR and image tampering detection deferred to downstream document processing agent (out of scope for data-collection). |
| **V. Security & Data Minimization** | Encrypt at rest/transit; PII-safe logging; role-based access | **APPROVED** | PDFs stored locally with file permissions controlled at OS level. No sensitive client/transaction data in this crawler (only regulatory metadata). Logging is regulatory-metadata only (URLs, dates, error codes). Future FastAPI wrapper will enforce auth (scope for Phase 2). |
| **VI. Scalable, Observable Backend** | FastAPI metrics, structured JSON logs, SLAs (<500ms analysis, <5s document processing) | **PARTIAL** | Phase 1 will design FastAPI integration structure and logging schema. Performance SLA for this crawler is <5 minutes full cycle (SC-005). Prometheus metrics deferred to Phase 2 (FastAPI endpoint implementation). |
| **VII. Frontend UX for Compliance Officers** | Not applicable to data-collection service | **N/A** | This is a backend service. Frontend integration (dashboard to trigger crawls, view results) is out of scope. |

**Constitution Status**: ✅ **GATE PASSED**
- No violations of core principles.
- Audit logging and security baseline standards met.
- Deferred LangGraph/agent integration and advanced observability to downstream consumers and Phase 2.
- Feature scope is appropriately bounded as a data utility, not a decision system.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mas_crawler/
├── __init__.py
├── config.py                      # Configuration (API keys, download dir, timeouts, retry params)
├── models.py                      # Pydantic models (Document, CrawlSession, Category, etc.)
├── scraper.py                     # Main scraper logic (fetch pages, parse documents)
├── pdf_downloader.py              # PDF download & validation logic
├── deduplicator.py                # Duplicate detection (normalized URL + file hash)
├── logger.py                      # Structured logging (compliance-audit-ready)
├── cli.py                         # CLI entry point (trigger crawls, configure)
├── api.py                         # FastAPI endpoint wrapper (Phase 2)
└── errors.py                      # Custom exception classes

tests/
├── __init__.py
├── conftest.py                    # pytest fixtures (mock MAS responses)
├── unit/
│   ├── test_scraper.py           # Unit tests for document discovery
│   ├── test_pdf_downloader.py    # Unit tests for PDF download & retry logic
│   ├── test_deduplicator.py      # Unit tests for duplicate detection
│   ├── test_models.py            # Pydantic model validation tests
│   └── test_logger.py            # Logging output validation
├── integration/
│   ├── test_full_crawl.py        # End-to-end crawl with mocked MAS responses
│   ├── test_json_output.py       # Validate JSON schema and field consistency
│   └── test_error_handling.py    # Test resilience (retries, HTTP errors, missing fields)
└── contract/
    └── test_api_contract.py       # (Phase 2) FastAPI endpoint contract tests

docs/
├── README.md                      # Installation, quick start, configuration
├── api_contract.md                # OpenAPI schema (Phase 1)
└── architecture.md                # Design decisions, module responsibilities

requirements.txt                    # Python dependencies
pytest.ini                         # pytest configuration
.env.example                       # Example environment variables
```

**Structure Decision**: Single Python project with clear module separation. Crawler is a library (importable `mas_crawler` package) with optional CLI and FastAPI wrapper. This enables:
- Unit testing of each component independently
- Integration testing of full crawl pipeline
- Easy wrapping in FastAPI endpoint (Phase 2)
- Future reuse in other contexts (scheduled jobs, batch processing)

## Complexity Tracking

> **No constitution violations identified. No complexity justifications required.**

All design decisions align with constitution principles (audit logging, security baseline, scope clarity). Single Python project is optimal for this scope.

---

## Phase 0 & Phase 1 Deliverables ✅

### Phase 0 (Research) Complete

**Output**: `research.md`
- ✅ All NEEDS CLARIFICATION resolved (5 questions asked and answered)
- ✅ Technology stack decisions documented with rationale
- ✅ Error handling & graceful degradation strategy defined
- ✅ Logging & observability approach (JSON compliance audit logs)
- ✅ API contract and FastAPI integration strategy (Phase 2 reference)
- ✅ Assumptions and constraints confirmed

**Key Decisions**:
1. Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s)
2. robots.txt compliance + descriptive user-agent header
3. Hybrid duplicate detection (normalized URL + SHA-256 file hash)
4. Pragmatic data quality (return nulls, don't drop documents)
5. 90-day "recent" documents window

### Phase 1 (Design) Complete

**Outputs**:
1. **data-model.md** - Pydantic models for Document, CrawlSession, Category, CrawlResult with validation rules
2. **quickstart.md** - Installation, configuration, CLI usage, Python API, logging, troubleshooting
3. **contracts/openapi.yaml** - OpenAPI 3.0 schema for FastAPI endpoint (Phase 2 reference)

**Artifacts Generated**:
- ✅ Entity definitions with field specifications and constraints
- ✅ Validation rules (min/max, format, type checks)
- ✅ JSON schema generation via Pydantic (auto-generated, ready for API documentation)
- ✅ Error handling and missing field strategies
- ✅ API contract ready for Phase 2 FastAPI implementation

---

## Next Phase: Implementation (Phase 2)

The plan is ready for `/speckit.tasks` to generate detailed implementation tasks.

**Phase 2 scope** (tasks will be auto-generated):
- Implement Python modules (scraper.py, pdf_downloader.py, deduplicator.py, etc.)
- Write unit and integration tests
- FastAPI endpoint wrapper (optional Phase 2; detailed in OpenAPI contract)
- CLI interface
- Docker packaging and deployment

**Ready for**: `/speckit.tasks` command to generate implementation plan with dependency-ordered tasks
