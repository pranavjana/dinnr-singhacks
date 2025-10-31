# API Contract

The OpenAPI specification for the FastAPI endpoint is available at:

`specs/feat-mas-data-collection/contracts/openapi.yaml`

## Endpoints

### POST /api/v1/crawl

Trigger a MAS document crawl.

**Request Parameters:**
- `days_back` (int, default: 90): Number of days to look back for documents
- `include_pdfs` (bool, default: true): Whether to download PDFs
- `download_dir` (string, default: "./downloads"): Directory for PDF storage
- `max_pdf_size_mb` (int, default: 50): Maximum PDF size in MB

**Response:** CrawlResult JSON

See [data-model.md](../specs/feat-mas-data-collection/data-model.md) for full schema.
