"""Unit tests for structured logging."""

import json
import logging
import pytest
from io import StringIO

from mas_crawler.logger import (
    setup_logging,
    JSONFormatter,
    log_document_discovered,
    log_pdf_download_start,
    log_pdf_download_success,
    log_pdf_download_retry,
    log_pdf_download_failure,
    log_crawl_session_start,
    log_crawl_session_end,
)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_json_formatter_basic_message(self):
        """Test that JSONFormatter outputs valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert isinstance(log_data, dict)
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "event" in log_data
        assert "logger" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["event"] == "Test message"
        assert log_data["logger"] == "test_logger"

    def test_json_formatter_with_extra_fields(self):
        """Test that JSONFormatter includes extra fields from record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Document discovered",
            args=(),
            exc_info=None,
        )
        record.document_url = "https://www.mas.gov.sg/test"
        record.status = "discovered"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["document_url"] == "https://www.mas.gov.sg/test"
        assert log_data["status"] == "discovered"

    def test_json_formatter_timestamp_format(self):
        """Test that timestamp is in ISO-8601 format with Z suffix."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Timestamp should end with 'Z' for UTC
        assert log_data["timestamp"].endswith("Z")
        # Should be parseable as ISO-8601
        from datetime import datetime
        datetime.fromisoformat(log_data["timestamp"].replace("Z", "+00:00"))


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger instance."""
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "mas_crawler"

    def test_setup_logging_sets_log_level(self):
        """Test that setup_logging sets the correct log level."""
        logger = setup_logging(log_level="DEBUG")
        assert logger.level == logging.DEBUG

        logger = setup_logging(log_level="WARNING")
        assert logger.level == logging.WARNING

    def test_setup_logging_console_output(self):
        """Test that setup_logging configures console handler."""
        logger = setup_logging(log_level="INFO")
        assert len(logger.handlers) >= 1
        # At least one handler should be a StreamHandler
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_setup_logging_no_propagation(self):
        """Test that logger does not propagate to root logger."""
        logger = setup_logging()
        assert logger.propagate is False


class TestLogHelperFunctions:
    """Tests for log helper functions."""

    def setup_method(self):
        """Set up a logger with string buffer for testing."""
        self.logger = logging.getLogger("test_mas_crawler")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Add string buffer handler
        self.log_buffer = StringIO()
        handler = logging.StreamHandler(self.log_buffer)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def get_last_log(self):
        """Parse the last log entry as JSON."""
        log_output = self.log_buffer.getvalue()
        if not log_output:
            return None
        lines = log_output.strip().split("\n")
        return json.loads(lines[-1])

    def test_log_document_discovered(self):
        """Test log_document_discovered creates correct log entry."""
        log_document_discovered(
            self.logger,
            document_url="https://www.mas.gov.sg/news/test",
            document_title="Test Circular",
            category="Circular",
            publication_date="2025-10-15",
        )

        log_entry = self.get_last_log()
        assert log_entry is not None
        assert log_entry["event"] == "Document discovered"
        assert log_entry["document_url"] == "https://www.mas.gov.sg/news/test"
        assert log_entry["document_title"] == "Test Circular"
        assert log_entry["status"] == "discovered"
        assert log_entry["details"]["category"] == "Circular"

    def test_log_pdf_download_start(self):
        """Test log_pdf_download_start creates correct log entry."""
        log_pdf_download_start(
            self.logger,
            document_url="https://www.mas.gov.sg/news/test",
            pdf_url="https://www.mas.gov.sg/news/test.pdf",
        )

        log_entry = self.get_last_log()
        assert log_entry["event"] == "PDF download started"
        assert log_entry["status"] == "download_started"
        assert log_entry["details"]["pdf_url"] == "https://www.mas.gov.sg/news/test.pdf"

    def test_log_pdf_download_success(self):
        """Test log_pdf_download_success creates correct log entry."""
        log_pdf_download_success(
            self.logger,
            document_url="https://www.mas.gov.sg/news/test",
            file_path="/tmp/test.pdf",
            file_hash="abc123" * 10,
        )

        log_entry = self.get_last_log()
        assert log_entry["event"] == "PDF download successful"
        assert log_entry["status"] == "download_success"
        assert log_entry["details"]["file_path"] == "/tmp/test.pdf"
        assert "file_hash" in log_entry["details"]

    def test_log_pdf_download_retry(self):
        """Test log_pdf_download_retry creates correct log entry."""
        log_pdf_download_retry(
            self.logger,
            document_url="https://www.mas.gov.sg/news/test",
            attempt=2,
            max_attempts=3,
            error="Timeout",
        )

        log_entry = self.get_last_log()
        assert "retry" in log_entry["event"]
        assert log_entry["status"] == "download_retry"
        assert log_entry["details"]["attempt"] == 2
        assert log_entry["details"]["max_attempts"] == 3
        assert log_entry["details"]["error"] == "Timeout"

    def test_log_pdf_download_failure(self):
        """Test log_pdf_download_failure creates correct log entry."""
        log_pdf_download_failure(
            self.logger,
            document_url="https://www.mas.gov.sg/news/test",
            error="Max retries exceeded",
        )

        log_entry = self.get_last_log()
        assert log_entry["event"] == "PDF download failed"
        assert log_entry["level"] == "ERROR"
        assert log_entry["status"] == "download_failed"
        assert log_entry["details"]["error"] == "Max retries exceeded"

    def test_log_crawl_session_start(self):
        """Test log_crawl_session_start creates correct log entry."""
        log_crawl_session_start(
            self.logger,
            session_id="test_session_001",
            config={"days_back": 90, "include_pdfs": True},
        )

        log_entry = self.get_last_log()
        assert "Starting crawl session" in log_entry["event"]
        assert log_entry["status"] == "session_started"
        assert log_entry["details"]["session_id"] == "test_session_001"
        assert log_entry["details"]["config"]["days_back"] == 90

    def test_log_crawl_session_end(self):
        """Test log_crawl_session_end creates correct log entry."""
        log_crawl_session_end(
            self.logger,
            session_id="test_session_001",
            documents_found=10,
            documents_downloaded=8,
            documents_skipped=2,
            errors_encountered=1,
            success=True,
        )

        log_entry = self.get_last_log()
        assert "Crawl session completed" in log_entry["event"]
        assert log_entry["status"] == "session_completed"
        assert log_entry["details"]["documents_found"] == 10
        assert log_entry["details"]["documents_downloaded"] == 8
        assert log_entry["details"]["success"] is True
