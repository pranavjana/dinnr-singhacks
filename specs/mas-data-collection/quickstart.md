# Quick Start Guide: MAS AML/CFT Document Crawler

**Date**: 2025-11-01 | **Feature**: feat-mas-data-collection | **Phase**: 1 (Design)

---

## Installation

### Prerequisites

- Python 3.11 or later
- pip or poetry for dependency management
- Local filesystem with 500MB+ free space (for PDF storage)
- Internet connectivity (for MAS website access)

### Setup Steps

```bash
# Clone repository (adjust path as needed)
cd /path/to/dinnr-singhacks

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import mas_crawler; print(mas_crawler.__version__)"
```

### requirements.txt

```
requests==2.31.0
beautifulsoup4==4.12.2
pydantic==2.5.0
python-dateutil==2.8.2
pytest==7.4.3
pytest-cov==4.1.0
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# .env
MAS_DOWNLOAD_DIR=./downloads          # Local directory for PDF storage
MAS_REQUEST_TIMEOUT=30                # Timeout per HTTP request (seconds)
MAS_PDF_TIMEOUT=60                    # Timeout per PDF download (seconds)
MAS_MAX_PDF_SIZE_MB=50                # Skip PDFs larger than this (MB)
MAS_RETRY_MAX_ATTEMPTS=3              # Max retry attempts
MAS_USER_AGENT=Mozilla/5.0 (compatible; MASAMLCrawler/1.0; +https://yourorg/crawler-policy)
MAS_LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

### Configuration in Code

```python
from mas_crawler.config import Config

config = Config.from_env()
print(config.download_dir)
print(config.max_pdf_size_mb)
```

---

## Basic Usage

### CLI: Run a Crawl

```bash
# Basic crawl (90-day window by default)
python -m mas_crawler.cli crawl

# Custom options
python -m mas_crawler.cli crawl \
  --days-back 180 \
  --download-dir /custom/path \
  --include-pdfs \
  --output-file ./mas_results.json

# View output
cat mas_results.json | jq '.session'
cat mas_results.json | jq '.documents[0]'
```

### Python: Programmatic Usage

```python
from mas_crawler.scraper import MASCrawler
from mas_crawler.config import Config
import json

# Initialize crawler
config = Config(
    download_dir="./downloads",
    days_back=90,
    include_pdfs=True
)
crawler = MASCrawler(config=config)

# Run crawl
result = crawler.crawl()

# Inspect results
print(f"Found {result.session.documents_found} documents")
print(f"Downloaded {result.session.documents_downloaded} PDFs")
print(f"Success: {result.session.success}")

# Save to file
with open("crawl_results.json", "w") as f:
    f.write(result.model_dump_json(indent=2))

# Inspect individual documents
for doc in result.documents:
    print(f"- {doc.title} ({doc.publication_date}) -> {doc.downloaded_pdf_path}")
```

---

## Output Format

### JSON Schema

The crawler outputs a JSON file with the following structure:

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
      "PDF timeout: max retries exceeded"
    ],
    "success": true,
    "crawl_config": {
      "days_back": 90,
      "include_pdfs": true,
      "download_dir": "./downloads",
      "max_pdf_size_mb": 50
    }
  },
  "documents": [
    {
      "title": "Notice on AML/CFT Requirements for Trade Finance",
      "publication_date": "2025-10-15T00:00:00Z",
      "category": "Circular",
      "source_url": "https://www.mas.gov.sg/news/media-releases/2025/notice-aml-cft",
      "normalized_url": "https://www.mas.gov.sg/news/media-releases/2025/notice-aml-cft",
      "downloaded_pdf_path": "./downloads/mas_circular_2025_10_15_aml_cft.pdf",
      "file_hash": "abcdef1234567890...",
      "download_timestamp": "2025-11-01T14:35:50.456Z",
      "data_quality_notes": null
    },
    {
      "title": "Guidance on Beneficial Ownership in AML Compliance",
      "publication_date": null,
      "category": "Regulation",
      "source_url": "https://www.mas.gov.sg/regulation/guidance/beneficial-ownership",
      "normalized_url": "https://www.mas.gov.sg/regulation/guidance/beneficial-ownership",
      "downloaded_pdf_path": null,
      "file_hash": null,
      "download_timestamp": null,
      "data_quality_notes": "PDF link broken; marked as failed after 3 retry attempts"
    }
  ]
}
```

### Parsing Results in Python

```python
import json

with open("mas_crawl_results.json") as f:
    result = json.load(f)

# Summary
session = result["session"]
print(f"Duration: {session['duration_seconds']}s")
print(f"Success: {session['success']}")
print(f"Downloaded: {session['documents_downloaded']} / {session['documents_found']}")

# Find documents with missing fields
incomplete = [
    doc for doc in result["documents"]
    if doc["publication_date"] is None or doc["downloaded_pdf_path"] is None
]
print(f"Incomplete documents: {len(incomplete)}")

# Export PDF paths for batch processing
pdf_paths = [doc["downloaded_pdf_path"] for doc in result["documents"] if doc["downloaded_pdf_path"]]
for path in pdf_paths:
    print(f"PDF: {path}")
```

---

## Logging

### Log Output

Logs are written to stdout by default (configurable to file).

```
2025-11-01T14:35:42.000Z [INFO] Starting crawl session: crawl_20251101_143542
2025-11-01T14:35:43.100Z [INFO] Fetching News page: https://www.mas.gov.sg/news
2025-11-01T14:35:44.200Z [INFO] Found 12 documents in News section
2025-11-01T14:35:44.300Z [INFO] Fetching Circulars page: https://www.mas.gov.sg/regulation/circulars
2025-11-01T14:35:45.500Z [INFO] Found 10 documents in Circulars section
2025-11-01T14:35:45.600Z [WARNING] HTTP 404 for Regulation page; skipping
2025-11-01T14:35:45.700Z [INFO] Starting PDF downloads (25 documents)
2025-11-01T14:35:46.000Z [INFO] Downloading: mas_circular_aml_cft.pdf
2025-11-01T14:35:47.100Z [INFO] Downloaded successfully; SHA-256: abcdef123...
2025-11-01T14:35:48.200Z [WARNING] PDF timeout for doc X; retrying (attempt 1/3)
2025-11-01T14:35:49.300Z [WARNING] PDF timeout again; retrying (attempt 2/3)
2025-11-01T14:35:50.400Z [ERROR] PDF timeout (attempt 3/3 failed); marked as failed
2025-11-01T14:38:15.500Z [INFO] Crawl completed: 28 found, 25 downloaded, 3 skipped, 2 errors
```

### Configuring Logging

```python
from mas_crawler.logger import setup_logging

# Log to file
setup_logging(log_file="crawl.log", level="DEBUG")

# Or: environment variable
import os
os.environ["MAS_LOG_LEVEL"] = "DEBUG"
```

---

## Common Tasks

### Task: Re-run Crawl with Deduplication

```python
from mas_crawler.deduplicator import Deduplicator
from mas_crawler.scraper import MASCrawler
import json

# Load previous results
with open("previous_crawl.json") as f:
    previous = json.load(f)

# Initialize deduplicator with previous documents
dedup = Deduplicator()
for doc in previous["documents"]:
    dedup.add_document(
        normalized_url=doc["normalized_url"],
        file_hash=doc["file_hash"]
    )

# Run new crawl
crawler = MASCrawler(deduplicator=dedup)
result = crawler.crawl()

# Result will skip documents already seen
print(f"New documents: {len(result.documents)}")
```

### Task: Filter Documents by Category

```python
import json

with open("mas_crawl_results.json") as f:
    result = json.load(f)

# Filter by category
circulars = [doc for doc in result["documents"] if doc["category"] == "Circular"]
print(f"Found {len(circulars)} circulars")

# Filter by date
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=30)
recent = [
    doc for doc in result["documents"]
    if doc["publication_date"] and datetime.fromisoformat(doc["publication_date"]) > cutoff
]
print(f"Found {len(recent)} documents in last 30 days")
```

### Task: Generate Report for Compliance Team

```python
import json
from datetime import datetime

with open("mas_crawl_results.json") as f:
    result = json.load(f)

session = result["session"]
print("=== MAS AML/CFT Document Crawl Report ===")
print(f"Date: {session['start_time']}")
print(f"Duration: {session['duration_seconds']} seconds")
print(f"Status: {'SUCCESS' if session['success'] else 'FAILED'}")
print()
print("Summary:")
print(f"  Documents found: {session['documents_found']}")
print(f"  PDFs downloaded: {session['documents_downloaded']}")
print(f"  Skipped/errors: {session['documents_skipped'] + session['errors_encountered']}")
print()
print("Documents:")
for doc in result["documents"]:
    status = "✓" if doc["downloaded_pdf_path"] else "✗"
    print(f"  {status} {doc['title']} ({doc['category']})")
    if doc["publication_date"]:
        print(f"     Date: {doc['publication_date']}")
    if doc["data_quality_notes"]:
        print(f"     Note: {doc['data_quality_notes']}")
```

---

## Troubleshooting

### Issue: "HTTP 404: MAS website page not found"

**Cause**: MAS website structure may have changed; CSS selectors no longer valid.

**Solution**:
1. Manually visit https://www.mas.gov.sg/news to verify page structure.
2. Update CSS selectors in `scraper.py`.
3. Re-run crawl.

### Issue: "PDF download timeout after 3 retries"

**Cause**: PDF file is very large or network is slow.

**Solution**:
1. Increase `MAS_PDF_TIMEOUT` to 120+ seconds.
2. Decrease `MAS_MAX_PDF_SIZE_MB` to skip large files.
3. Check network connectivity.
4. Manually download and place in `downloads/` directory if critical.

### Issue: "No documents found (empty results)"

**Cause**: Crawl ran but discovered no documents matching criteria.

**Possibilities**:
1. MAS website is down or structure changed.
2. All documents are older than 90-day window.
3. Network/robots.txt blocking the crawler.

**Debug**:
1. Check logs for HTTP errors.
2. Manually visit https://www.mas.gov.sg/news.
3. Verify robots.txt allows crawling: https://www.mas.gov.sg/robots.txt.
4. Temporarily reduce `--days-back` to 365 and re-run.

### Issue: "Pydantic validation error on JSON output"

**Cause**: Document data doesn't match schema (type mismatch, invalid format).

**Solution**:
1. Check `data_quality_notes` field for hints.
2. Enable `DEBUG` logging to see full validation error.
3. Check if date parsing failed; ensure ISO-8601 format.

---

## Next Steps

1. **Review Generated Files**: Check `downloads/` directory for PDFs.
2. **Validate JSON**: Use `jq` or Python to inspect output structure.
3. **Integrate with FastAPI** (Phase 2): Wrap `MASCrawler.crawl()` in FastAPI endpoint.
4. **Schedule Runs**: Use cron, Celery, or Airflow to trigger crawls on schedule.
5. **Feed to LLM**: Pass JSON output to downstream compliance rule extraction agent.

---

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_scraper.py -v

# Generate coverage report
pytest tests/ --cov=mas_crawler --cov-report=html
# View report: open htmlcov/index.html
```

### Run Integration Tests

```bash
# Integration tests (with mocked MAS responses)
pytest tests/integration/ -v

# Include slow tests (if any)
pytest tests/ -v -m "slow"
```

---

## Documentation

- **[data-model.md](./data-model.md)**: Entity definitions and validation rules.
- **[research.md](./research.md)**: Design decisions and rationale.
- **[api_contract.md](./contracts/openapi.yaml)**: OpenAPI schema (Phase 2).
