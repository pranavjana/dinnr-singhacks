# MAS AML/CFT Document Crawler

A Python library for collecting AML/CFT-related documents from the Monetary Authority of Singapore (MAS) regulatory website.

## Features

- Discover documents from MAS News, Circulars, and Regulation pages
- Download and validate PDF files with retry logic
- Deduplicate documents using normalized URLs and file hashes
- Generate structured JSON output for LLM processing
- Comprehensive logging for compliance audit trails

## Installation

```bash
# Clone repository
cd /path/to/dinnr-singhacks

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

See [quickstart.md](../specs/feat-mas-data-collection/quickstart.md) for detailed usage instructions.

## Documentation

- [Architecture](./architecture.md) - System design and module responsibilities
- [API Contract](./api_contract.md) - OpenAPI schema for FastAPI endpoint

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=mas_crawler --cov-report=html
```

## License

MIT License
