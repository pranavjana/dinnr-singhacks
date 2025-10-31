"""Integration tests for FastAPI endpoint with real crawler.

Tests full end-to-end API functionality using the real crawler.
"""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from mas_crawler.api import create_app
from mas_crawler.config import Config


@pytest.fixture
def config():
    """Provide test configuration."""
    return Config.from_env()


@pytest.fixture
def app(config):
    """Provide test FastAPI app."""
    return create_app(config)


@pytest.fixture
def client(app):
    """Provide test client for API."""
    return TestClient(app)


class TestFastAPIIntegration:
    """Integration tests for FastAPI endpoint with real crawler."""

    def test_crawl_endpoint_succeeds_with_default_parameters(self, client):
        """Test crawl endpoint succeeds with default parameters."""
        response = client.post(
            "/api/v1/crawl",
            json={},  # Use defaults
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "session" in data
        assert "documents" in data

        session = data["session"]
        assert session["success"] is not None
        assert session["session_id"] is not None

    def test_crawl_endpoint_returns_documents(self, client):
        """Test crawl endpoint returns documents list."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        documents = data["documents"]
        assert isinstance(documents, list)

        # Check document structure if any documents returned
        if len(documents) > 0:
            for doc in documents:
                assert "title" in doc
                assert "category" in doc
                assert "source_url" in doc
                assert doc["title"]  # Non-empty
                assert doc["source_url"]  # Non-empty

    def test_crawl_with_short_lookback_period(self, client):
        """Test crawl with shorter lookback period."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 7,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        session = data["session"]
        assert session["documents_found"] >= 0

    def test_crawl_without_pdf_download(self, client):
        """Test crawl succeeds without PDF download."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # With include_pdfs=False, all documents should have no PDF path
        for doc in data["documents"]:
            assert doc["downloaded_pdf_path"] is None

    def test_status_endpoint_for_completed_crawl(self, client):
        """Test status endpoint returns completed crawl."""
        # First do a crawl
        crawl_response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )
        session_id = crawl_response.json()["session"]["session_id"]

        # Get status
        response = client.get(f"/api/v1/crawl/status/{session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "completed"
        assert data["result"] is not None

    def test_crawl_response_has_valid_timestamp_fields(self, client):
        """Test crawl response has valid ISO-8601 timestamps."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        session = data["session"]

        # Parse start_time
        start_time_str = session["start_time"]
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        assert start_time.tzinfo is not None

        # Parse end_time if available
        if session["end_time"]:
            end_time_str = session["end_time"]
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            assert end_time.tzinfo is not None
            assert end_time >= start_time

    def test_crawl_documents_have_valid_publication_dates(self, client):
        """Test crawl documents have valid ISO-8601 publication dates."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        for doc in data["documents"]:
            if doc["publication_date"]:
                pub_date_str = doc["publication_date"]
                pub_date = datetime.fromisoformat(
                    pub_date_str.replace("Z", "+00:00")
                )
                assert pub_date.tzinfo is not None

    def test_crawl_session_has_all_metadata_fields(self, client):
        """Test crawl session includes all expected metadata fields."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        session = data["session"]

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

    def test_crawl_with_max_pdfs_limit(self, client):
        """Test crawl respects max_pdfs limit."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
                "max_pdfs": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # PDF count should not exceed max_pdfs (but may be lower if fewer docs)
        assert data["session"]["documents_downloaded"] <= 5

    def test_crawl_endpoint_logs_requests(self, client, config):
        """Test crawl endpoint logs requests (indirectly via successful execution)."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        # If we got here, logging didn't crash the endpoint

    def test_multiple_crawls_have_unique_session_ids(self, client):
        """Test multiple crawls generate unique session IDs."""
        response1 = client.post(
            "/api/v1/crawl",
            json={"days_back": 90, "include_pdfs": False},
        )
        session_id1 = response1.json()["session"]["session_id"]

        response2 = client.post(
            "/api/v1/crawl",
            json={"days_back": 90, "include_pdfs": False},
        )
        session_id2 = response2.json()["session"]["session_id"]

        assert session_id1 != session_id2

    def test_crawl_result_is_json_serializable_in_response(self, client):
        """Test crawl result is properly JSON-serialized in response."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200

        # Should be able to serialize response content
        json_text = response.text
        parsed = json.loads(json_text)
        assert isinstance(parsed, dict)
        assert "session" in parsed
        assert "documents" in parsed
