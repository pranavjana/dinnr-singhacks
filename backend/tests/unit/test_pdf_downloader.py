"""Unit tests for PDF downloader."""

import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from mas_crawler.config import Config
from mas_crawler.errors import PDFDownloadError
from mas_crawler.pdf_downloader import PDFDownloader


@pytest.fixture
def config():
    """Create test configuration."""
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
def downloader(config):
    """Create PDF downloader instance."""
    return PDFDownloader(config)


def test_downloader_initialization(config):
    """Test PDF downloader initializes correctly."""
    downloader = PDFDownloader(config)
    assert downloader.config == config
    assert downloader.logger is not None
    assert downloader.session is not None


def test_download_dir_creation(config):
    """Test download directory is created if it doesn't exist."""
    # Remove directory
    if os.path.exists(config.download_dir):
        os.rmdir(config.download_dir)

    # Create downloader (should recreate directory)
    downloader = PDFDownloader(config)
    assert os.path.exists(config.download_dir)


def test_generate_safe_filename_with_title(downloader):
    """Test filename generation with document title."""
    url = "https://www.mas.gov.sg/-/media/test-document.pdf"
    title = "Test Document 2024"

    filename = downloader._generate_safe_filename(url, title)

    assert filename.endswith(".pdf")
    assert "Test_Document_2024" in filename
    assert ".." not in filename
    assert "/" not in filename


def test_generate_safe_filename_without_title(downloader):
    """Test filename generation without document title."""
    url = "https://www.mas.gov.sg/-/media/test-document.pdf"

    filename = downloader._generate_safe_filename(url, None)

    assert filename.endswith(".pdf")
    assert "test-document" in filename.lower() or "test_document" in filename.lower()


def test_generate_safe_filename_removes_path_traversal(downloader):
    """Test filename sanitization removes path traversal attempts."""
    url = "https://www.mas.gov.sg/-/media/../../../etc/passwd.pdf"
    title = "../../etc/passwd"

    filename = downloader._generate_safe_filename(url, title)

    assert ".." not in filename
    assert "/" not in filename
    assert "\\" not in filename


def test_validate_pdf_valid_file(downloader, config):
    """Test PDF validation with valid PDF file."""
    # Create a valid PDF file (with PDF magic bytes)
    pdf_path = os.path.join(config.download_dir, "test.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"% Fake PDF content for testing\n")
        f.write(b"Test content " * 100)  # Add some content

    assert downloader._validate_pdf(pdf_path) is True

    # Cleanup
    os.remove(pdf_path)


def test_validate_pdf_missing_magic_bytes(downloader, config):
    """Test PDF validation fails for file without PDF magic bytes."""
    # Create a file without PDF magic bytes
    pdf_path = os.path.join(config.download_dir, "fake.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"This is not a PDF file")

    assert downloader._validate_pdf(pdf_path) is False

    # Cleanup
    os.remove(pdf_path)


def test_validate_pdf_empty_file(downloader, config):
    """Test PDF validation fails for empty file."""
    # Create empty file
    pdf_path = os.path.join(config.download_dir, "empty.pdf")
    with open(pdf_path, "wb") as f:
        pass

    assert downloader._validate_pdf(pdf_path) is False

    # Cleanup
    os.remove(pdf_path)


def test_validate_pdf_file_too_large(downloader, config):
    """Test PDF validation fails for file exceeding size limit."""
    # Create a file larger than max_pdf_size_mb
    pdf_path = os.path.join(config.download_dir, "large.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        # Write more than max_pdf_size_mb (10 MB) of data
        f.write(b"X" * (11 * 1024 * 1024))  # 11 MB

    assert downloader._validate_pdf(pdf_path) is False

    # Cleanup
    os.remove(pdf_path)


def test_validate_pdf_nonexistent_file(downloader):
    """Test PDF validation fails for non-existent file."""
    assert downloader._validate_pdf("/nonexistent/file.pdf") is False


def test_compute_file_hash(downloader, config):
    """Test file hash computation."""
    # Create a test file
    pdf_path = os.path.join(config.download_dir, "test_hash.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"Test content for hashing")

    file_hash = downloader._compute_file_hash(pdf_path)

    assert file_hash is not None
    assert len(file_hash) == 64  # SHA-256 produces 64-character hex string
    assert all(c in "0123456789abcdef" for c in file_hash)

    # Cleanup
    os.remove(pdf_path)


def test_compute_file_hash_same_content_same_hash(downloader, config):
    """Test that identical content produces identical hash."""
    content = b"Identical test content"

    # Create first file
    pdf_path1 = os.path.join(config.download_dir, "test1.pdf")
    with open(pdf_path1, "wb") as f:
        f.write(content)
    hash1 = downloader._compute_file_hash(pdf_path1)

    # Create second file with same content
    pdf_path2 = os.path.join(config.download_dir, "test2.pdf")
    with open(pdf_path2, "wb") as f:
        f.write(content)
    hash2 = downloader._compute_file_hash(pdf_path2)

    assert hash1 == hash2

    # Cleanup
    os.remove(pdf_path1)
    os.remove(pdf_path2)


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_download_pdf_success(mock_get, downloader, config):
    """Test successful PDF download."""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.iter_content = Mock(return_value=[b"%PDF-1.4\n", b"Test PDF content\n" * 100])
    mock_get.return_value = mock_response

    url = "/-/media/test.pdf"
    title = "Test Document"

    file_path, file_hash, download_timestamp = downloader.download_pdf(url, title)

    assert file_path is not None
    assert file_hash is not None
    assert download_timestamp is not None
    assert os.path.exists(file_path)
    assert file_path.endswith(".pdf")
    assert len(file_hash) == 64  # SHA-256

    # Cleanup
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_download_pdf_retry_on_failure(mock_get, downloader, config):
    """Test PDF download retries on failure."""
    # Mock HTTP response to fail twice, then succeed
    mock_response_fail = Mock()
    mock_response_fail.raise_for_status = Mock(side_effect=requests.HTTPError("503 Service Unavailable"))

    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.raise_for_status = Mock()
    mock_response_success.iter_content = Mock(return_value=[b"%PDF-1.4\n", b"Test PDF content\n" * 100])

    mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

    url = "/-/media/test.pdf"
    title = "Test Document"

    file_path, file_hash, download_timestamp = downloader.download_pdf(url, title)

    assert file_path is not None
    assert mock_get.call_count == 3  # 2 failures + 1 success

    # Cleanup
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_download_pdf_all_retries_fail(mock_get, downloader, config):
    """Test PDF download returns None after all retries fail."""
    # Mock HTTP response to fail all attempts
    mock_response = Mock()
    mock_response.raise_for_status = Mock(side_effect=requests.HTTPError("404 Not Found"))
    mock_get.return_value = mock_response

    url = "/-/media/nonexistent.pdf"
    title = "Nonexistent Document"

    file_path, file_hash, download_timestamp = downloader.download_pdf(url, title)

    assert file_path is None
    assert file_hash is None
    assert download_timestamp is None
    assert mock_get.call_count == config.retry_max_attempts


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_download_pdf_validation_failure(mock_get, downloader, config):
    """Test PDF download fails if validation fails."""
    # Mock HTTP response with invalid PDF content
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.iter_content = Mock(return_value=[b"Not a PDF file"])
    mock_get.return_value = mock_response

    url = "/-/media/invalid.pdf"
    title = "Invalid PDF"

    file_path, file_hash, download_timestamp = downloader.download_pdf(url, title)

    assert file_path is None
    assert file_hash is None
    assert download_timestamp is None


@patch("mas_crawler.pdf_downloader.requests.Session.get")
def test_download_pdf_resolves_relative_url(mock_get, downloader, config):
    """Test PDF download resolves relative URLs correctly."""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.iter_content = Mock(return_value=[b"%PDF-1.4\n", b"Test PDF content\n" * 100])
    mock_get.return_value = mock_response

    relative_url = "/-/media/test.pdf"
    title = "Test Document"

    file_path, file_hash, download_timestamp = downloader.download_pdf(relative_url, title)

    # Check that full URL was used in request
    assert mock_get.called
    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("https://www.mas.gov.sg")

    # Cleanup
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
