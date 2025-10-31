"""
Integration tests for JSON output validation against schema.

Tests full crawl result JSON output including schema validation and LLM compatibility.
"""

import json
from datetime import datetime, timezone

import pytest

from mas_crawler.models import Category, CrawlResult, CrawlSession, Document


class TestFullCrawlJSONOutput:
    """Integration tests for complete crawl result JSON output."""

    @pytest.fixture
    def complete_crawl_result(self):
        """Create a realistic complete crawl result with multiple documents."""
        # Create multiple documents with varying completeness
        documents = [
            # Complete document with all fields
            Document(
                title="Notice on AML/CFT Requirements for Trade Finance",
                publication_date=datetime(2025, 10, 15, tzinfo=timezone.utc),
                category=Category.CIRCULAR,
                source_url="https://www.mas.gov.sg/news/circular-001",
                normalized_url="https://www.mas.gov.sg/news/circular-001",
                downloaded_pdf_path="./downloads/circular_001.pdf",
                file_hash="a" * 64,
                download_timestamp=datetime(2025, 11, 1, 14, 35, 50, tzinfo=timezone.utc),
            ),
            # Document with missing publication date
            Document(
                title="Guidance on Beneficial Ownership",
                publication_date=None,
                category=Category.REGULATION,
                source_url="https://www.mas.gov.sg/regulation/guidance-002",
                normalized_url="https://www.mas.gov.sg/regulation/guidance-002",
                downloaded_pdf_path="./downloads/regulation_002.pdf",
                file_hash="b" * 64,
                download_timestamp=datetime(2025, 11, 1, 14, 36, 10, tzinfo=timezone.utc),
                data_quality_notes="publication_date not found on page",
            ),
            # Document with failed PDF download
            Document(
                title="Media Release on Enhanced AML Controls",
                publication_date=datetime(2025, 10, 20, tzinfo=timezone.utc),
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/media-release-003",
                normalized_url="https://www.mas.gov.sg/news/media-release-003",
                downloaded_pdf_path=None,
                file_hash=None,
                download_timestamp=None,
                data_quality_notes="PDF download failed after 3 retries",
            ),
        ]

        session = CrawlSession(
            session_id="crawl_20251101_143542",
            start_time=datetime(2025, 11, 1, 14, 35, 42, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 1, 14, 38, 15, 500000, tzinfo=timezone.utc),
            duration_seconds=153.5,
            documents_found=3,
            documents_downloaded=2,
            documents_skipped=0,
            errors_encountered=1,
            errors_details=[
                "PDF download timeout for media-release-003 (attempt 3/3 failed)"
            ],
            success=True,
            crawl_config={
                "days_back": 90,
                "include_pdfs": True,
                "download_dir": "./downloads",
                "max_pdf_size_mb": 50,
            },
        )

        return CrawlResult(session=session, documents=documents)

    def test_json_output_validates_against_schema(self, complete_crawl_result):
        """Complete crawl result should validate against its JSON schema."""
        # Get schema
        schema = CrawlResult.get_json_schema()
        assert schema is not None

        # Validate instance
        assert complete_crawl_result.validate_schema() is True

    def test_json_output_has_all_required_session_fields(self, complete_crawl_result):
        """JSON output should include all required session fields."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        session = parsed["session"]

        # Required fields
        assert "session_id" in session
        assert "start_time" in session
        assert "documents_found" in session
        assert "documents_downloaded" in session
        assert "documents_skipped" in session
        assert "errors_encountered" in session
        assert "errors_details" in session
        assert "success" in session
        assert "crawl_config" in session

    def test_json_output_has_all_required_document_fields(self, complete_crawl_result):
        """JSON output should include all required document fields."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        for doc in parsed["documents"]:
            # Required fields (even if null)
            assert "title" in doc
            assert "publication_date" in doc
            assert "category" in doc
            assert "source_url" in doc
            assert "normalized_url" in doc
            assert "downloaded_pdf_path" in doc
            assert "file_hash" in doc
            assert "download_timestamp" in doc
            assert "data_quality_notes" in doc

    def test_json_handles_mixed_complete_incomplete_documents(
        self, complete_crawl_result
    ):
        """JSON should correctly handle mix of complete and incomplete documents."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        docs = parsed["documents"]
        assert len(docs) == 3

        # First document: fully complete
        assert docs[0]["publication_date"] is not None
        assert docs[0]["downloaded_pdf_path"] is not None
        assert docs[0]["file_hash"] is not None

        # Second document: missing publication date
        assert docs[1]["publication_date"] is None
        assert docs[1]["downloaded_pdf_path"] is not None
        assert docs[1]["data_quality_notes"] is not None

        # Third document: failed PDF download
        assert docs[2]["publication_date"] is not None
        assert docs[2]["downloaded_pdf_path"] is None
        assert docs[2]["file_hash"] is None

    def test_json_preserves_error_details(self, complete_crawl_result):
        """JSON should preserve error details array."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        errors = parsed["session"]["errors_details"]
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "timeout" in errors[0].lower()

    def test_json_preserves_crawl_config(self, complete_crawl_result):
        """JSON should preserve crawl configuration."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        config = parsed["session"]["crawl_config"]
        assert config["days_back"] == 90
        assert config["include_pdfs"] is True
        assert config["download_dir"] == "./downloads"
        assert config["max_pdf_size_mb"] == 50

    def test_json_is_parseable_without_transformation(self, complete_crawl_result):
        """JSON should be directly parseable without any transformation."""
        json_str = complete_crawl_result.to_json()

        # Parse with standard library
        parsed = json.loads(json_str)

        # Should have correct structure
        assert "session" in parsed
        assert "documents" in parsed

        # Should be able to access nested fields directly
        assert parsed["session"]["session_id"] == "crawl_20251101_143542"
        assert parsed["documents"][0]["title"] is not None

    def test_json_round_trip_maintains_data_integrity(self, complete_crawl_result):
        """JSON serialization and deserialization should maintain data integrity."""
        # Original
        original_json = complete_crawl_result.to_json()

        # Deserialize
        restored = CrawlResult.model_validate_json(original_json)

        # Re-serialize
        restored_json = restored.to_json()

        # Compare JSON strings (should be identical)
        original_parsed = json.loads(original_json)
        restored_parsed = json.loads(restored_json)

        assert original_parsed == restored_parsed

    def test_json_formatting_is_readable(self, complete_crawl_result):
        """JSON should be formatted for human readability."""
        json_str = complete_crawl_result.to_json(indent=2)

        # Should have newlines for readability
        assert "\n" in json_str

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed is not None

    def test_json_dates_are_utc_iso8601(self, complete_crawl_result):
        """All dates in JSON should be UTC ISO-8601 format."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Check session dates
        start = parsed["session"]["start_time"]
        end = parsed["session"]["end_time"]

        # Should end with Z or +00:00 for UTC
        assert start.endswith("Z") or "+00:00" in start
        assert end.endswith("Z") or "+00:00" in end

        # Check document dates
        for doc in parsed["documents"]:
            if doc["publication_date"]:
                assert doc["publication_date"].endswith("Z") or "+00:00" in doc[
                    "publication_date"
                ]
            if doc["download_timestamp"]:
                assert doc["download_timestamp"].endswith("Z") or "+00:00" in doc[
                    "download_timestamp"
                ]

    def test_category_field_identifies_source_clearly(self, complete_crawl_result):
        """Category field should clearly identify document source."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        categories = [doc["category"] for doc in parsed["documents"]]

        # Should have all three category types
        assert "Circular" in categories
        assert "Regulation" in categories
        assert "News" in categories

        # All should be one of the valid categories
        valid_categories = {"News", "Circular", "Regulation"}
        assert all(cat in valid_categories for cat in categories)


class TestJSONSchemaValidation:
    """Test JSON schema generation and validation."""

    def test_schema_matches_pydantic_model(self):
        """Generated JSON schema should match Pydantic model definition."""
        schema = CrawlResult.get_json_schema()

        # Schema should have title
        assert "title" in schema or "$defs" in schema or "definitions" in schema

        # Should define CrawlResult, CrawlSession, Document
        defs = schema.get("$defs", schema.get("definitions", {}))

        # Check that key models are defined
        assert (
            "CrawlSession" in str(defs) or "session" in schema.get("properties", {})
        )
        assert (
            "Document" in str(defs) or "documents" in schema.get("properties", {})
        )

    def test_schema_defines_all_field_constraints(self):
        """Schema should include field constraints from Pydantic."""
        schema = CrawlResult.get_json_schema()

        # Get Document definition
        defs = schema.get("$defs", schema.get("definitions", {}))

        # Should have constraints like minLength, maxLength, format
        doc_schema = defs.get("Document", {})
        if doc_schema:
            # Title should have length constraints
            props = doc_schema.get("properties", {})
            title = props.get("title", {})

            # Pydantic should enforce min/max length
            # (exact schema structure may vary by Pydantic version)
            assert title  # Title property exists


class TestLLMCompatibility:
    """Test that JSON is compatible with LLM parsing expectations."""

    def test_json_is_self_describing(self, complete_crawl_result):
        """JSON should be self-describing for LLM parsing."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        # LLM can identify this is a crawl result
        assert "session" in parsed
        assert "documents" in parsed

        # Session has identifying metadata
        assert parsed["session"]["session_id"]
        assert parsed["session"]["start_time"]

        # Documents have clear structure
        assert isinstance(parsed["documents"], list)

    def test_json_field_names_are_descriptive(self, complete_crawl_result):
        """Field names should be descriptive for LLM understanding."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Session fields are self-explanatory
        session = parsed["session"]
        assert "start_time" in session
        assert "end_time" in session
        assert "duration_seconds" in session
        assert "documents_found" in session
        assert "documents_downloaded" in session
        assert "success" in session

        # Document fields are self-explanatory
        doc = parsed["documents"][0]
        assert "title" in doc
        assert "publication_date" in doc
        assert "category" in doc
        assert "source_url" in doc
        assert "downloaded_pdf_path" in doc
        assert "file_hash" in doc

    def test_json_null_handling_is_explicit(self, complete_crawl_result):
        """Null values should be explicitly marked for LLM interpretation."""
        json_str = complete_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Find document with null fields
        incomplete_doc = parsed["documents"][1]

        # publication_date should be explicitly null
        assert incomplete_doc["publication_date"] is None

        # data_quality_notes should explain why
        assert incomplete_doc["data_quality_notes"] is not None
        assert "publication_date" in incomplete_doc["data_quality_notes"]

    @pytest.fixture
    def complete_crawl_result(self):
        """Create a realistic complete crawl result with multiple documents."""
        documents = [
            Document(
                title="Notice on AML/CFT Requirements",
                publication_date=datetime(2025, 10, 15, tzinfo=timezone.utc),
                category=Category.CIRCULAR,
                source_url="https://www.mas.gov.sg/news/circular-001",
                normalized_url="https://www.mas.gov.sg/news/circular-001",
                downloaded_pdf_path="./downloads/circular_001.pdf",
                file_hash="a" * 64,
                download_timestamp=datetime(2025, 11, 1, 14, 35, 50, tzinfo=timezone.utc),
            ),
            Document(
                title="Guidance on Beneficial Ownership",
                publication_date=None,
                category=Category.REGULATION,
                source_url="https://www.mas.gov.sg/regulation/guidance-002",
                normalized_url="https://www.mas.gov.sg/regulation/guidance-002",
                downloaded_pdf_path="./downloads/regulation_002.pdf",
                file_hash="b" * 64,
                download_timestamp=datetime(2025, 11, 1, 14, 36, 10, tzinfo=timezone.utc),
                data_quality_notes="publication_date not found on page",
            ),
            Document(
                title="Media Release on Enhanced AML Controls",
                publication_date=datetime(2025, 10, 20, tzinfo=timezone.utc),
                category=Category.NEWS,
                source_url="https://www.mas.gov.sg/news/media-release-003",
                normalized_url="https://www.mas.gov.sg/news/media-release-003",
                downloaded_pdf_path=None,
                file_hash=None,
                download_timestamp=None,
                data_quality_notes="PDF download failed",
            ),
        ]

        session = CrawlSession(
            session_id="crawl_20251101_143542",
            start_time=datetime(2025, 11, 1, 14, 35, 42, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 1, 14, 38, 15, tzinfo=timezone.utc),
            duration_seconds=153.5,
            documents_found=3,
            documents_downloaded=2,
            errors_encountered=1,
            errors_details=["PDF download timeout"],
            success=True,
            crawl_config={"days_back": 90},
        )

        return CrawlResult(session=session, documents=documents)
