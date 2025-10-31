"""
Configuration management for MAS crawler.

Loads and validates configuration from environment variables with sensible defaults.
"""

import os
from pathlib import Path


class Config:
    """Configuration container for crawler settings."""

    def __init__(
        self,
        download_dir: str = "./downloads",
        request_timeout: int = 10,
        pdf_timeout: int = 30,
        max_pdf_size_mb: int = 50,
        retry_max_attempts: int = 3,
        user_agent: str = "DINNR-AML-Crawler/0.1.0 (+https://github.com/dinnr/singhacks)",
        log_level: str = "INFO",
    ):
        """
        Initialize configuration.

        Args:
            download_dir: Directory to save downloaded PDFs
            request_timeout: Timeout for HTTP requests in seconds
            pdf_timeout: Timeout for PDF downloads in seconds
            max_pdf_size_mb: Maximum PDF file size in megabytes
            retry_max_attempts: Maximum number of retry attempts
            user_agent: User-Agent header for HTTP requests
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.download_dir = download_dir
        self.request_timeout = request_timeout
        self.pdf_timeout = pdf_timeout
        self.max_pdf_size_mb = max_pdf_size_mb
        self.retry_max_attempts = retry_max_attempts
        self.user_agent = user_agent
        self.log_level = log_level

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Environment variables:
            MAS_DOWNLOAD_DIR: Directory for PDF downloads (default: ./downloads)
            MAS_REQUEST_TIMEOUT: HTTP request timeout in seconds (default: 10)
            MAS_PDF_TIMEOUT: PDF download timeout in seconds (default: 30)
            MAS_MAX_PDF_SIZE_MB: Maximum PDF size in MB (default: 50)
            MAS_RETRY_ATTEMPTS: Max retry attempts (default: 3)
            MAS_USER_AGENT: User-Agent header (default: DINNR-AML-Crawler/0.1.0)
            MAS_LOG_LEVEL: Logging level (default: INFO)

        Returns:
            Config instance with values from environment or defaults
        """
        return cls(
            download_dir=os.getenv("MAS_DOWNLOAD_DIR", "./downloads"),
            request_timeout=int(os.getenv("MAS_REQUEST_TIMEOUT", "10")),
            pdf_timeout=int(os.getenv("MAS_PDF_TIMEOUT", "30")),
            max_pdf_size_mb=int(os.getenv("MAS_MAX_PDF_SIZE_MB", "50")),
            retry_max_attempts=int(os.getenv("MAS_RETRY_ATTEMPTS", "3")),
            user_agent=os.getenv(
                "MAS_USER_AGENT",
                "DINNR-AML-Crawler/0.1.0 (+https://github.com/dinnr/singhacks)",
            ),
            log_level=os.getenv("MAS_LOG_LEVEL", "INFO"),
        )

    def ensure_download_dir(self) -> None:
        """Create download directory if it doesn't exist."""
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "download_dir": self.download_dir,
            "request_timeout": self.request_timeout,
            "pdf_timeout": self.pdf_timeout,
            "max_pdf_size_mb": self.max_pdf_size_mb,
            "retry_max_attempts": self.retry_max_attempts,
            "user_agent": self.user_agent,
            "log_level": self.log_level,
        }
