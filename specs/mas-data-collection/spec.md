# Feature Specification: MAS AML/CFT Document Crawler

**Feature Branch**: `feat-mas-data-collection`
**Created**: 2025-11-01
**Status**: Draft
**Input**: User description: "I'm building the data-collection feature for our AML agent. Please write a Python function (or set of functions) that scrapes the Monetary Authority of Singapore website—particularly the News, Circulars, and Regulation pages—to find and collect the most recent AML/CFT-related announcements or documents. The crawler should gather title, publication date, category, URL, and download any linked PDFs, skipping duplicates by URL. Return a clean JSON list of document metadata with local download paths. Use requests and BeautifulSoup, add simple error handling, and structure the code so it can later integrate with a FastAPI endpoint. The data output from this scraper will later be provided as structured input to an LLM, which will analyze the documents and extract actionable compliance rules, so make sure the output is well-structured, clearly labeled, and consistent to optimize LLM parsing accuracy."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Compliance Officer Collects Latest MAS Guidance (Priority: P1)

A compliance officer needs to regularly collect the latest AML/CFT guidance from the Monetary Authority of Singapore to stay informed about regulatory changes. They trigger a crawler that automatically fetches documents from MAS News, Circulars, and Regulation pages (documents published within the last 90 days), then reviews the structured metadata to identify which documents are new and relevant to their organization.

**Why this priority**: This is the core value proposition of the feature—enabling compliance teams to discover and track regulatory updates from authoritative sources. Without this capability, the entire data-collection system is meaningless.

**Independent Test**: The crawler can be tested independently by verifying it successfully retrieves and lists documents from MAS pages, and a compliance officer can review the JSON output to identify new documents without needing downstream LLM processing.

**Acceptance Scenarios**:

1. **Given** the MAS website is accessible, **When** the crawler runs, **Then** it returns a JSON list containing at least 5 recent AML/CFT documents with title, publication date, category, and URL fields populated
2. **Given** documents have been previously downloaded, **When** the crawler runs again, **Then** it skips duplicates by URL and only includes new documents in the output
3. **Given** multiple document pages exist (News, Circulars, Regulation), **When** the crawler runs, **Then** it collects documents from all specified sections

---

### User Story 2 - System Downloads and Stores Associated PDFs (Priority: P1)

The crawler needs to not only identify documents but also download any linked PDFs to a local filesystem so that the documents are available for downstream processing (LLM analysis) without requiring external API calls during analysis.

**Why this priority**: PDF downloads are essential for the LLM to analyze document content. Without local PDFs, the system cannot extract actionable compliance rules as intended.

**Independent Test**: The crawler can be tested by verifying downloaded files exist at specified paths and the JSON output contains correct local download paths corresponding to actual files.

**Acceptance Scenarios**:

1. **Given** a document has an associated PDF link, **When** the crawler runs, **Then** the PDF is downloaded to a local directory with a clear, trackable filename
2. **Given** a download fails (network error, broken link), **When** the crawler encounters this, **Then** it logs the error and continues processing other documents without crashing
3. **Given** the same PDF is encountered in a second run, **When** the crawler checks for duplicates, **Then** it reuses the existing local file instead of re-downloading

---

### User Story 3 - Structured Output Enables LLM Processing (Priority: P1)

The data-collection output must be structured and clearly labeled so that an LLM can efficiently parse the document metadata and perform compliance rule extraction. Inconsistent or poorly labeled data would cause parsing errors and wasted LLM processing.

**Why this priority**: The entire feature is designed to feed data to an LLM pipeline. If the output format is not optimized for LLM parsing, the downstream analysis will fail or be inefficient. This is a hard requirement, not optional.

**Independent Test**: The JSON output can be validated for structure consistency (all required fields present, consistent field naming, proper data types) without running the LLM—testing the data quality independently.

**Acceptance Scenarios**:

1. **Given** the crawler produces output, **When** the JSON is parsed, **Then** every document has consistent field names and data types (e.g., all dates are ISO-8601 format, all URLs are valid strings)
2. **Given** multiple documents exist, **When** the JSON is examined, **Then** the category field clearly identifies the document source (e.g., "News", "Circular", "Regulation")
3. **Given** the JSON output is provided to an LLM, **When** the LLM parses it, **Then** it can extract document metadata without requiring data transformation or cleanup

---

### User Story 4 - Integration with FastAPI Endpoint (Priority: P2)

The crawler functions are structured to be easily integrated as a FastAPI endpoint so that an automated system or web application can trigger crawls on a schedule or on-demand.

**Why this priority**: While essential for production deployment, this is lower priority than the core crawling functionality. The crawler logic can be tested standalone; integration is a secondary concern.

**Independent Test**: The functions can be wrapped in a FastAPI endpoint and tested via HTTP requests to verify they accept parameters and return results in the expected format.

**Acceptance Scenarios**:

1. **Given** a FastAPI application imports the crawler module, **When** a function is wrapped as an endpoint, **Then** the endpoint accepts optional filter parameters (e.g., category, date range) and returns JSON
2. **Given** an HTTP request is made to the endpoint, **When** the crawler executes, **Then** the endpoint returns a response with appropriate HTTP status codes and error messages

### Edge Cases

- What happens when the MAS website structure changes or pages are unavailable? The crawler should handle HTTP errors (404, 500, timeout) gracefully and report them.
- How does the system handle documents with missing fields (e.g., a document with no publication date)? The crawler MUST mark missing fields clearly (null or "unknown") rather than skipping documents, enabling downstream systems (LLM) to assess data quality per document.
- What happens when a PDF link is broken or leads to a non-PDF file? The crawler should detect this, log the issue, and continue without crashing.
- How does the system handle very large PDFs (e.g., 50+ MB)? The crawler should have configurable size limits and skip oversized files with appropriate logging.
- What happens if the local storage directory doesn't exist or is not writable? The crawler should create the directory or raise a clear error.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST crawl the Monetary Authority of Singapore website's News, Circulars, and Regulation pages to identify AML/CFT-related documents; crawler MUST respect robots.txt rules and include a descriptive user-agent header
- **FR-002**: System MUST extract and return the following metadata for each document: title, publication date, category (source section), URL, and local download path; missing required fields MUST be marked explicitly as null or "unknown" rather than excluded, enabling downstream systems to assess data completeness and quality
- **FR-003**: System MUST download any linked PDFs associated with discovered documents to a local filesystem
- **FR-004**: System MUST skip duplicate documents using a hybrid approach: normalized URL comparison (removing query parameters and fragments) for initial detection, followed by file hash validation (MD5 or SHA-256) to prevent false negatives from identical content at different URLs; system MUST avoid re-downloading previously acquired PDFs
- **FR-005**: System MUST handle HTTP errors, network timeouts, and broken links gracefully without crashing the entire crawl operation; failed downloads are retried up to 3 times with exponential backoff (1s, 2s, 4s) before being logged as permanently failed
- **FR-006**: System MUST return output as a well-structured JSON list with consistent field names, data types, and formatting
- **FR-007**: System MUST include error logging that documents any failed downloads, skipped documents, or warnings for later review
- **FR-008**: System MUST be architected as a set of Python functions that can be independently called and later wrapped as a FastAPI endpoint
- **FR-009**: System MUST validate that downloaded PDFs are actual PDF files and reject non-PDF content with appropriate logging
- **FR-010**: System MUST store metadata with enough detail (e.g., source URL, download timestamp, file hash) to enable LLM parsing and future deduplication

### Key Entities *(include if feature involves data)*

- **Document**: Represents a single AML/CFT-related announcement or guidance document from MAS, with attributes: title, publication_date, category, source_url, downloaded_pdf_path, file_hash (MD5 or SHA-256 of PDF content for deduplication), download_timestamp; normalized_url is derived from source_url for initial duplicate detection
- **Crawl Session**: Metadata about a specific crawl run, including: start_time, end_time, documents_found, documents_downloaded, documents_skipped, errors_encountered
- **Category**: One of "News", "Circular", or "Regulation" representing the source section of the document

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Crawler successfully collects and returns at least 10 AML/CFT documents published within the last 90 days from MAS website in a single run
- **SC-002**: All returned documents include title, publication date, category, and URL fields; missing required fields are explicitly marked as null or "unknown" rather than excluded, enabling downstream systems to assess data completeness
- **SC-003**: Crawler successfully downloads 90% or higher of available PDFs (excluding links that are broken or non-PDF content)
- **SC-004**: Duplicate detection by URL prevents re-downloading previously acquired documents; crawler run 2+ times returns zero duplicate entries
- **SC-005**: Crawler completes a full crawl cycle (News, Circulars, Regulation pages + PDF downloads) within 5 minutes under normal network conditions
- **SC-006**: JSON output can be parsed by a language model without data transformation; 100% of field values match expected data types and formats
- **SC-007**: Error logging captures all failed operations and is clear enough to enable troubleshooting (e.g., which links failed, why, and at what timestamp)
- **SC-008**: Crawler continues operation when encountering individual failures; no single broken link or network timeout halts the entire crawl process

## Clarifications

### Session 2025-11-01

- Q: When a PDF download fails (network error, timeout), should the crawler retry? → A: Retry up to 3 times with exponential backoff (1s, 2s, 4s delay between attempts)
- Q: Should the crawler handle authentication, respect robots.txt, and implement rate limiting? → A: No authentication needed; respect robots.txt rules and include user-agent header identifying the crawler
- Q: How should the crawler detect duplicate documents (exact URL, normalized URL, content hash)? → A: Hybrid approach: normalized URL for initial detection, then file hash (MD5/SHA-256) validation to prevent false negatives
- Q: What is the minimum acceptable data quality threshold for returned documents? → A: Pragmatic approach: return documents even with missing required fields, but mark them clearly (null or "unknown") so downstream systems know the data is incomplete
- Q: What timeframe constitutes "recent" documents for collection? → A: 90-day window; documents published in the last 90 days are considered recent (captures quarterly MAS guidance cycles)

## Assumptions

- The Monetary Authority of Singapore website uses a consistent HTML structure for the News, Circulars, and Regulation pages (if structure changes, CSS selectors may need updates but the overall architecture remains valid)
- Publication dates are always present and in a standard format (ISO-8601 or clearly parseable)
- PDF links are direct, downloadable files; no authentication is required to access documents or MAS website pages
- Local filesystem storage is available and writable; permissions are pre-configured
- Network connectivity is generally reliable; temporary timeouts are expected and should be retried
- The crawler will be run on-demand or on a regular schedule (e.g., daily), not continuously
- Failed downloads are retried up to 3 times using exponential backoff (1s, 2s, 4s) before being marked as permanently failed
- MAS website robots.txt rules will be parsed and respected to avoid crawling disallowed paths
- "Recent" documents are defined as those published within the last 90 days; older documents will be filtered out during collection

## Constraints & Scope

### In Scope

- Crawling MAS News, Circulars, and Regulation pages
- Extracting title, publication date, category, URL, and local download path
- Downloading associated PDF documents
- Duplicate prevention by URL
- Error handling and logging
- JSON output format optimized for LLM parsing
- Function design suitable for FastAPI integration

### Out of Scope

- Real-time monitoring or continuous crawling
- Advanced NLP or content analysis (that's for the LLM downstream)
- User authentication or access control for the crawler
- Multi-language support for document metadata
- Integration with external compliance databases or regulatory repositories
