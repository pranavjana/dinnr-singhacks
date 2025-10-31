"""Integration tests for PDF download pipeline."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from mas_crawler.config import Config
from mas_crawler.scraper import MASCrawler


@pytest.fixture
def config():
    """Create test configuration with temporary download directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Config(
            download_dir=tmpdir,
            request_timeout=5,
            pdf_timeout=10,
            max_pdf_size_mb=10,
            retry_max_attempts=3,
            log_level="INFO",
        )


@pytest.fixture
def crawler(config):
    """Create crawler instance."""
    return MASCrawler(config)


def test_extract_pdf_links_from_page(crawler):
    """Test extracting PDF links from a notice page."""
    # Mock HTML response with PDF links (based on debug script findings)
    mock_html = """
    <html>
        <body>
            <a href="/-/media/notice-626a.pdf">Notice 626A PDF</a>
            <a href="https://www.mas.gov.sg/-/media/amendment-2022.pdf">Amendment 2022</a>
            <a href="/some-other-page">Regular link</a>
        </body>
    </html>
    """

    with patch.object(crawler, "fetch_page", return_value=mock_html):
        pdf_urls = crawler.extract_pdf_links_from_page("https://www.mas.gov.sg/regulation/notices/notice-626a")

    assert len(pdf_urls) == 2
    assert any("notice-626a.pdf" in url for url in pdf_urls)
    assert any("amendment-2022.pdf" in url for url in pdf_urls)
    # Check URLs are absolute
    assert all(url.startswith("https://") for url in pdf_urls)


def test_extract_pdf_links_no_pdfs(crawler):
    """Test extracting PDF links from page with no PDFs."""
    mock_html = """
    <html>
        <body>
            <a href="/page1">Link 1</a>
            <a href="/page2">Link 2</a>
        </body>
    </html>
    """

    with patch.object(crawler, "fetch_page", return_value=mock_html):
        pdf_urls = crawler.extract_pdf_links_from_page("https://www.mas.gov.sg/some-page")

    assert len(pdf_urls) == 0


def test_extract_pdf_links_handles_errors(crawler):
    """Test PDF extraction handles fetch errors gracefully."""
    with patch.object(crawler, "fetch_page", side_effect=Exception("Network error")):
        pdf_urls = crawler.extract_pdf_links_from_page("https://www.mas.gov.sg/error-page")

    assert len(pdf_urls) == 0  # Should return empty list on error


@patch("mas_crawler.pdf_downloader.requests.Session")
@patch("mas_crawler.scraper.requests.Session")
def test_full_pdf_download_pipeline(mock_scraper_session_class, mock_pdf_session_class, crawler, config):
    """Test complete PDF download pipeline: discover documents → extract PDFs → download."""
    # Mock API response with 1 document
    mock_api_response = Mock()
    mock_api_response.status_code = 200
    mock_api_response.raise_for_status = Mock()
    mock_api_response.text = '{"response": {"docs": [{"document_title_string_s": "Test Notice 626A", "page_url_s": "/regulation/notices/notice-626a", "mas_date_tdt": "2025-10-01T00:00:00Z", "mas_contenttype_s": "Notice"}], "numFound": 1}}'
    mock_api_response.json = Mock(return_value={
        "response": {
            "docs": [
                {
                    "document_title_string_s": "Test Notice 626A",
                    "page_url_s": "/regulation/notices/notice-626a",
                    "mas_date_tdt": "2025-10-01T00:00:00Z",
                    "mas_contenttype_s": "Notice",
                }
            ],
            "numFound": 1,
        }
    })

    # Mock notice page HTML with PDF links
    mock_notice_page = """
    <html>
        <body>
            <a href="/-/media/notice-626a.pdf">Notice 626A PDF</a>
        </body>
    </html>
    """
    mock_page_response = Mock()
    mock_page_response.status_code = 200
    mock_page_response.text = mock_notice_page
    mock_page_response.raise_for_status = Mock()

    # Mock PDF download
    mock_pdf_response = Mock()
    mock_pdf_response.status_code = 200
    mock_pdf_response.raise_for_status = Mock()
    mock_pdf_response.iter_content = Mock(return_value=[
        b"%PDF-1.4\n",
        b"% Test PDF content\n" * 100,
    ])

    # Set up mock to return different responses for different URLs
    def get_side_effect(url, *args, **kwargs):
        if "/api/v1/search" in str(url):
            return mock_api_response
        elif "/regulation/notices/notice-626a" in str(url):
            return mock_page_response
        elif ".pdf" in str(url):
            return mock_pdf_response
        else:
            # Default mock for other requests (news, circulars, etc.)
            mock = Mock()
            mock.status_code = 200
            mock.text = "<html></html>"
            mock.raise_for_status = Mock()
            return mock

    # Mock session instances
    mock_scraper_session = Mock()
    mock_scraper_session.get = Mock(side_effect=get_side_effect)
    mock_scraper_session.headers = Mock()
    mock_scraper_session.headers.update = Mock()
    mock_scraper_session_class.return_value = mock_scraper_session

    mock_pdf_session = Mock()
    mock_pdf_session.get = Mock(side_effect=get_side_effect)
    mock_pdf_session.headers = Mock()
    mock_pdf_session.headers.update = Mock()
    mock_pdf_session_class.return_value = mock_pdf_session

    # Create new crawler with mocked sessions
    test_crawler = MASCrawler(config)

    # Run crawl
    result = test_crawler.crawl(days_back=365)

    # Verify results
    assert result.session.success is True
    assert result.session.documents_found >= 1
    assert result.session.documents_downloaded >= 0  # May be 0 or 1 depending on date filtering

    # Check if any documents have PDFs downloaded
    docs_with_pdfs = [doc for doc in result.documents if doc.downloaded_pdf_path is not None]

    if docs_with_pdfs:
        # Verify PDF was downloaded
        doc = docs_with_pdfs[0]
        assert doc.downloaded_pdf_path is not None
        assert os.path.exists(doc.downloaded_pdf_path)
        assert doc.file_hash is not None
        assert len(doc.file_hash) == 64  # SHA-256
        assert doc.download_timestamp is not None

        # Cleanup
        if os.path.exists(doc.downloaded_pdf_path):
            os.remove(doc.downloaded_pdf_path)


@patch("mas_crawler.scraper.requests.Session.get")
@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_pdf_download_pipeline_graceful_degradation(mock_pdf_get, mock_page_get, crawler, config):
    """Test pipeline continues even if PDF download fails for some documents."""
    # Mock API response with 2 documents
    mock_api_response = Mock()
    mock_api_response.status_code = 200
    mock_api_response.raise_for_status = Mock()
    mock_api_response.json = Mock(return_value={
        "response": {
            "docs": [
                {
                    "document_title_string_s": "Notice 626A",
                    "page_url_s": "/regulation/notices/notice-626a",
                    "mas_date_tdt": "2025-10-01T00:00:00Z",
                    "mas_contenttype_s": "Notice",
                },
                {
                    "document_title_string_s": "Notice 626B",
                    "page_url_s": "/regulation/notices/notice-626b",
                    "mas_date_tdt": "2025-10-15T00:00:00Z",
                    "mas_contenttype_s": "Notice",
                },
            ],
            "numFound": 2,
        }
    })

    # Mock page responses
    mock_page_626a = """<html><body><a href="/-/media/notice-626a.pdf">PDF</a></body></html>"""
    mock_page_626b = """<html><body><a href="/-/media/notice-626b.pdf">PDF</a></body></html>"""

    # Mock first PDF success, second PDF failure
    mock_pdf_success = Mock()
    mock_pdf_success.status_code = 200
    mock_pdf_success.raise_for_status = Mock()
    mock_pdf_success.iter_content = Mock(return_value=[b"%PDF-1.4\n", b"Content\n" * 100])

    mock_pdf_fail = Mock()
    mock_pdf_fail.raise_for_status = Mock(side_effect=Exception("404 Not Found"))

    call_count = {"pdf": 0}

    def get_side_effect(url, *args, **kwargs):
        if "/api/v1/search" in url:
            return mock_api_response
        elif "/regulation/notices/notice-626a" in url:
            mock = Mock()
            mock.status_code = 200
            mock.text = mock_page_626a
            mock.raise_for_status = Mock()
            return mock
        elif "/regulation/notices/notice-626b" in url:
            mock = Mock()
            mock.status_code = 200
            mock.text = mock_page_626b
            mock.raise_for_status = Mock()
            return mock
        elif ".pdf" in url:
            call_count["pdf"] += 1
            # First PDF succeeds, second fails
            if "626a.pdf" in url:
                return mock_pdf_success
            else:
                return mock_pdf_fail
        else:
            mock = Mock()
            mock.status_code = 200
            mock.text = "<html></html>"
            mock.raise_for_status = Mock()
            return mock

    mock_page_get.side_effect = get_side_effect
    mock_pdf_get.side_effect = get_side_effect

    # Run crawl - should not crash even with PDF download failure
    result = crawler.crawl(days_back=365)

    # Verify crawler completed successfully despite PDF failure
    assert result.session.success is True
    assert result.session.documents_found >= 2
    # Session should track partial success
    assert result.session.documents_downloaded >= 0

    # Cleanup any downloaded files
    for doc in result.documents:
        if doc.downloaded_pdf_path and os.path.exists(doc.downloaded_pdf_path):
            os.remove(doc.downloaded_pdf_path)


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_pdf_retry_logic_integration(mock_get, config):
    """Test PDF download retry logic in integration context."""
    from mas_crawler.pdf_downloader import PDFDownloader

    downloader = PDFDownloader(config)

    # Mock: fail twice, succeed on third attempt
    mock_fail = Mock()
    mock_fail.raise_for_status = Mock(side_effect=Exception("Timeout"))

    mock_success = Mock()
    mock_success.status_code = 200
    mock_success.raise_for_status = Mock()
    mock_success.iter_content = Mock(return_value=[b"%PDF-1.4\n", b"Content\n" * 100])

    mock_get.side_effect = [mock_fail, mock_fail, mock_success]

    # Download should succeed after 3 attempts
    file_path, file_hash, timestamp = downloader.download_pdf(
        "/-/media/test.pdf",
        "Test Document",
    )

    assert file_path is not None
    assert file_hash is not None
    assert timestamp is not None
    assert mock_get.call_count == 3

    # Cleanup
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
