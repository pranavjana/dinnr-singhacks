# Implementation Tasks: MAS AML/CFT Document Crawler

**Feature**: feat-mas-data-collection | **Branch**: `feat-mas-data-collection`
**Created**: 2025-11-01 | **Status**: Ready for Implementation
**Priority**: MVP-focused (User Stories 1, 2, 3 before Story 4)

---

## Overview & Strategy

This document defines all implementation tasks for the MAS crawler feature, organized by phase and user story. Each task is independently actionable and follows the checklist format for tracking progress.

**Implementation Strategy**:
1. **Phase 1**: Setup infrastructure (project skeleton, dependencies, config)
2. **Phase 2**: Foundational layers (models, logging, error handling)
3. **Phase 3**: User Story 1 (Document Discovery) — Core MVP
4. **Phase 4**: User Story 2 (PDF Downloads) — Extends MVP
5. **Phase 5**: User Story 3 (LLM Output) — Completes core feature
6. **Phase 6**: User Story 4 (FastAPI Integration) — Production-ready
7. **Phase 7**: Polish & deployment

**MVP Scope**: Phases 1–5 (Stories 1–3) deliver core value; Story 4 is post-MVP.

---

## Phase 1: Setup & Infrastructure

Initialize project structure, dependencies, and foundational configuration.

**Goals**:
- Create project directory structure per plan.md
- Install and configure Python environment
- Set up CI/CD and pre-commit hooks
- Enable development workflow

### Setup Tasks

- [X] T001 Create Python project structure in `src/mas_crawler/` with all module stubs (__init__.py, config.py, models.py, scraper.py, pdf_downloader.py, deduplicator.py, logger.py, cli.py, api.py, errors.py)
- [X] T002 Create `tests/` directory structure with `unit/`, `integration/`, `contract/` subdirectories and `conftest.py`
- [X] T003 Create `docs/` directory with README.md, api_contract.md, architecture.md stubs
- [X] T004 Initialize `requirements.txt` with dependencies: requests==2.31.0, beautifulsoup4==4.12.2, pydantic==2.5.0, python-dateutil==2.8.2, pytest==7.4.3, pytest-cov==4.1.0
- [X] T005 Create `.env.example` with sample configuration (download dir, timeouts, retry params, user agent)
- [X] T006 Create `pytest.ini` configuration file with test discovery patterns and output options
- [X] T007 Create `.gitignore` excluding `venv/`, `__pycache__/`, `.env`, `.pytest_cache/`, `htmlcov/`, `downloads/`
- [ ] T008 Create GitHub Actions workflow (`.github/workflows/tests.yml`) for pytest and coverage on PR (SKIPPED - local testing only)
- [X] T009 Create `setup.py` or `pyproject.toml` for package metadata and installation

---

## Phase 2: Foundational Components

Implement core data models, configuration, logging, and error handling (blocking prerequisites for all user stories).

**Goals**:
- Define and validate all data entities (Pydantic models)
- Establish configuration management
- Implement structured logging for compliance audit trails
- Define error handling strategy

### Models & Data Validation

- [X] T010 [P] Implement `Category` enum (News, Circular, Regulation) in `src/mas_crawler/models.py`
- [X] T011 [P] Implement `Document` Pydantic model in `src/mas_crawler/models.py` with fields: title, publication_date, category, source_url, normalized_url, downloaded_pdf_path, file_hash, download_timestamp, data_quality_notes
- [X] T012 [P] Implement `CrawlSession` Pydantic model in `src/mas_crawler/models.py` with fields: session_id, start_time, end_time, duration_seconds, documents_found, documents_downloaded, documents_skipped, errors_encountered, errors_details, success, crawl_config
- [X] T013 [P] Implement `CrawlResult` Pydantic model in `src/mas_crawler/models.py` with fields: session (CrawlSession), documents (List[Document])
- [X] T014 Add Pydantic validation rules to Document model (title min/max length, URL format, file_hash hex pattern)
- [X] T015 Add Pydantic validation rules to CrawlSession model (counts >= 0, duration >= 0)
- [X] T016 Write unit tests for model validation in `tests/unit/test_models.py` (valid document, invalid title, invalid hash, etc.)

### Configuration Management

- [X] T017 [P] Implement `Config` class in `src/mas_crawler/config.py` with properties: download_dir, request_timeout, pdf_timeout, max_pdf_size_mb, retry_max_attempts, user_agent, log_level
- [X] T018 [P] Implement `Config.from_env()` classmethod to load configuration from environment variables (with defaults)
- [X] T019 Write unit tests for Config in `tests/unit/test_config.py` (from_env, defaults, env override)

### Error Handling

- [X] T020 [P] Define custom exception classes in `src/mas_crawler/errors.py`: `MASCrawlerError` (base), `HTTPError`, `PDFDownloadError`, `ParseError`, `RobotsViolation`, `DataValidationError`
- [X] T021 Write documentation in errors.py explaining when each exception is raised

### Logging

- [X] T022 [P] Implement structured logging in `src/mas_crawler/logger.py` with `setup_logging()` function
- [X] T023 Configure JSON logging output with fields: timestamp, event, level, details, document_url (if applicable)
- [X] T024 Implement log level control via environment variable and config
- [X] T025 Write unit tests for logging format in `tests/unit/test_logger.py` (valid JSON, required fields)

---

## Phase 3: User Story 1 — Compliance Officer Collects Latest MAS Guidance (P1)

Implement document discovery from MAS website (News, Circulars, Regulation pages).

**Goals**:
- Scrape MAS website pages to discover documents
- Extract metadata (title, date, category, URL)
- Filter by 90-day recency window
- Return structured document list

**Acceptance Criteria**:
- ✅ Returns JSON list with ≥5 documents from MAS
- ✅ All documents have title, publication_date, category, source_url fields (null if missing)
- ✅ Documents from all 3 sections (News, Circulars, Regulation) included
- ✅ Only documents from last 90 days included

### US1 Implementation Tasks

- [X] T026 [US1] Implement `MASCrawler` class skeleton in `src/mas_crawler/scraper.py` with `__init__` accepting Config
- [X] T027 [US1] Implement `fetch_page()` method in scraper.py with requests library, timeout, user-agent header, error handling
- [X] T028 [US1] Implement robots.txt parser in `src/mas_crawler/scraper.py` (parse and check disallow rules)
- [X] T029 [US1] Implement `parse_news_page()` method to extract documents from MAS News section (CSS selectors)
- [X] T030 [US1] Implement `parse_circulars_page()` method to extract documents from MAS Circulars section (CSS selectors)
- [X] T031 [US1] Implement `parse_regulation_page()` method to extract documents from MAS Regulation section (CSS selectors)
- [X] T032 [US1] Implement date parsing with `python-dateutil` to convert MAS dates to ISO-8601 format
- [X] T033 [US1] Implement 90-day recency filter (exclude docs older than datetime.now() - timedelta(days=90))
- [X] T034 [US1] Implement URL normalization in `src/mas_crawler/deduplicator.py` (remove query params, fragments, lowercase)
- [X] T035 [US1] Implement `crawl()` method in `MASCrawler` that orchestrates fetch_page → parse → filter → return CrawlResult
- [X] T036 [US1] Implement error logging for HTTP errors, parse errors, missing fields (log but continue)
- [X] T037 [US1] Write integration tests for full crawl in `tests/integration/test_full_crawl.py` (mocked MAS responses)
- [X] T038 [US1] Write unit tests for page parsers in `tests/unit/test_scraper.py` (valid HTML, missing fields, date parsing)

---

## Phase 4: User Story 2 — System Downloads and Stores Associated PDFs (P1)

Implement PDF download, validation, and retry logic.

**Goals**:
- Download PDFs from document URLs
- Validate PDF file format
- Implement 3-attempt retry with exponential backoff
- Store with meaningful filenames

**Acceptance Criteria**:
- ✅ PDFs downloaded to local directory with clear filenames
- ✅ Failed downloads retried 3x with exponential backoff (1s, 2s, 4s)
- ✅ Crawler continues on download failures (doesn't crash)
- ✅ 90%+ PDF download success rate

### US2 Implementation Tasks

- [X] T039 [P] [US2] Implement `PDFDownloader` class in `src/mas_crawler/pdf_downloader.py` with `__init__` accepting Config
- [X] T040 [P] [US2] Implement `download_pdf()` method with retry logic (3 attempts, exponential backoff 1s/2s/4s)
- [X] T041 [P] [US2] Implement PDF file validation (check magic bytes `%PDF`, file size < max_pdf_size_mb)
- [X] T042 [P] [US2] Implement SHA-256 hashing of downloaded PDF for deduplication
- [X] T043 [P] [US2] Implement safe filename generation (sanitize URLs, avoid path traversal)
- [X] T044 [P] [US2] Implement directory creation (create download_dir if not exists)
- [X] T045 [P] [US2] Implement timeout handling (separate timeouts for page fetch vs PDF download per spec)
- [X] T046 [P] [US2] Integrate PDFDownloader into `MASCrawler.crawl()` workflow
- [X] T047 [US2] Write unit tests for PDFDownloader in `tests/unit/test_pdf_downloader.py` (valid PDF, invalid content, retry logic, timeout)
- [X] T048 [US2] Write integration tests in `tests/integration/test_pdf_download.py` (full download pipeline with mocked responses)
- [X] T049 [US2] Verify Document model fields updated (downloaded_pdf_path, file_hash, download_timestamp) in crawl results

---

## Phase 5: User Story 3 — Structured Output Enables LLM Processing (P1)

Ensure JSON output is LLM-parseable with consistent field naming and types.

**Goals**:
- Validate all fields match expected data types
- Ensure JSON schema matches Pydantic models
- Test LLM parsing compatibility
- Document output format

**Acceptance Criteria**:
- ✅ All fields consistently named (snake_case)
- ✅ All dates in ISO-8601 format (UTC)
- ✅ All URLs valid (HttpUrl Pydantic validation)
- ✅ Category field clearly identifies source (News, Circular, Regulation)
- ✅ JSON parseable without transformation

### US3 Implementation Tasks

- [X] T050 [US3] Implement JSON schema validation in `src/mas_crawler/models.py` using Pydantic's `model_json_schema()`
- [X] T051 [US3] Implement `CrawlResult.model_dump_json()` output (Pydantic serialization)
- [X] T052 [US3] Write validation tests in `tests/unit/test_json_output.py` (schema consistency, data types, field names)
- [X] T053 [US3] Write integration test in `tests/integration/test_json_output.py` validating JSON against schema
- [X] T054 [US3] Add type hints to all crawler functions (return types, parameter types)
- [X] T055 [US3] Generate OpenAPI schema from Pydantic models for API documentation
- [X] T056 [US3] Document JSON output structure in `docs/api_contract.md` (field descriptions, examples)
- [X] T057 [US3] Test LLM-parsing compatibility (mock LLM parsing test in `tests/integration/test_llm_parsing.py`)

---

## Phase 6: User Story 4 — Integration with FastAPI Endpoint (P2)

Wrap crawler as FastAPI endpoint for HTTP trigger and automated scheduling.

**Goals**:
- Create FastAPI wrapper for crawler
- Expose `/api/v1/crawl` POST endpoint
- Support optional filter parameters
- Return HTTP 200 with CrawlResult JSON

**Acceptance Criteria**:
- ✅ FastAPI app imports and wraps crawler functions
- ✅ Endpoint accepts filter parameters (days_back, include_pdfs, etc.)
- ✅ Endpoint returns HTTP 200 with JSON
- ✅ Appropriate HTTP error codes (400, 500)

### US4 Implementation Tasks

- [X] T058 [US4] Implement FastAPI app in `src/mas_crawler/api.py` with dependency injection for Config, logging
- [X] T059 [US4] Implement `POST /api/v1/crawl` endpoint accepting optional parameters (days_back, include_pdfs, download_dir, max_pdf_size_mb)
- [X] T060 [US4] Implement request validation with Pydantic `CrawlRequest` model
- [X] T061 [US4] Implement response serialization with `CrawlResult` model
- [X] T062 [US4] Implement error handling (HTTP 400 for invalid params, HTTP 500 for crawl errors)
- [X] T063 [US4] Implement `/api/v1/crawl/status/{session_id}` GET endpoint (optional, for async crawls in future)
- [X] T064 [US4] Write contract tests in `tests/contract/test_api_contract.py` (request/response schema, HTTP status codes)
- [X] T065 [US4] Write integration tests for FastAPI endpoint in `tests/integration/test_fastapi_integration.py`
- [X] T066 [US4] Create `main.py` or `app.py` to run FastAPI dev server (example: `if __name__ == "__main__": uvicorn.run(...)`)

---

## Phase 7: CLI Interface & Polish

Implement command-line interface for standalone usage and final quality checks.

**Goals**:
- Make crawler executable via CLI
- Support configuration via CLI args
- Implement help and error messages
- Final testing and documentation

### CLI & Polish Tasks

- [ ] T067 Implement CLI in `src/mas_crawler/cli.py` using argparse (subcommands: crawl, validate-output, help)
- [ ] T068 Implement `crawl` subcommand accepting --days-back, --download-dir, --include-pdfs, --output-file options
- [ ] T069 Implement `validate-output` subcommand to validate JSON output against schema
- [ ] T070 Add `__main__.py` to make package executable (`python -m mas_crawler crawl`)
- [ ] T071 Implement proper exit codes (0 for success, 1 for errors, 2 for argument errors)
- [ ] T072 Write help text and usage examples in CLI
- [ ] T073 Write end-to-end test in `tests/integration/test_cli.py` (crawl via CLI, validate output file)

### Documentation

- [ ] T074 Write `docs/README.md` with installation, configuration, and quickstart
- [ ] T075 Write `docs/architecture.md` documenting module responsibilities and data flow
- [ ] T076 Add docstrings to all public functions and classes (Google style)
- [ ] T077 Generate API documentation from OpenAPI schema in `docs/api_contract.md`
- [ ] T078 Create CHANGELOG.md documenting features and known limitations

### Testing & Quality

- [ ] T079 [P] Run full test suite with coverage (`pytest tests/ --cov=mas_crawler`)
- [ ] T080 [P] Verify ≥80% code coverage for production code (src/mas_crawler/)
- [ ] T081 [P] Run linting (Ruff for Python code style) and fix violations
- [ ] T082 [P] Type checking with mypy on all modules
- [ ] T083 Add pre-commit hooks configuration (`.pre-commit-config.yaml`) for linting, type checks, tests

### Deployment & Final

- [ ] T084 Create `Dockerfile` for containerized deployment
- [ ] T085 Create `docker-compose.yml` for local development (optional)
- [ ] T086 Document deployment steps in `docs/DEPLOYMENT.md`
- [ ] T087 Final manual testing: crawl live MAS website, verify output, review logs
- [ ] T088 Create release notes and version bump (v1.0.0-alpha or v1.0.0)

---

## Task Summary & Dependency Graph

### Task Count by Phase

| Phase | Name | Task Count | Parallelizable |
|-------|------|-----------|-----------------|
| 1 | Setup & Infrastructure | 9 tasks | 3 tasks [P] |
| 2 | Foundational Components | 16 tasks | 8 tasks [P] |
| 3 | User Story 1 (Document Discovery) | 13 tasks | 3 tasks [P] |
| 4 | User Story 2 (PDF Downloads) | 11 tasks | 8 tasks [P] |
| 5 | User Story 3 (LLM Output) | 8 tasks | 2 tasks [P] |
| 6 | User Story 4 (FastAPI) | 9 tasks | 2 tasks [P] |
| 7 | CLI & Polish | 22 tasks | 10 tasks [P] |
| **TOTAL** | **All Phases** | **88 tasks** | **36 tasks [P]** |

### User Story Completion Order

1. **User Story 1** (Document Discovery): T026–T038 ← **MVP core**
2. **User Story 2** (PDF Downloads): T039–T049 ← **MVP core**
3. **User Story 3** (LLM Output): T050–T057 ← **MVP core**
4. **User Story 4** (FastAPI): T058–T066 ← **Post-MVP**

### Blocking Dependencies

- Phase 1 (Setup) blocks all other phases
- Phase 2 (Foundational) blocks all user stories
- User Stories 1–3 can be parallelized after Phase 2
- User Story 4 depends on User Stories 1–3 (uses same scraper)

### Parallelization Opportunities

**After Phase 1 completes**, Phase 2 tasks can be parallelized:
- Models (T010–T016) in parallel with Config (T017–T019) and Logging (T022–T025)

**After Phase 2 completes**, user stories can be parallelized:
- US1 Document Discovery (T026–T038) in parallel with US2 PDF Downloads (T039–T049)
- Both can run while US3 (T050–T057) develops
- US4 (T058–T066) starts after US1–3 complete

**CLI & Polish (Phase 7)** can partially overlap with US4:
- T067–T072 (CLI) can start as soon as core crawler (US1–3) is testable

### Estimated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 1 | 0.5 day | Sequential setup |
| Phase 2 | 1 day | Mostly parallelizable |
| Phase 3 (US1) | 1.5 days | Core scraping logic |
| Phase 4 (US2) | 1.5 days | Can overlap with US1 (parallel after Phase 2) |
| Phase 5 (US3) | 0.5 day | Validation; overlaps with US2 |
| Phase 6 (US4) | 1 day | Depends on US1–3 complete |
| Phase 7 | 1.5 days | Testing, docs, deployment |
| **TOTAL (Sequential)** | **~8 days** | If strictly sequential |
| **TOTAL (Parallelized)** | **~5–6 days** | With parallel story execution |

---

## Independent Test Criteria per User Story

### User Story 1 Test Criteria
- ✅ Crawler discovers ≥5 documents from mocked MAS website
- ✅ All documents have required fields (title, category, source_url, etc.)
- ✅ Only documents within 90-day window included
- ✅ Documents from all 3 sections (News, Circulars, Regulation) present
- ✅ Logs show fetch attempts and any parse errors

### User Story 2 Test Criteria
- ✅ PDFs downloaded to specified directory with valid filenames
- ✅ Downloaded file count ≥90% of available PDF links
- ✅ Each document has downloaded_pdf_path and file_hash populated (if successful)
- ✅ Retry logic triggered and logged for simulated failures
- ✅ Crawler continues after download errors (no crash)

### User Story 3 Test Criteria
- ✅ JSON output parses without errors
- ✅ All dates are ISO-8601 format
- ✅ All URLs are valid (HttpUrl validation passes)
- ✅ All categories are one of: News, Circular, Regulation
- ✅ LLM can parse JSON without data transformation (mock test)

### User Story 4 Test Criteria
- ✅ FastAPI app imports crawler successfully
- ✅ POST /api/v1/crawl endpoint returns HTTP 200 with CrawlResult JSON
- ✅ Accepts optional parameters (days_back, include_pdfs, etc.)
- ✅ Returns HTTP 400 for invalid parameters
- ✅ Returns HTTP 500 for internal errors (gracefully)

---

## MVP Scope

**Minimum Viable Product = Phases 1–5** (User Stories 1–3)

Delivers:
- ✅ Document discovery from MAS website
- ✅ PDF download with retry logic
- ✅ Structured JSON output for LLM processing
- ✅ Full test coverage for core functionality
- ✅ Error logging and graceful degradation

**Does NOT include** (Post-MVP):
- ❌ FastAPI endpoint (User Story 4)
- ❌ Docker packaging
- ❌ Prometheus metrics
- ❌ Multi-session persistence
- ❌ Async crawling

---

## Success Criteria Mapping

Each task contributes to one or more success criteria:

| Success Criterion | Related Tasks |
|-------------------|---------------|
| SC-001: ≥10 docs in 90 days | T027–T033, T037–T038 |
| SC-002: Fields present/null | T014–T016, T034, T036, T050–T053 |
| SC-003: 90% PDF download rate | T040–T045, T049, T079 |
| SC-004: Zero duplicates on re-run | T034, T042, T046, T049 |
| SC-005: <5 minute crawl | T027, T040, T046, T079 |
| SC-006: LLM-parseable JSON | T050–T057 |
| SC-007: Comprehensive error logs | T022–T025, T036, T046, T075 |
| SC-008: Graceful degradation | T036, T045, T048–T049 |

---

## Next Steps

1. **Start Phase 1**: Create project structure (T001–T009)
2. **Proceed to Phase 2**: Implement models, config, logging (T010–T025)
3. **Parallelize User Stories**: Once Phase 2 completes, develop US1–US3 in parallel
4. **Integrate & Test**: Use integration tests to validate stories work together
5. **Post-MVP**: Add FastAPI, Docker, and deployment (Phase 6–7)

---

**Ready to implement!** Each task is specific and actionable. Begin with Phase 1 setup.
