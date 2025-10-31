# Data Model: MAS AML/CFT Document Crawler

**Date**: 2025-11-01 | **Feature**: feat-mas-data-collection | **Phase**: 1 (Design)

---

## Overview

This document defines the data model for the MAS crawler, including entity definitions, field specifications, validation rules, and relationships. All models will be implemented in Python using Pydantic v2 for type safety and automatic JSON schema generation.

---

## Core Entities

### 1. Category (Enum)

Represents the source section of a document on MAS website.

```python
from enum import Enum

class Category(str, Enum):
    """Document source category."""
    NEWS = "News"
    CIRCULAR = "Circular"
    REGULATION = "Regulation"
```

**Field Details**:
- **Type**: Enum (restricted to 3 values)
- **Validation**: Must be one of NEWS, CIRCULAR, REGULATION
- **Default**: No default; required for every document
- **JSON Serialization**: String value (e.g., `"News"`)

---

### 2. Document

Represents a single AML/CFT-related announcement or guidance document from MAS.

```python
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional

class Document(BaseModel):
    """Single MAS AML/CFT document metadata."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title as displayed on MAS website"
    )

    publication_date: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 publication date (UTC). None if not found on page."
    )

    category: Category = Field(
        ...,
        description="Source section: News, Circular, or Regulation"
    )

    source_url: HttpUrl = Field(
        ...,
        description="Direct link to document on MAS website"
    )

    normalized_url: str = Field(
        ...,
        description="Normalized source_url (query params/fragments removed) for deduplication"
    )

    downloaded_pdf_path: Optional[str] = Field(
        default=None,
        description="Local filesystem path to downloaded PDF. None if download failed or unavailable."
    )

    file_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of downloaded PDF (lowercase hex string). None if PDF not downloaded."
    )

    download_timestamp: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 timestamp when PDF was successfully downloaded (UTC). None if not downloaded."
    )

    data_quality_notes: Optional[str] = Field(
        default=None,
        description="Optional: Free-text notes on data completeness (e.g., 'publication_date not found in HTML')"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Notice on AML/CFT Requirements for Trade Finance",
            "publication_date": "2025-10-15T00:00:00Z",
            "category": "Circular",
            "source_url": "https://www.mas.gov.sg/news/media-releases/2025/notice-aml-cft-requirements",
            "normalized_url": "https://www.mas.gov.sg/news/media-releases/2025/notice-aml-cft-requirements",
            "downloaded_pdf_path": "./downloads/mas_circular_2025_10_15_aml_cft.pdf",
            "file_hash": "a1b2c3d4e5f6...",
            "download_timestamp": "2025-11-01T14:35:42.123Z",
            "data_quality_notes": None
        }
    })
```

**Field Validation Rules**:

| Field | Type | Required? | Validation | Notes |
|-------|------|-----------|-----------|-------|
| `title` | str | Yes | 1–500 chars | May be `null` if not found; trigger null in required fields list |
| `publication_date` | datetime (ISO-8601, UTC) | No | Valid ISO-8601 or `null` | If missing, set to `null`; log data quality note |
| `category` | Enum | Yes | NEWS \| CIRCULAR \| REGULATION | Derived from page section |
| `source_url` | HttpUrl | Yes | Valid URL (https only recommended) | Must be absolute; validated by Pydantic |
| `normalized_url` | str | Yes | Derived from source_url | Remove query params, fragments; lowercase domain |
| `downloaded_pdf_path` | str | No | Valid filesystem path | `null` if download not attempted or failed |
| `file_hash` | str | No | SHA-256 hex (lowercase, 64 chars) | Computed after successful PDF download |
| `download_timestamp` | datetime | No | ISO-8601, UTC | Set when PDF download completed |
| `data_quality_notes` | str | No | Free-text (optional) | Log reason for `null` fields; aids debugging |

**Relationships**:
- Belongs to a **Crawl Session** (1:many; multiple documents per crawl).
- Immutable after creation (Pydantic `frozen=True` optional for production).

**JSON Example**:
```json
{
  "title": "Guidance on Beneficial Ownership in AML Compliance",
  "publication_date": "2025-09-20T00:00:00Z",
  "category": "Regulation",
  "source_url": "https://www.mas.gov.sg/regulation/guidance/beneficial-ownership-aml",
  "normalized_url": "https://www.mas.gov.sg/regulation/guidance/beneficial-ownership-aml",
  "downloaded_pdf_path": "/tmp/downloads/mas_regulation_beneficial_ownership.pdf",
  "file_hash": "abcdef1234567890...",
  "download_timestamp": "2025-11-01T15:22:10.456Z",
  "data_quality_notes": null
}
```

---

### 3. CrawlSession

Metadata about a specific crawl run (execution context and summary statistics).

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class CrawlSession(BaseModel):
    """Metadata and summary of a single crawl execution."""

    session_id: str = Field(
        ...,
        description="Unique identifier (UUID or timestamp-based) for this crawl session"
    )

    start_time: datetime = Field(
        ...,
        description="ISO-8601 timestamp when crawl started (UTC)"
    )

    end_time: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 timestamp when crawl completed (UTC). None if in progress."
    )

    duration_seconds: Optional[float] = Field(
        default=None,
        description="Total execution time in seconds. Calculated as end_time - start_time."
    )

    documents_found: int = Field(
        default=0,
        ge=0,
        description="Total unique documents discovered on MAS website (before dedup)"
    )

    documents_downloaded: int = Field(
        default=0,
        ge=0,
        description="Number of PDFs successfully downloaded"
    )

    documents_skipped: int = Field(
        default=0,
        ge=0,
        description="Documents skipped (duplicates, robots.txt, missing fields, etc.)"
    )

    errors_encountered: int = Field(
        default=0,
        ge=0,
        description="Count of non-fatal errors (retries, missing fields, broken links)"
    )

    errors_details: List[str] = Field(
        default_factory=list,
        description="Log entries for errors (up to 100 most recent; summary of issues)"
    )

    success: bool = Field(
        default=False,
        description="True if crawl completed without fatal errors; False if halted early"
    )

    crawl_config: dict = Field(
        default_factory=dict,
        description="Configuration used for crawl (days_back, download_dir, retry_policy, etc.)"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "crawl_20251101_143542",
            "start_time": "2025-11-01T14:35:42.000Z",
            "end_time": "2025-11-01T14:38:15.500Z",
            "duration_seconds": 153.5,
            "documents_found": 28,
            "documents_downloaded": 25,
            "documents_skipped": 3,
            "errors_encountered": 2,
            "errors_details": [
                "HTTP 404 for Regulation page (URL unavailable)",
                "PDF download timeout for document X (retried 3x, marked failed)"
            ],
            "success": True,
            "crawl_config": {
                "days_back": 90,
                "include_pdfs": True,
                "download_dir": "/tmp/downloads",
                "max_pdf_size_mb": 50
            }
        }
    })
```

**Field Validation Rules**:

| Field | Type | Required? | Validation | Notes |
|-------|------|-----------|-----------|-------|
| `session_id` | str | Yes | Unique UUID or timestamp | Generated by crawler; immutable |
| `start_time` | datetime | Yes | ISO-8601, UTC | Set at crawl start |
| `end_time` | datetime | No | ISO-8601, UTC | Set when crawl completes; `null` if in-progress |
| `duration_seconds` | float | No | >= 0 | Calculated post-crawl |
| `documents_found` | int | Yes | >= 0 | Total discovered (before dedup/filter) |
| `documents_downloaded` | int | Yes | >= 0 | PDF download successes |
| `documents_skipped` | int | Yes | >= 0 | Duplicates, errors, filtered by date |
| `errors_encountered` | int | Yes | >= 0 | Non-fatal error count |
| `errors_details` | List[str] | Yes (array) | List of error log entries | Last 100 errors; free-text summaries |
| `success` | bool | Yes | True \| False | Success = completed without fatal crash |
| `crawl_config` | dict | Yes | Key-value pairs | Configuration snapshot |

**Relationships**:
- Contains **multiple Documents** (1:many; one crawl produces multiple document records).
- Metadata only; not persisted separately (included in output JSON alongside documents).

**JSON Example**:
```json
{
  "session_id": "crawl_20251101_143542",
  "start_time": "2025-11-01T14:35:42.000Z",
  "end_time": "2025-11-01T14:38:15.500Z",
  "duration_seconds": 153.5,
  "documents_found": 28,
  "documents_downloaded": 25,
  "documents_skipped": 3,
  "errors_encountered": 2,
  "errors_details": [
    "HTTP 404: Regulation page unavailable",
    "PDF timeout: max retries exceeded for document ID X"
  ],
  "success": true,
  "crawl_config": {
    "days_back": 90,
    "download_dir": "./downloads",
    "max_retries": 3,
    "backoff_strategy": "exponential"
  }
}
```

---

## Composite Output: CrawlResult

The primary JSON output returned by the crawler, combining session metadata and all documents.

```python
from pydantic import BaseModel, Field
from typing import List

class CrawlResult(BaseModel):
    """Complete output of a crawl session: metadata + documents."""

    session: CrawlSession = Field(
        ...,
        description="Crawl execution metadata and summary statistics"
    )

    documents: List[Document] = Field(
        default_factory=list,
        description="Array of documents discovered and processed in this crawl"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": { /* CrawlSession example */ },
                "documents": [ /* array of Document examples */ ]
            }
        }
    )
```

**JSON Structure**:
```json
{
  "session": {
    "session_id": "crawl_20251101_143542",
    "start_time": "2025-11-01T14:35:42.000Z",
    "end_time": "2025-11-01T14:38:15.500Z",
    "duration_seconds": 153.5,
    "documents_found": 28,
    "documents_downloaded": 25,
    "documents_skipped": 3,
    "errors_encountered": 2,
    "errors_details": [
      "HTTP 404: Regulation page unavailable",
      "PDF timeout: retries exhausted"
    ],
    "success": true,
    "crawl_config": { /* config snapshot */ }
  },
  "documents": [
    { /* Document 1 */ },
    { /* Document 2 */ },
    /* ... */
  ]
}
```

---

## Validation & Constraints

### Pydantic Configuration (Shared)

```python
from pydantic import ConfigDict

class BaseModel(BaseModel):
    model_config = ConfigDict(
        json_schema_extra=...,
        str_strip_whitespace=True,        # Trim leading/trailing whitespace from strings
        validate_default=True,             # Validate default values
        arbitrary_types_allowed=False,     # No non-Pydantic types without custom serializers
        use_enum_values=True               # Serialize enums as their string values, not names
    )
```

### Custom Validators (Pseudo-code)

```python
from pydantic import field_validator, model_validator

class Document(BaseModel):
    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("source_url")
    @classmethod
    def url_https_recommended(cls, v):
        # Warn if not HTTPS (log warning, don't fail validation)
        if not str(v).startswith("https://"):
            # Log warning to crawler logger
            pass
        return v

    @field_validator("normalized_url")
    @classmethod
    def normalized_url_lowercase(cls, v):
        return v.lower()

    @field_validator("file_hash")
    @classmethod
    def hash_format(cls, v):
        if v is not None:
            # SHA-256 = 64 hex characters
            if not (len(v) == 64 and all(c in "0123456789abcdef" for c in v)):
                raise ValueError("file_hash must be 64-character lowercase hex string (SHA-256)")
        return v

    @model_validator(mode='after')
    def downloaded_path_requires_hash(self):
        # If PDF was downloaded, hash must be present
        if self.downloaded_pdf_path is not None and self.file_hash is None:
            raise ValueError("file_hash must be set if downloaded_pdf_path is not null")
        return self
```

---

## Storage & Serialization

### Output Format

- **Default**: JSON (Pydantic `model_dump_json()` with pretty-printing).
- **File Encoding**: UTF-8.
- **Date Format**: ISO-8601 (e.g., `2025-11-01T14:35:42.123Z`).
- **File Naming**: `mas_crawl_<session_id>.json` or `mas_crawl_<timestamp>.json`.

### Example File Write

```python
# After crawl completes:
result = CrawlResult(session=session, documents=documents)

# Write to file
output_path = f"./mas_crawl_{session.session_id}.json"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(result.model_dump_json(indent=2))

# Or: return for API response
return result.model_dump(mode='json')  # Pydantic v2 serialization
```

### Optional: Persistent Deduplication Store

If maintaining crawl history across sessions, persist `Document` records:

```python
# Pseudo-code: Optional SQLite or JSON-file store for deduplication
class DeduplicationStore:
    def save_documents(self, documents: List[Document]):
        """Persist document metadata for future dedup checks."""
        # Store (normalized_url, file_hash) tuples
        pass

    def is_duplicate(self, normalized_url: str, file_hash: str) -> bool:
        """Check if document already seen."""
        pass
```

(Out of scope for Phase 1; optional for Phase 2+)

---

## Data Quality & Missing Fields

### Handling Missing Fields

**Philosophy**: Return documents with `null` fields; don't silently drop incomplete data.

| Field | If Missing | Behavior |
|-------|-----------|----------|
| `title` | Not found in HTML | Set to `null`; log data quality note; include in results |
| `publication_date` | Not found in HTML | Set to `null`; log data quality note |
| `downloaded_pdf_path` | PDF download fails | Set to `null`; log error; continue |
| `file_hash` | PDF not downloaded | Set to `null` automatically |
| `download_timestamp` | PDF not downloaded | Set to `null` automatically |

### Data Quality Notes Example

```json
{
  "title": "Circular on AML/CFT",
  "publication_date": null,
  "data_quality_notes": "publication_date not found in HTML; check manually or contact MAS"
}
```

---

## API Contract (JSON Schema)

Pydantic v2 auto-generates OpenAPI-compatible JSON schema:

```python
from pydantic.json_schema import model_json_schema

# Generate schema for API documentation
schema = model_json_schema(CrawlResult)
# Output to contracts/openapi.yaml (see Phase 1 deliverables)
```

**Schema includes**:
- All field definitions with types and constraints.
- Required vs. optional field markers.
- Min/max length, enum values, format constraints.
- Field descriptions (from Pydantic `Field(description=...)`).

---

## Testing & Validation

### Unit Tests for Models

```python
# tests/unit/test_models.py
import pytest
from mas_crawler.models import Document, Category

def test_document_valid():
    """Valid document passes validation."""
    doc = Document(
        title="Test Circular",
        publication_date="2025-10-15T00:00:00Z",
        category=Category.CIRCULAR,
        source_url="https://www.mas.gov.sg/news/test",
        normalized_url="https://www.mas.gov.sg/news/test",
        downloaded_pdf_path="/tmp/test.pdf",
        file_hash="a" * 64
    )
    assert doc.title == "Test Circular"

def test_document_title_required():
    """Document without title raises validation error."""
    with pytest.raises(ValueError):
        Document(
            title="",  # Empty; should fail
            publication_date="2025-10-15T00:00:00Z",
            category=Category.CIRCULAR,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test"
        )

def test_document_hash_format():
    """Invalid SHA-256 hash format raises error."""
    with pytest.raises(ValueError):
        Document(
            title="Test",
            category=Category.CIRCULAR,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
            downloaded_pdf_path="/tmp/test.pdf",
            file_hash="invalid_hash"  # Not 64 hex chars
        )

def test_document_json_serialization():
    """Document serializes to valid JSON."""
    doc = Document(...)
    json_str = doc.model_dump_json()
    assert isinstance(json_str, str)
    # Deserialize to verify round-trip
    doc2 = Document.model_validate_json(json_str)
    assert doc == doc2
```

---

## Summary

The data model is designed for:
1. **Compliance Audit**: Comprehensive tracking of all decisions, timestamps, errors.
2. **LLM Parsing**: Consistent field names, data types, and JSON structure.
3. **Robustness**: Explicit `null` handling; no silent data loss.
4. **Testability**: Pydantic validation enables deterministic schema testing.
5. **Reusability**: Models can be imported and used in FastAPI, CLI, batch jobs.

All fields are documented, validated, and serializable to JSON suitable for downstream consumption.
