"""Integration tests for full MAS crawler workflow."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from mas_crawler.config import Config
from mas_crawler.scraper import MASCrawler
from mas_crawler.models import Category


# Sample HTML fixtures
SAMPLE_NEWS_HTML = """
<html>
<body>
    <article>
        <h2><a href="/news/aml-circular-2025">AML/CFT Requirements Update</a></h2>
        <time datetime="2025-10-15">15 Oct 2025</time>
    </article>
    <article>
        <h2><a href="/news/beneficial-ownership">Beneficial Ownership Guidance</a></h2>
        <time datetime="2025-09-20">20 Sep 2025</time>
    </article>
</body>
</html>
"""

SAMPLE_CIRCULARS_HTML = """
<html>
<body>
    <table>
        <tr>
            <td><a href="/regulation/circular-001">Circular on Trade Finance AML</a></td>
            <td>2025-10-01</td>
        </tr>
        <tr>
            <td><a href="/regulation/circular-002">Risk Assessment Guidelines</a></td>
            <td>2025-09-15</td>
        </tr>
    </table>
</body>
</html>
"""

SAMPLE_REGULATION_HTML = """
<html>
<body>
    <div class="regulation-item">
        <h3><a href="/regulation/notice-aml-2025">AML Notice 2025</a></h3>
        <span class="date">2025-10-20</span>
    </div>
</body>
</html>
"""


@pytest.fixture
def test_config():
    """Configuration for testing."""
    return Config(
        download_dir="/tmp/test_downloads",
        request_timeout=5,
        pdf_timeout=10,
        max_pdf_size_mb=50,
        retry_max_attempts=2,
        user_agent="TestCrawler/1.0",
        log_level="WARNING",  # Reduce log noise in tests
    )


@pytest.fixture
def mock_crawler(test_config):
    """Create crawler with mocked HTTP requests."""
    with patch("mas_crawler.scraper.requests.Session") as mock_session_class:
        # Create mock session
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock HTTP responses
        def mock_get(url, timeout=None):
            response = Mock()
            response.status_code = 200

            if "news" in url:
                response.text = SAMPLE_NEWS_HTML
            elif "circulars" in url:
                response.text = SAMPLE_CIRCULARS_HTML
            elif "regulation" in url:
                response.text = SAMPLE_REGULATION_HTML
            elif "robots.txt" in url:
                response.text = "User-agent: *\nAllow: /"
            else:
                response.text = "<html><body></body></html>"

            response.raise_for_status = Mock()
            return response

        mock_session.get = Mock(side_effect=mock_get)

        # Create crawler
        crawler = MASCrawler(test_config)
        yield crawler


def test_full_crawl_success(mock_crawler):
    """Test successful full crawl of all sections."""
    result = mock_crawler.crawl(days_back=90)

    # Check session metadata
    assert result.session.session_id.startswith("crawl_")
    assert result.session.start_time is not None
    assert result.session.end_time is not None
    assert result.session.duration_seconds >= 0
    assert result.session.success is True

    # Check documents discovered
    assert result.session.documents_found >= 5
    assert len(result.documents) >= 5

    # Check all categories present
    categories = {doc.category for doc in result.documents}
    assert Category.NEWS in categories
    assert Category.CIRCULAR in categories
    assert Category.REGULATION in categories


def test_crawl_with_recent_filter(mock_crawler):
    """Test that 90-day filter works correctly."""
    # Crawl with 30-day window (should filter out older docs)
    result = mock_crawler.crawl(days_back=30)

    # All returned documents should have recent dates
    for doc in result.documents:
        if doc.publication_date:
            age_days = (datetime.now(timezone.utc) - doc.publication_date).days
            # Either within window or no date (pragmatic approach)
            assert age_days <= 30 or doc.publication_date is None


def test_crawl_handles_section_failure(test_config):
    """Test graceful degradation when one section fails."""
    with patch("mas_crawler.scraper.requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        def mock_get(url, timeout=None):
            response = Mock()

            if "news" in url:
                # News section succeeds
                response.status_code = 200
                response.text = SAMPLE_NEWS_HTML
                response.raise_for_status = Mock()
            elif "circulars" in url:
                # Circulars section fails
                response.status_code = 404
                response.raise_for_status = Mock(
                    side_effect=Exception("HTTP 404")
                )
            elif "regulation" in url:
                # Regulation section succeeds
                response.status_code = 200
                response.text = SAMPLE_REGULATION_HTML
                response.raise_for_status = Mock()
            elif "robots.txt" in url:
                response.status_code = 200
                response.text = "User-agent: *\nAllow: /"
                response.raise_for_status = Mock()
            else:
                response.status_code = 404
                response.raise_for_status = Mock(
                    side_effect=Exception("HTTP 404")
                )

            return response

        mock_session.get = Mock(side_effect=mock_get)

        crawler = MASCrawler(test_config)
        result = crawler.crawl()

        # Should still succeed with partial results
        assert result.session.success is True  # 2 out of 3 sections succeeded
        assert result.session.errors_encountered > 0
        assert len(result.session.errors_details) > 0
        assert "Circulars" in result.session.errors_details[0]

        # Should have documents from News and Regulation
        assert len(result.documents) >= 2


def test_robots_txt_compliance(test_config):
    """Test that crawler respects robots.txt rules."""
    with patch("mas_crawler.scraper.RobotFileParser") as mock_robot_parser_class:
        with patch("mas_crawler.scraper.requests.Session") as mock_session_class:
            # Mock robots.txt parser
            mock_robot_parser = Mock()
            mock_robot_parser_class.return_value = mock_robot_parser

            def mock_can_fetch(user_agent, url):
                # Block news section, allow others
                if "/news" in url:
                    return False
                return True

            mock_robot_parser.can_fetch = Mock(side_effect=mock_can_fetch)
            mock_robot_parser.set_url = Mock()
            mock_robot_parser.read = Mock()

            # Mock HTTP session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            def mock_get(url, timeout=None):
                response = Mock()
                response.status_code = 200

                if "circulars" in url:
                    response.text = SAMPLE_CIRCULARS_HTML
                elif "regulation" in url:
                    response.text = SAMPLE_REGULATION_HTML
                else:
                    response.text = "<html></html>"

                response.raise_for_status = Mock()
                return response

            mock_session.get = Mock(side_effect=mock_get)

            crawler = MASCrawler(test_config)
            result = crawler.crawl()

            # Should have errors due to robots.txt blocking
            assert result.session.errors_encountered > 0
            # Should still have documents from other sections
            assert len(result.documents) >= 1


def test_date_parsing_various_formats(mock_crawler):
    """Test that crawler can parse different date formats."""
    # The mock HTML has different date formats:
    # - ISO format with datetime attribute
    # - Plain text dates
    # - Different separators

    result = mock_crawler.crawl()

    # Check that dates were parsed
    docs_with_dates = [doc for doc in result.documents if doc.publication_date]
    assert len(docs_with_dates) >= 1  # At least some dates should parse

    # All parsed dates should be datetime objects
    for doc in docs_with_dates:
        assert isinstance(doc.publication_date, datetime)
        # Should have timezone info (UTC)
        assert doc.publication_date.tzinfo is not None


def test_url_normalization(mock_crawler):
    """Test that URLs are normalized for deduplication."""
    result = mock_crawler.crawl()

    for doc in result.documents:
        # Normalized URL should be lowercase
        assert doc.normalized_url == doc.normalized_url.lower()

        # Normalized URL should not have query params or fragments
        assert "?" not in doc.normalized_url
        assert "#" not in doc.normalized_url


def test_data_quality_notes_for_missing_fields(test_config):
    """Test that data quality notes are added for missing fields."""
    # HTML without dates
    html_no_dates = """
    <html>
    <body>
        <article>
            <h2><a href="/news/no-date-doc">Document Without Date</a></h2>
        </article>
    </body>
    </html>
    """

    with patch("mas_crawler.scraper.requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        def mock_get(url, timeout=None):
            response = Mock()
            response.status_code = 200
            response.raise_for_status = Mock()

            if "news" in url:
                response.text = html_no_dates
            elif "robots.txt" in url:
                response.text = "User-agent: *\nAllow: /"
            else:
                response.text = "<html></html>"

            return response

        mock_session.get = Mock(side_effect=mock_get)

        crawler = MASCrawler(test_config)
        result = crawler.crawl()

        # Should have document without date
        docs_no_date = [
            doc for doc in result.documents
            if doc.publication_date is None and doc.data_quality_notes
        ]
        assert len(docs_no_date) >= 1
        assert "publication_date not found" in docs_no_date[0].data_quality_notes


def test_crawl_result_json_serialization(mock_crawler):
    """Test that CrawlResult can be serialized to JSON."""
    result = mock_crawler.crawl()

    # Should serialize without errors
    json_output = result.model_dump_json(indent=2)
    assert isinstance(json_output, str)
    assert len(json_output) > 100

    # Should contain expected fields
    assert "session" in json_output
    assert "documents" in json_output
    assert "session_id" in json_output
    assert "documents_found" in json_output


def test_retry_logic_on_transient_failures(test_config):
    """Test that crawler retries on transient failures."""
    with patch("mas_crawler.scraper.RobotFileParser"):  # Mock robots.txt
        with patch("mas_crawler.scraper.time.sleep"):  # Skip sleep delays
            with patch("mas_crawler.scraper.requests.Session") as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value = mock_session

                # Track attempt count
                attempt_count = {"news": 0}

                def mock_get(url, timeout=None):
                    response = Mock()

                    if "news" in url:
                        attempt_count["news"] += 1
                        if attempt_count["news"] < 2:
                            # First attempt fails
                            import requests
                            raise requests.exceptions.Timeout("Timeout")
                        else:
                            # Second attempt succeeds
                            response.status_code = 200
                            response.text = SAMPLE_NEWS_HTML
                            response.raise_for_status = Mock()
                            return response
                    else:
                        response.status_code = 200
                        response.text = "<html></html>"
                        response.raise_for_status = Mock()
                        return response

                mock_session.get = Mock(side_effect=mock_get)

                crawler = MASCrawler(test_config)
                result = crawler.crawl()

                # Should succeed after retry
                assert result.session.success is True
                # Should have retried at least once
                assert attempt_count["news"] >= 2
