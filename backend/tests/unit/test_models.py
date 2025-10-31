"""Unit tests for Pydantic data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from mas_crawler.models import Category, Document, CrawlSession, CrawlResult


class TestCategory:
    """Tests for Category enum."""

    def test_category_values(self):
        """Test that Category has correct enum values."""
        assert Category.NEWS == "News"
        assert Category.CIRCULAR == "Circular"
        assert Category.REGULATION == "Regulation"

    def test_category_membership(self):
        """Test Category enum membership."""
        assert "News" in [c.value for c in Category]
        assert "Circular" in [c.value for c in Category]
        assert "Regulation" in [c.value for c in Category]


class TestDocument:
    """Tests for Document model."""

    def test_valid_document_minimal(self):
        """Test creating a valid document with minimal required fields."""
        doc = Document(
            title="Test Document",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
        )
        assert doc.title == "Test Document"
        assert doc.category == Category.NEWS
        assert doc.publication_date is None
        assert doc.downloaded_pdf_path is None
        assert doc.file_hash is None

    def test_valid_document_with_pdf(self):
        """Test creating a document with PDF download information."""
        doc = Document(
            title="Test Circular",
            publication_date=datetime(2025, 10, 15),
            category=Category.CIRCULAR,
            source_url="https://www.mas.gov.sg/circular/test",
            normalized_url="https://www.mas.gov.sg/circular/test",
            downloaded_pdf_path="/tmp/test.pdf",
            file_hash="a" * 64,
            download_timestamp=datetime(2025, 11, 1),
        )
        assert doc.title == "Test Circular"
        assert doc.downloaded_pdf_path == "/tmp/test.pdf"
        assert doc.file_hash == "a" * 64

    def test_document_title_required(self):
        """Test that title is required."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/test",
                normalized_url="https://www.mas.gov.sg/news/test",
            )
        assert "title" in str(exc_info.value)

    def test_document_empty_title_fails(self):
        """Test that empty title after stripping raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                title="   ",  # Only whitespace
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/test",
                normalized_url="https://www.mas.gov.sg/news/test",
            )
        # Pydantic strips whitespace first, then validates min_length
        assert "at least 1 character" in str(exc_info.value) or "cannot be empty" in str(exc_info.value)

    def test_document_title_stripped(self):
        """Test that title is automatically stripped of whitespace."""
        doc = Document(
            title="  Test Title  ",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
        )
        assert doc.title == "Test Title"

    def test_document_normalized_url_lowercase(self):
        """Test that normalized_url is converted to lowercase."""
        doc = Document(
            title="Test",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/News/Test",
            normalized_url="HTTPS://WWW.MAS.GOV.SG/NEWS/TEST",
        )
        assert doc.normalized_url == "https://www.mas.gov.sg/news/test"

    def test_document_file_hash_valid_format(self):
        """Test that valid SHA-256 hash is accepted."""
        doc = Document(
            title="Test",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
            downloaded_pdf_path="/tmp/test.pdf",
            file_hash="abcdef0123456789" * 4,  # 64 hex characters
        )
        assert len(doc.file_hash) == 64

    def test_document_file_hash_invalid_length(self):
        """Test that invalid hash length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                title="Test",
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/test",
                normalized_url="https://www.mas.gov.sg/news/test",
                downloaded_pdf_path="/tmp/test.pdf",
                file_hash="abc123",  # Too short
            )
        assert "64-character" in str(exc_info.value)

    def test_document_file_hash_invalid_characters(self):
        """Test that non-hex characters in hash raise error."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                title="Test",
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/test",
                normalized_url="https://www.mas.gov.sg/news/test",
                downloaded_pdf_path="/tmp/test.pdf",
                file_hash="ZZZZZZZZ" + "0" * 56,  # Invalid hex
            )
        assert "lowercase hex" in str(exc_info.value)

    def test_document_pdf_path_requires_hash(self):
        """Test that downloaded_pdf_path requires file_hash."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                title="Test",
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/test",
                normalized_url="https://www.mas.gov.sg/news/test",
                downloaded_pdf_path="/tmp/test.pdf",
                file_hash=None,  # Missing hash
            )
        assert "file_hash must be set" in str(exc_info.value)

    def test_document_json_serialization(self):
        """Test that document serializes to JSON correctly."""
        doc = Document(
            title="Test",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
        )
        json_str = doc.model_dump_json()
        assert isinstance(json_str, str)
        assert '"title":"Test"' in json_str or '"title": "Test"' in json_str


class TestCrawlSession:
    """Tests for CrawlSession model."""

    def test_valid_crawl_session(self):
        """Test creating a valid crawl session."""
        session = CrawlSession(
            session_id="test_001",
            start_time=datetime(2025, 11, 1, 14, 0, 0),
            end_time=datetime(2025, 11, 1, 14, 5, 0),
            duration_seconds=300.0,
            documents_found=10,
            documents_downloaded=8,
            documents_skipped=2,
            errors_encountered=1,
            success=True,
        )
        assert session.session_id == "test_001"
        assert session.documents_found == 10
        assert session.success is True

    def test_crawl_session_defaults(self):
        """Test that CrawlSession has correct defaults."""
        session = CrawlSession(
            session_id="test_002",
            start_time=datetime(2025, 11, 1, 14, 0, 0),
        )
        assert session.documents_found == 0
        assert session.documents_downloaded == 0
        assert session.documents_skipped == 0
        assert session.errors_encountered == 0
        assert session.success is False
        assert session.errors_details == []
        assert session.crawl_config == {}

    def test_crawl_session_negative_counts_fail(self):
        """Test that negative counts raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CrawlSession(
                session_id="test_003",
                start_time=datetime(2025, 11, 1, 14, 0, 0),
                documents_found=-5,
            )
        assert "greater than or equal to 0" in str(exc_info.value)


class TestCrawlResult:
    """Tests for CrawlResult model."""

    def test_valid_crawl_result(self, sample_crawl_session, sample_document):
        """Test creating a valid crawl result."""
        result = CrawlResult(
            session=sample_crawl_session,
            documents=[sample_document],
        )
        assert result.session.session_id == "test_session_001"
        assert len(result.documents) == 1
        assert result.documents[0].title == "Test AML/CFT Circular"

    def test_crawl_result_empty_documents(self, sample_crawl_session):
        """Test that CrawlResult can have empty documents list."""
        result = CrawlResult(
            session=sample_crawl_session,
            documents=[],
        )
        assert len(result.documents) == 0

    def test_crawl_result_json_serialization(self, sample_crawl_session, sample_document):
        """Test that CrawlResult serializes to JSON correctly."""
        result = CrawlResult(
            session=sample_crawl_session,
            documents=[sample_document],
        )
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "session" in json_str
        assert "documents" in json_str
        assert "Test AML/CFT Circular" in json_str
