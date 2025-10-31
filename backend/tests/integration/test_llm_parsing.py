"""
Integration tests for LLM parsing compatibility.

Tests that JSON output can be directly consumed by LLMs without transformation.
"""

import json
from datetime import datetime, timezone

import pytest

from mas_crawler.models import Category, CrawlResult, CrawlSession, Document


class TestLLMParsingCompatibility:
    """Test that JSON output is optimized for LLM consumption."""

    @pytest.fixture
    def sample_crawl_result(self):
        """Create a sample crawl result for LLM parsing tests."""
        documents = [
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
            Document(
                title="Guidance on Beneficial Ownership",
                publication_date=None,
                category=Category.REGULATION,
                source_url="https://www.mas.gov.sg/regulation/guidance-002",
                normalized_url="https://www.mas.gov.sg/regulation/guidance-002",
                downloaded_pdf_path=None,
                file_hash=None,
                download_timestamp=None,
                data_quality_notes="PDF download failed",
            ),
        ]

        session = CrawlSession(
            session_id="crawl_test_llm_parsing",
            start_time=datetime(2025, 11, 1, 14, 35, 42, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 1, 14, 38, 15, tzinfo=timezone.utc),
            duration_seconds=153.5,
            documents_found=2,
            documents_downloaded=1,
            documents_skipped=0,
            errors_encountered=1,
            errors_details=["PDF download failed for document 2"],
            success=True,
            crawl_config={"days_back": 90},
        )

        return CrawlResult(session=session, documents=documents)

    def test_json_is_parseable_without_transformation(self, sample_crawl_result):
        """LLM should be able to parse JSON without any preprocessing."""
        # Get JSON string (what LLM would receive)
        json_str = sample_crawl_result.to_json()

        # Parse with standard library (simulating LLM's JSON parser)
        parsed = json.loads(json_str)

        # LLM can access top-level structure
        assert "session" in parsed
        assert "documents" in parsed

        # LLM can access nested fields directly
        assert parsed["session"]["session_id"] == "crawl_test_llm_parsing"
        assert parsed["session"]["documents_found"] == 2
        assert len(parsed["documents"]) == 2

    def test_field_names_are_descriptive_for_llm(self, sample_crawl_result):
        """Field names should clearly indicate their purpose for LLM understanding."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Session fields are self-documenting
        session = parsed["session"]
        assert "start_time" in session  # Clear: when crawl started
        assert "end_time" in session  # Clear: when crawl ended
        assert "documents_found" in session  # Clear: how many docs discovered
        assert "documents_downloaded" in session  # Clear: how many PDFs got
        assert "success" in session  # Clear: did crawl succeed

        # Document fields are self-documenting
        doc = parsed["documents"][0]
        assert "publication_date" in doc  # Clear: when doc was published
        assert "source_url" in doc  # Clear: where doc came from
        assert "downloaded_pdf_path" in doc  # Clear: where PDF is stored
        assert "file_hash" in doc  # Clear: PDF integrity hash

    def test_llm_can_identify_successful_vs_failed_downloads(self, sample_crawl_result):
        """LLM should easily distinguish successful vs failed PDF downloads."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # First document: successful download
        doc1 = parsed["documents"][0]
        assert doc1["downloaded_pdf_path"] is not None  # LLM sees: PDF available
        assert doc1["file_hash"] is not None  # LLM sees: hash computed
        assert doc1["data_quality_notes"] is None  # LLM sees: no issues

        # Second document: failed download
        doc2 = parsed["documents"][1]
        assert doc2["downloaded_pdf_path"] is None  # LLM sees: no PDF
        assert doc2["file_hash"] is None  # LLM sees: no hash
        assert doc2["data_quality_notes"] is not None  # LLM sees: there's a problem
        assert "failed" in doc2["data_quality_notes"].lower()  # LLM sees: why failed

    def test_llm_can_extract_summary_statistics(self, sample_crawl_result):
        """LLM can extract summary statistics without calculations."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        session = parsed["session"]

        # Pre-computed statistics available directly
        assert session["documents_found"] == 2
        assert session["documents_downloaded"] == 1
        assert session["documents_skipped"] == 0
        assert session["errors_encountered"] == 1

        # LLM doesn't need to calculate:
        # - How many docs were found (already counted)
        # - How many PDFs were downloaded (already counted)
        # - Success rate (can compute: 1/2 = 50%)

    def test_llm_can_identify_document_categories(self, sample_crawl_result):
        """LLM can easily categorize documents by source."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Categories are clear string values
        categories = [doc["category"] for doc in parsed["documents"]]

        assert "Circular" in categories
        assert "Regulation" in categories

        # LLM can group by category:
        circulars = [doc for doc in parsed["documents"] if doc["category"] == "Circular"]
        regulations = [
            doc for doc in parsed["documents"] if doc["category"] == "Regulation"
        ]

        assert len(circulars) == 1
        assert len(regulations) == 1

    def test_llm_can_understand_data_quality_issues(self, sample_crawl_result):
        """LLM can identify and understand data quality problems."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Session-level errors
        assert parsed["session"]["errors_encountered"] > 0
        assert len(parsed["session"]["errors_details"]) > 0

        # LLM can read error descriptions
        error_msg = parsed["session"]["errors_details"][0]
        assert "failed" in error_msg.lower()

        # Document-level quality notes
        doc_with_issue = parsed["documents"][1]
        assert doc_with_issue["data_quality_notes"] is not None
        assert "failed" in doc_with_issue["data_quality_notes"].lower()

    def test_llm_prompt_example(self, sample_crawl_result):
        """Demonstrate how LLM would receive and parse the data."""
        json_str = sample_crawl_result.to_json()

        # Simulated LLM prompt
        prompt = f"""
Analyze the following MAS regulatory document crawl results:

{json_str}

Task: Extract the following information:
1. How many documents were discovered?
2. How many PDFs were successfully downloaded?
3. What categories of documents were found?
4. Were there any errors or data quality issues?
"""

        # Simulate LLM parsing
        parsed = json.loads(json_str)

        # LLM would extract:
        documents_found = parsed["session"]["documents_found"]
        pdfs_downloaded = parsed["session"]["documents_downloaded"]
        categories = list(set(doc["category"] for doc in parsed["documents"]))
        has_errors = parsed["session"]["errors_encountered"] > 0

        # Simulated LLM response:
        expected_response = f"""
1. Documents discovered: {documents_found}
2. PDFs successfully downloaded: {pdfs_downloaded}
3. Categories found: {', '.join(categories)}
4. Errors: {'Yes' if has_errors else 'No'} ({parsed["session"]["errors_encountered"]} errors encountered)
   - {parsed["session"]["errors_details"][0] if has_errors else 'None'}
"""

        # Assertions to verify LLM could extract correct info
        assert documents_found == 2
        assert pdfs_downloaded == 1
        assert set(categories) == {"Circular", "Regulation"}
        assert has_errors is True

    def test_json_structure_is_consistent_across_results(self):
        """JSON structure should be identical for empty vs full results."""
        # Empty result
        empty_session = CrawlSession(
            session_id="empty",
            start_time=datetime.now(timezone.utc),
            documents_found=0,
        )
        empty_result = CrawlResult(session=empty_session, documents=[])

        # Full result
        doc = Document(
            title="Test",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/test",
            normalized_url="https://www.mas.gov.sg/test",
        )
        full_session = CrawlSession(
            session_id="full",
            start_time=datetime.now(timezone.utc),
            documents_found=1,
        )
        full_result = CrawlResult(session=full_session, documents=[doc])

        # Parse both
        empty_json = json.loads(empty_result.to_json())
        full_json = json.loads(full_result.to_json())

        # Same structure
        assert set(empty_json.keys()) == set(full_json.keys())
        assert set(empty_json["session"].keys()) == set(full_json["session"].keys())

        # LLM doesn't need to handle different schemas
        assert "session" in empty_json and "session" in full_json
        assert "documents" in empty_json and "documents" in full_json

    def test_null_values_are_explicit_not_missing(self, sample_crawl_result):
        """LLM should see explicit null, not missing fields."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Document with missing fields
        incomplete_doc = parsed["documents"][1]

        # Fields are present but null (not omitted)
        assert "publication_date" in incomplete_doc
        assert incomplete_doc["publication_date"] is None  # Explicit null

        assert "downloaded_pdf_path" in incomplete_doc
        assert incomplete_doc["downloaded_pdf_path"] is None  # Explicit null

        # LLM can distinguish:
        # - Field present with value: "title": "..."
        # - Field present but null: "publication_date": null
        # - LLM knows it's not: field missing (would be ambiguous)

    def test_llm_can_filter_by_multiple_criteria(self, sample_crawl_result):
        """LLM can filter documents using multiple criteria."""
        json_str = sample_crawl_result.to_json()
        parsed = json.loads(json_str)

        # Filter: Circulars with PDFs downloaded
        results = [
            doc
            for doc in parsed["documents"]
            if doc["category"] == "Circular" and doc["downloaded_pdf_path"] is not None
        ]

        assert len(results) == 1
        assert results[0]["title"] == "Notice on AML/CFT Requirements for Trade Finance"

        # Filter: Documents with data quality issues
        issues = [
            doc
            for doc in parsed["documents"]
            if doc["data_quality_notes"] is not None
        ]

        assert len(issues) == 1
        assert "failed" in issues[0]["data_quality_notes"].lower()


class TestLLMSemanticUnderstanding:
    """Test that LLM can semantically understand the data structure."""

    def test_llm_can_infer_crawl_status(self):
        """LLM can determine if crawl was successful."""
        # Successful crawl
        success_session = CrawlSession(
            session_id="success",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            success=True,
            documents_found=10,
        )
        success_result = CrawlResult(session=success_session, documents=[])

        json_str = success_result.to_json()
        parsed = json.loads(json_str)

        # LLM sees: success=true, has end_time, no fatal errors
        assert parsed["session"]["success"] is True
        assert parsed["session"]["end_time"] is not None

    def test_llm_can_calculate_success_rate(self):
        """LLM can calculate download success rate from provided counts."""
        session = CrawlSession(
            session_id="test",
            start_time=datetime.now(timezone.utc),
            documents_found=100,
            documents_downloaded=90,
        )
        result = CrawlResult(session=session, documents=[])

        json_str = result.to_json()
        parsed = json.loads(json_str)

        # LLM can calculate: 90/100 = 90% success rate
        found = parsed["session"]["documents_found"]
        downloaded = parsed["session"]["documents_downloaded"]

        success_rate = (downloaded / found) * 100 if found > 0 else 0
        assert success_rate == 90.0

    def test_llm_understands_temporal_sequence(self):
        """LLM can understand chronological order of events."""
        session = CrawlSession(
            session_id="test",
            start_time=datetime(2025, 11, 1, 14, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 1, 14, 5, 0, tzinfo=timezone.utc),
            duration_seconds=300,
        )

        doc1 = Document(
            title="First Document",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/1",
            normalized_url="https://www.mas.gov.sg/1",
            download_timestamp=datetime(2025, 11, 1, 14, 1, 0, tzinfo=timezone.utc),
        )

        doc2 = Document(
            title="Second Document",
            category=Category.NEWS,
            source_url="https://www.mas.gov.sg/2",
            normalized_url="https://www.mas.gov.sg/2",
            download_timestamp=datetime(2025, 11, 1, 14, 2, 0, tzinfo=timezone.utc),
        )

        result = CrawlResult(session=session, documents=[doc1, doc2])
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # LLM can determine:
        # 1. Crawl started at 14:00
        # 2. First PDF downloaded at 14:01
        # 3. Second PDF downloaded at 14:02
        # 4. Crawl ended at 14:05
        # 5. Total duration: 5 minutes

        start = datetime.fromisoformat(
            parsed["session"]["start_time"].replace("Z", "+00:00")
        )
        end = datetime.fromisoformat(
            parsed["session"]["end_time"].replace("Z", "+00:00")
        )

        assert (end - start).total_seconds() == 300  # 5 minutes
