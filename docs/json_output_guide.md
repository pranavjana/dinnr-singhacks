# JSON Output Structure Guide

**MAS AML/CFT Document Crawler - Version 0.1.0**
**Last Updated**: 2025-11-01

---

## Overview

This guide documents the JSON output structure produced by the MAS crawler. The output is designed for downstream LLM processing with consistent field naming, explicit null handling, and comprehensive metadata.

## Quick Reference

### Output Structure

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
    "errors_details": ["Error 1", "Error 2"],
    "success": true,
    "crawl_config": { "days_back": 90 }
  },
  "documents": [
    {
      "title": "Notice on AML/CFT Requirements",
      "publication_date": "2025-10-15T00:00:00Z",
      "category": "Circular",
      "source_url": "https://www.mas.gov.sg/news/...",
      "normalized_url": "https://www.mas.gov.sg/news/...",
      "downloaded_pdf_path": "./downloads/circular_001.pdf",
      "file_hash": "a1b2c3d4...",
      "download_timestamp": "2025-11-01T14:35:50.456Z",
      "data_quality_notes": null
    }
  ]
}
```

## Field Specifications

### Session Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | ✓ | Unique crawl identifier |
| `start_time` | string (ISO-8601) | ✓ | Crawl start time (UTC) |
| `end_time` | string (ISO-8601) | - | Crawl end time (UTC) |
| `duration_seconds` | number | - | Total execution time |
| `documents_found` | integer | ✓ | Total documents discovered |
| `documents_downloaded` | integer | ✓ | PDFs successfully downloaded |
| `documents_skipped` | integer | ✓ | Documents skipped/filtered |
| `errors_encountered` | integer | ✓ | Non-fatal error count |
| `errors_details` | array | ✓ | Error log entries |
| `success` | boolean | ✓ | Crawl completion status |
| `crawl_config` | object | ✓ | Configuration snapshot |

### Document Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string (1-500) | ✓ | Document title |
| `publication_date` | string (ISO-8601) | - | Publication date (UTC) |
| `category` | enum | ✓ | "News", "Circular", or "Regulation" |
| `source_url` | string (URL) | ✓ | Original document URL |
| `normalized_url` | string | ✓ | Deduplicated URL |
| `downloaded_pdf_path` | string | - | Local PDF file path |
| `file_hash` | string (64 hex) | - | SHA-256 hash of PDF |
| `download_timestamp` | string (ISO-8601) | - | PDF download time |
| `data_quality_notes` | string | - | Data completeness notes |

## Data Type Reference

### String (ISO-8601)
UTC timestamps with 'Z' suffix:
```json
"2025-11-01T14:35:42.123Z"
```

### String (URL)
Fully qualified HTTP/HTTPS URLs:
```json
"https://www.mas.gov.sg/news/circular-001"
```

### String (SHA-256 Hash)
64-character lowercase hexadecimal:
```json
"a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
```

### Enum (Category)
One of three predefined values:
```json
"News" | "Circular" | "Regulation"
```

## Null Handling

The crawler uses **explicit nulls** for missing data:

```json
{
  "publication_date": null,
  "data_quality_notes": "publication_date not found on page"
}
```

**Never omitted** - all fields always present, even if null.

## Usage Examples

### Python - Load and Parse

```python
import json

with open("crawl_result.json") as f:
    result = json.load(f)

# Access session metadata
print(f"Found {result['session']['documents_found']} documents")
print(f"Downloaded {result['session']['documents_downloaded']} PDFs")

# Iterate documents
for doc in result["documents"]:
    if doc["downloaded_pdf_path"]:
        print(f"✓ {doc['title']} - {doc['downloaded_pdf_path']}")
    else:
        print(f"✗ {doc['title']} - {doc['data_quality_notes']}")
```

### Python - Filter by Category

```python
# Get only Circulars with PDFs
circulars = [
    doc for doc in result["documents"]
    if doc["category"] == "Circular"
    and doc["downloaded_pdf_path"] is not None
]
```

### Python - Validate Schema

```python
from mas_crawler.models import CrawlResult

# Load and validate
with open("result.json") as f:
    json_str = f.read()

validated = CrawlResult.model_validate_json(json_str)
print(f"Valid: {validated.validate_schema()}")
```

## LLM Compatibility

### Self-Describing Structure

Field names clearly indicate content:
- `documents_found` (not just `found`)
- `publication_date` (not just `date`)
- `downloaded_pdf_path` (not just `path`)

### No Transformation Required

LLMs can parse directly without preprocessing:

```python
# LLM prompt
prompt = f"""
Analyze these MAS regulatory documents:

{json.dumps(result, indent=2)}

Extract key AML/CFT compliance requirements.
"""
```

### Data Quality Indicators

LLMs can identify incomplete data via:
1. Explicit `null` values
2. `data_quality_notes` explanations
3. `errors_details` array

## Validation

### Pydantic Schema Validation

```python
from mas_crawler.models import CrawlResult

# Will raise ValidationError if invalid
result = CrawlResult.model_validate_json(json_string)
```

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `title cannot be empty` | Missing title | Check HTML parsing |
| `file_hash must be 64-char hex` | Invalid hash | Use SHA-256 lowercase |
| `downloaded_pdf_path requires file_hash` | Missing hash | Compute hash after download |
| `Invalid ISO-8601 date` | Wrong date format | Use `datetime.isoformat()` |

## Generated Artifacts

### JSON Schema
Full JSON Schema specification:
```bash
cat docs/json_schema.json
```

### Examples
Sample JSON output:
```bash
cat docs/json_examples.json
```

### Generate Schema
Regenerate schema from Pydantic models:
```bash
PYTHONPATH=src python3 src/mas_crawler/generate_schema.py
```

## Related Documentation

- **Data Model**: `specs/feat-mas-data-collection/data-model.md`
- **API Contract**: `specs/feat-mas-data-collection/contracts/openapi.yaml`
- **Quickstart**: `specs/feat-mas-data-collection/quickstart.md`
- **Source Code**: `src/mas_crawler/models.py`
