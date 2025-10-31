"""
Custom exception classes for MAS crawler.

Defines specific error types for different failure scenarios.
"""


class MASCrawlerError(Exception):
    """Base exception for all MAS crawler errors."""

    pass


class HTTPError(MASCrawlerError):
    """Raised when HTTP request fails (non-2xx status code)."""

    pass


class PDFDownloadError(MASCrawlerError):
    """Raised when PDF download fails (all retries exhausted, validation failed, etc.)."""

    pass


class ParseError(MASCrawlerError):
    """Raised when HTML parsing fails or expected elements are not found."""

    pass


class RobotsViolation(MASCrawlerError):
    """Raised when request would violate robots.txt rules."""

    pass


class DataValidationError(MASCrawlerError):
    """Raised when document data fails Pydantic validation."""

    pass
