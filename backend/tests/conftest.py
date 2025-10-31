"""Pytest configuration and shared fixtures for MAS crawler tests."""

import pytest
from datetime import datetime
from mas_crawler.models import Category, Document, CrawlSession


@pytest.fixture
def sample_document():
    """Sample valid document for testing."""
    return Document(
        title="Test AML/CFT Circular",
        publication_date=datetime(2025, 10, 15),
        category=Category.CIRCULAR,
        source_url="https://www.mas.gov.sg/news/test-circular",
        normalized_url="https://www.mas.gov.sg/news/test-circular",
    )


@pytest.fixture
def sample_document_with_pdf():
    """Sample document with PDF download info."""
    return Document(
        title="Test Regulation",
        publication_date=datetime(2025, 10, 1),
        category=Category.REGULATION,
        source_url="https://www.mas.gov.sg/regulation/test",
        normalized_url="https://www.mas.gov.sg/regulation/test",
        downloaded_pdf_path="/tmp/test.pdf",
        file_hash="a" * 64,  # Valid SHA-256 format
        download_timestamp=datetime(2025, 11, 1, 14, 30, 0),
    )


@pytest.fixture
def sample_crawl_session():
    """Sample crawl session for testing."""
    return CrawlSession(
        session_id="test_session_001",
        start_time=datetime(2025, 11, 1, 14, 0, 0),
        end_time=datetime(2025, 11, 1, 14, 5, 0),
        duration_seconds=300.0,
        documents_found=10,
        documents_downloaded=8,
        documents_skipped=2,
        errors_encountered=1,
        errors_details=["PDF timeout for document X"],
        success=True,
        crawl_config={"days_back": 90, "include_pdfs": True},
    )
