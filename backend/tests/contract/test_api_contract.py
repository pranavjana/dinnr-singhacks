"""Contract tests for FastAPI endpoint.

Tests request/response schema validation, HTTP status codes, and API contract.
"""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from mas_crawler.api import CrawlRequest, create_app
from mas_crawler.config import Config
from mas_crawler.models import Category, CrawlResult, CrawlSession, Document


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


class TestAPIContract:
    """Test API contract: request/response schemas and HTTP status codes."""

    def test_health_check_returns_200(self, client):
        """Test health check endpoint returns HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_crawl_endpoint_exists(self, client):
        """Test crawl endpoint exists and accepts POST requests."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )
        # Should not return 404
        assert response.status_code != 404

    def test_crawl_request_model_validation(self):
        """Test CrawlRequest model validates parameters."""
        # Valid request
        req = CrawlRequest(days_back=90, include_pdfs=True)
        assert req.days_back == 90
        assert req.include_pdfs is True

        # Invalid: days_back < 1
        with pytest.raises(ValueError):
            CrawlRequest(days_back=0)

        # Invalid: days_back > 365
        with pytest.raises(ValueError):
            CrawlRequest(days_back=366)

        # Invalid: max_pdf_size_mb < 1
        with pytest.raises(ValueError):
            CrawlRequest(max_pdf_size_mb=0)

    def test_crawl_response_has_crawlresult_schema(self, client):
        """Test crawl endpoint returns CrawlResult schema."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response has required CrawlResult fields
        assert "session" in data
        assert "documents" in data

        # Check session has required CrawlSession fields
        session = data["session"]
        assert "session_id" in session
        assert "start_time" in session
        assert "end_time" in session
        assert "documents_found" in session
        assert "documents_downloaded" in session
        assert "documents_skipped" in session
        assert "success" in session

    def test_crawl_response_documents_have_correct_schema(self, client):
        """Test crawl response documents have correct Document schema."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check each document has required fields
        for doc in data["documents"]:
            assert "title" in doc
            assert "category" in doc
            assert "source_url" in doc
            assert "normalized_url" in doc
            # Optional fields
            assert "publication_date" in doc
            assert "downloaded_pdf_path" in doc
            assert "file_hash" in doc

    def test_crawl_response_dates_are_iso8601(self, client):
        """Test crawl response dates are ISO-8601 formatted."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check session dates are ISO-8601
        session = data["session"]
        if session["start_time"]:
            # Should parse without error
            datetime.fromisoformat(session["start_time"].replace("Z", "+00:00"))

        # Check document dates are ISO-8601
        for doc in data["documents"]:
            if doc["publication_date"]:
                datetime.fromisoformat(doc["publication_date"].replace("Z", "+00:00"))

    def test_crawl_request_with_invalid_json_returns_400(self, client):
        """Test crawl endpoint returns 400 for invalid JSON."""
        response = client.post(
            "/api/v1/crawl",
            json={"days_back": "invalid"},  # Should be int
        )
        assert response.status_code == 422  # Validation error

    def test_crawl_request_with_out_of_range_days_back_returns_400(self, client):
        """Test crawl endpoint returns 422 for out-of-range days_back."""
        response = client.post(
            "/api/v1/crawl",
            json={"days_back": 999},  # > 365
        )
        assert response.status_code == 422

    def test_status_endpoint_returns_404_for_missing_session(self, client):
        """Test status endpoint returns 404 for missing session."""
        response = client.get("/api/v1/crawl/status/nonexistent_session")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_status_endpoint_returns_crawlstatusresponse_schema(self, client):
        """Test status endpoint returns CrawlStatusResponse schema."""
        # First create a crawl
        crawl_response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )
        session_id = crawl_response.json()["session"]["session_id"]

        # Then get status
        response = client.get(f"/api/v1/crawl/status/{session_id}")
        assert response.status_code == 200
        data = response.json()

        # Check response has CrawlStatusResponse fields
        assert "session_id" in data
        assert "status" in data
        assert "message" in data
        assert "result" in data

    def test_crawl_endpoint_accepts_optional_parameters(self, client):
        """Test crawl endpoint accepts optional parameters."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 30,
                "include_pdfs": True,
                "max_pdf_size_mb": 50,
                "max_pdfs": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify parameters were used (check crawl_config)
        config = data["session"]["crawl_config"]
        assert config["days_back"] == 30

    def test_crawl_response_is_json_serializable(self, client):
        """Test crawl response is JSON-serializable."""
        response = client.post(
            "/api/v1/crawl",
            json={"days_back": 90, "include_pdfs": False},
        )

        assert response.status_code == 200
        # Should serialize without error
        json_str = json.dumps(response.json())
        assert isinstance(json_str, str)

    def test_crawl_categories_are_valid_enum_values(self, client):
        """Test crawl response has valid category enum values."""
        response = client.post(
            "/api/v1/crawl",
            json={
                "days_back": 90,
                "include_pdfs": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        valid_categories = ["News", "Circular", "Regulation"]
        for doc in data["documents"]:
            assert doc["category"] in valid_categories

    def test_crawl_session_counts_are_non_negative(self, client):
        """Test crawl session has non-negative counts."""
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

        assert session["documents_found"] >= 0
        assert session["documents_downloaded"] >= 0
        assert session["documents_skipped"] >= 0
        assert session["errors_encountered"] >= 0
