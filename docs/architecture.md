# Architecture Documentation

## Module Responsibilities

### Core Modules

- **models.py**: Pydantic data models for validation and serialization
- **config.py**: Configuration management from environment variables
- **errors.py**: Custom exception classes for error handling
- **logger.py**: Structured JSON logging for audit trails

### Scraping Modules

- **scraper.py**: Main crawler logic for MAS website
- **pdf_downloader.py**: PDF download with retry and validation
- **deduplicator.py**: Duplicate detection logic

### Interface Modules

- **cli.py**: Command-line interface
- **api.py**: FastAPI endpoint wrapper (Phase 6)

## Data Flow

1. Configuration loaded from environment variables
2. Crawler fetches MAS pages (News, Circulars, Regulation)
3. Parser extracts document metadata
4. Deduplicator filters duplicates
5. PDF downloader retrieves files with retry logic
6. Results serialized to JSON via Pydantic models
7. Logs written for audit trail

## Error Handling Strategy

All errors are logged but don't halt the crawl process. Retry logic with exponential backoff (1s, 2s, 4s) is applied to transient failures.

## Design Patterns

- **Dependency Injection**: Configuration passed to modules
- **Separation of Concerns**: Each module has single responsibility
- **Graceful Degradation**: Continue on individual failures
