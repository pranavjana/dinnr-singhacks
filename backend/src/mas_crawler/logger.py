"""Structured logging for compliance audit trails."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON for compliance audits."""

    def _serialize_value(self, value: Any) -> Any:
        """
        Convert value to JSON-serializable format.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable version of value
        """
        # Handle Pydantic HttpUrl objects
        if hasattr(value, '__class__') and value.__class__.__name__ == 'HttpUrl':
            return str(value)

        # Handle dict values recursively
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # Handle list values recursively
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        # Return as-is for JSON-serializable types
        return value

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }

        # Add optional fields if present (with serialization)
        if hasattr(record, "document_url"):
            log_data["document_url"] = self._serialize_value(record.document_url)
        if hasattr(record, "document_title"):
            log_data["document_title"] = self._serialize_value(record.document_title)
        if hasattr(record, "status"):
            log_data["status"] = self._serialize_value(record.status)
        if hasattr(record, "details"):
            log_data["details"] = self._serialize_value(record.details)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure structured logging for MAS crawler.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file (defaults to stdout only)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("mas_crawler")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_document_discovered(
    logger: logging.Logger,
    document_url: str,
    document_title: str,
    category: str,
    publication_date: Optional[str] = None,
) -> None:
    """Log document discovery event."""
    logger.info(
        "Document discovered",
        extra={
            "document_url": document_url,
            "document_title": document_title,
            "status": "discovered",
            "details": {
                "category": category,
                "publication_date": publication_date,
            },
        },
    )


def log_pdf_download_start(
    logger: logging.Logger,
    document_url: str,
    pdf_url: str,
) -> None:
    """Log PDF download start."""
    logger.info(
        "PDF download started",
        extra={
            "document_url": document_url,
            "status": "download_started",
            "details": {"pdf_url": pdf_url},
        },
    )


def log_pdf_download_success(
    logger: logging.Logger,
    document_url: str,
    file_path: str,
    file_hash: str,
) -> None:
    """Log successful PDF download."""
    logger.info(
        "PDF download successful",
        extra={
            "document_url": document_url,
            "status": "download_success",
            "details": {
                "file_path": file_path,
                "file_hash": file_hash,
            },
        },
    )


def log_pdf_download_retry(
    logger: logging.Logger,
    document_url: str,
    attempt: int,
    max_attempts: int,
    error: str,
) -> None:
    """Log PDF download retry attempt."""
    logger.warning(
        f"PDF download retry (attempt {attempt}/{max_attempts})",
        extra={
            "document_url": document_url,
            "status": "download_retry",
            "details": {
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": error,
            },
        },
    )


def log_pdf_download_failure(
    logger: logging.Logger,
    document_url: str,
    error: str,
) -> None:
    """Log PDF download failure after all retries."""
    logger.error(
        "PDF download failed",
        extra={
            "document_url": document_url,
            "status": "download_failed",
            "details": {"error": error},
        },
    )


def log_crawl_session_start(
    logger: logging.Logger,
    session_id: str,
    config: dict,
) -> None:
    """Log crawl session start."""
    logger.info(
        f"Starting crawl session: {session_id}",
        extra={
            "status": "session_started",
            "details": {"session_id": session_id, "config": config},
        },
    )


def log_crawl_session_end(
    logger: logging.Logger,
    session_id: str,
    documents_found: int,
    documents_downloaded: int,
    documents_skipped: int,
    errors_encountered: int,
    success: bool,
) -> None:
    """Log crawl session completion."""
    logger.info(
        f"Crawl session completed: {session_id}",
        extra={
            "status": "session_completed",
            "details": {
                "session_id": session_id,
                "documents_found": documents_found,
                "documents_downloaded": documents_downloaded,
                "documents_skipped": documents_skipped,
                "errors_encountered": errors_encountered,
                "success": success,
            },
        },
    )
