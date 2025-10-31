"""
Unit tests for JSON output validation.

Tests schema consistency, data types, field names, and JSON serialization.
"""

import json
from datetime import datetime, timezone

import pytest

from mas_crawler.models import Category, CrawlResult, CrawlSession, Document


class TestJSONSchemaConsistency:
    """Test JSON schema generation and consistency."""

    def test_get_json_schema_returns_dict(self):
        """JSON schema should be returned as a dictionary."""
        schema = CrawlResult.get_json_schema()
        assert isinstance(schema, dict)

    def test_json_schema_has_required_fields(self):
        """JSON schema should define session and documents fields."""
        schema = CrawlResult.get_json_schema()

        # Check that schema has properties
        assert "properties" in schema
        assert "session" in schema["properties"]
        assert "documents" in schema["properties"]

    def test_json_schema_defines_types(self):
        """JSON schema should specify correct types for fields."""
        schema = CrawlResult.get_json_schema()

        # Documents should be an array
        documents_schema = schema["properties"]["documents"]
        assert documents_schema.get("type") == "array"

    def test_document_schema_has_category_enum(self):
        """Document schema should define Category as enum."""
        schema = CrawlResult.get_json_schema()

        # Navigate to Document definition
        assert "$defs" in schema or "definitions" in schema
        defs = schema.get("$defs", schema.get("definitions", {}))

        assert "Category" in defs
        category_schema = defs["Category"]
        assert "enum" in category_schema
        assert set(category_schema["enum"]) == {"News", "Circular", "Regulation"}


class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            title="Test AML/CFT Circular",
            publication_date=datetime(2025, 10, 15, tzinfo=timezone.utc),
            category=Category.CIRCULAR,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
            downloaded_pdf_path="/tmp/test.pdf",
            file_hash="a" * 64,
            download_timestamp=datetime(2025, 11, 1, 14, 35, 50, tzinfo=timezone.utc),
        )

    @pytest.fixture
    def sample_crawl_result(self, sample_document):
        """Create a sample CrawlResult for testing."""
        session = CrawlSession(
            session_id="test_session_123",
            start_time=datetime(2025, 11, 1, 14, 35, 42, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 1, 14, 38, 15, tzinfo=timezone.utc),
            duration_seconds=153.5,
            documents_found=1,
            documents_downloaded=1,
            documents_skipped=0,
            errors_encountered=0,
            success=True,
            crawl_config={"days_back": 90, "download_dir": "./downloads"},
        )

        return CrawlResult(session=session, documents=[sample_document])

    def test_to_json_returns_string(self, sample_crawl_result):
        """to_json should return a valid JSON string."""
        json_str = sample_crawl_result.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON by parsing
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_has_correct_structure(self, sample_crawl_result):
        """JSON output should have session and documents keys."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        assert "session" in parsed
        assert "documents" in parsed
        assert isinstance(parsed["documents"], list)

    def test_json_field_names_are_snake_case(self, sample_crawl_result):
        """All field names should be in snake_case."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Check session fields
        session = parsed["session"]
        assert "session_id" in session
        assert "start_time" in session
        assert "end_time" in session
        assert "duration_seconds" in session
        assert "documents_found" in session
        assert "documents_downloaded" in session
        assert "documents_skipped" in session
        assert "errors_encountered" in session
        assert "errors_details" in session
        assert "crawl_config" in session

        # Check document fields
        doc = parsed["documents"][0]
        assert "publication_date" in doc
        assert "source_url" in doc
        assert "normalized_url" in doc
        assert "downloaded_pdf_path" in doc
        assert "file_hash" in doc
        assert "download_timestamp" in doc
        assert "data_quality_notes" in doc

    def test_json_dates_are_iso8601(self, sample_crawl_result):
        """All datetime fields should be in ISO-8601 format."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Check session dates
        start_time = parsed["session"]["start_time"]
        end_time = parsed["session"]["end_time"]

        # Should be ISO-8601 strings
        assert isinstance(start_time, str)
        assert isinstance(end_time, str)

        # Should be parseable as datetime
        datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        # Check document dates
        doc = parsed["documents"][0]
        pub_date = doc["publication_date"]
        download_time = doc["download_timestamp"]

        assert isinstance(pub_date, str)
        assert isinstance(download_time, str)

        datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        datetime.fromisoformat(download_time.replace("Z", "+00:00"))

    def test_json_urls_are_strings(self, sample_crawl_result):
        """URL fields should be serialized as strings."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        doc = parsed["documents"][0]
        assert isinstance(doc["source_url"], str)
        assert isinstance(doc["normalized_url"], str)

        # URLs should be valid
        assert doc["source_url"].startswith("http")
        assert doc["normalized_url"].startswith("http")

    def test_category_serialized_as_string(self, sample_crawl_result):
        """Category enum should serialize as string value."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        category = parsed["documents"][0]["category"]
        assert isinstance(category, str)
        assert category in ["News", "Circular", "Regulation"]

    def test_json_round_trip_preserves_data(self, sample_crawl_result):
        """JSON serialization and deserialization should preserve data."""
        # Serialize
        json_str = sample_crawl_result.to_json()

        # Deserialize
        restored = CrawlResult.model_validate_json(json_str)

        # Compare
        assert restored.session.session_id == sample_crawl_result.session.session_id
        assert len(restored.documents) == len(sample_crawl_result.documents)
        assert restored.documents[0].title == sample_crawl_result.documents[0].title
        assert restored.documents[0].category == sample_crawl_result.documents[0].category

    def test_validate_schema_succeeds_for_valid_data(self, sample_crawl_result):
        """validate_schema should return True for valid CrawlResult."""
        assert sample_crawl_result.validate_schema() is True

    def test_json_with_null_fields(self):
        """JSON should handle null/None fields correctly."""
        doc = Document(
            title="Test Document",
            publication_date=None,  # Null field
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/news/test",
            normalized_url="https://www.mas.gov.sg/news/test",
            downloaded_pdf_path=None,  # Null field
            file_hash=None,  # Null field
            download_timestamp=None,  # Null field
        )

        session = CrawlSession(
            session_id="test_session",
            start_time=datetime.now(timezone.utc),
            documents_found=1,
        )

        result = CrawlResult(session=session, documents=[doc])
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # Null fields should be explicitly null in JSON
        doc_json = parsed["documents"][0]
        assert doc_json["publication_date"] is None
        assert doc_json["downloaded_pdf_path"] is None
        assert doc_json["file_hash"] is None
        assert doc_json["download_timestamp"] is None


class TestDataTypeConsistency:
    """Test that all fields have consistent data types."""

    def test_session_id_is_string(self):
        """session_id should be a string."""
        session = CrawlSession(
            session_id="test_123",
            start_time=datetime.now(timezone.utc),
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert isinstance(parsed["session"]["session_id"], str)

    def test_counters_are_integers(self):
        """All count fields should be integers."""
        session = CrawlSession(
            session_id="test_123",
            start_time=datetime.now(timezone.utc),
            documents_found=10,
            documents_downloaded=8,
            documents_skipped=2,
            errors_encountered=1,
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        s = parsed["session"]
        assert isinstance(s["documents_found"], int)
        assert isinstance(s["documents_downloaded"], int)
        assert isinstance(s["documents_skipped"], int)
        assert isinstance(s["errors_encountered"], int)

    def test_duration_is_number(self):
        """duration_seconds should be a number (float or int)."""
        session = CrawlSession(
            session_id="test_123",
            start_time=datetime.now(timezone.utc),
            duration_seconds=153.5,
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        duration = parsed["session"]["duration_seconds"]
        assert isinstance(duration, (int, float))

    def test_success_is_boolean(self):
        """success field should be a boolean."""
        session = CrawlSession(
            session_id="test_123",
            start_time=datetime.now(timezone.utc),
            success=True,
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert isinstance(parsed["session"]["success"], bool)

    def test_errors_details_is_array(self):
        """errors_details should be an array of strings."""
        session = CrawlSession(
            session_id="test_123",
            start_time=datetime.now(timezone.utc),
            errors_details=["Error 1", "Error 2"],
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        errors = parsed["session"]["errors_details"]
        assert isinstance(errors, list)
        assert all(isinstance(e, str) for e in errors)


class TestJSONParsability:
    """Test that JSON can be parsed without transformation."""

    def test_json_loads_without_error(self):
        """JSON should be parseable by standard json.loads."""
        session = CrawlSession(
            session_id="test",
            start_time=datetime.now(timezone.utc),
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()

        # Should not raise exception
        parsed = json.loads(json_str)
        assert parsed is not None

    def test_json_is_valid_utf8(self):
        """JSON output should be valid UTF-8."""
        doc = Document(
            title="AML/CFT Règlement — 规定",  # Unicode characters
            category=Category.REGULATION,
            source_url="https://www.mas.gov.sg/test",
            normalized_url="https://www.mas.gov.sg/test",
        )

        session = CrawlSession(
            session_id="test",
            start_time=datetime.now(timezone.utc),
        )
        result = CrawlResult(session=session, documents=[doc])

        json_str = result.to_json()

        # Should be valid UTF-8
        json_str.encode("utf-8")

        # Should parse correctly
        parsed = json.loads(json_str)
        assert "Règlement" in parsed["documents"][0]["title"]
        assert "规定" in parsed["documents"][0]["title"]
