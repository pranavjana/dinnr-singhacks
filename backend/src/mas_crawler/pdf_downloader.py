"""PDF download and validation logic."""

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

from .config import Config
from .errors import PDFDownloadError
from .logger import setup_logging


class PDFDownloader:
    """Handles PDF download with retry logic and validation."""

    # PDF file magic bytes
    PDF_MAGIC_BYTES = b"%PDF"

    def __init__(self, config: Config):
        """
        Initialize PDF downloader.

        Args:
            config: Configuration object with download settings
        """
        self.config = config
        self.logger = setup_logging(log_level=config.log_level)
        self.session = requests.Session()

        # Use browser headers for downloads (same as crawler)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })

        # Create download directory if it doesn't exist
        self._ensure_download_dir()

    def _ensure_download_dir(self) -> None:
        """Create download directory if it doesn't exist."""
        try:
            Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)
            self.logger.debug(
                f"Download directory ready: {self.config.download_dir}",
                extra={"status": "dir_ready"},
            )
        except Exception as e:
            error_msg = f"Failed to create download directory: {e}"
            self.logger.error(error_msg, extra={"status": "dir_creation_failed"})
            raise PDFDownloadError(error_msg)

    def _generate_safe_filename(self, url: str, document_title: Optional[str] = None) -> str:
        """
        Generate safe filename from URL and optional title.

        Args:
            url: PDF URL
            document_title: Optional document title for more meaningful filename

        Returns:
            Safe filename with .pdf extension

        Security Notes:
            - Removes path traversal attempts (../)
            - Sanitizes special characters
            - Limits filename length to 200 chars
            - Falls back to URL-based naming if title unavailable
        """
        # Extract filename from URL
        parsed = urlparse(url)
        path_parts = parsed.path.split("/")
        url_filename = unquote(path_parts[-1]) if path_parts else "document"

        # Use document title if available, otherwise use URL filename
        if document_title:
            # Sanitize title: remove special chars, limit length
            safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in document_title)
            safe_title = safe_title.strip().replace(" ", "_")[:150]
            base_name = safe_title
        else:
            # Sanitize URL filename
            base_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in url_filename)
            base_name = base_name.strip()[:150]

        # Remove path traversal attempts
        base_name = base_name.replace("..", "").replace("/", "_").replace("\\", "_")

        # Ensure .pdf extension
        if not base_name.lower().endswith(".pdf"):
            base_name = f"{base_name}.pdf"

        # Add timestamp prefix to avoid collisions
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{base_name}"

        return filename

    def _validate_pdf(self, file_path: str) -> bool:
        """
        Validate PDF file format and size.

        Args:
            file_path: Path to downloaded file

        Returns:
            True if valid PDF, False otherwise

        Validation checks:
            1. File exists and is readable
            2. File size > 0 and < max_pdf_size_mb
            3. File starts with PDF magic bytes (%PDF)
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                self.logger.warning(f"File does not exist: {file_path}")
                return False

            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb == 0:
                self.logger.warning(f"File is empty: {file_path}")
                return False

            if file_size_mb > self.config.max_pdf_size_mb:
                self.logger.warning(
                    f"File too large: {file_size_mb:.2f}MB > {self.config.max_pdf_size_mb}MB",
                    extra={"file_path": file_path, "size_mb": file_size_mb},
                )
                return False

            # Check PDF magic bytes
            with open(file_path, "rb") as f:
                header = f.read(len(self.PDF_MAGIC_BYTES))
                if not header.startswith(self.PDF_MAGIC_BYTES):
                    self.logger.warning(
                        f"File is not a valid PDF (missing magic bytes): {file_path}",
                        extra={"file_path": file_path},
                    )
                    return False

            self.logger.debug(
                f"PDF validation passed: {file_path} ({file_size_mb:.2f}MB)",
                extra={"file_path": file_path, "size_mb": file_size_mb},
            )
            return True

        except Exception as e:
            self.logger.error(
                f"PDF validation error: {e}",
                extra={"file_path": file_path, "status": "validation_error"},
            )
            return False

    def _compute_file_hash(self, file_path: str) -> str:
        """
        Compute SHA-256 hash of file for deduplication.

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.error(
                f"Failed to compute file hash: {e}",
                extra={"file_path": file_path, "status": "hash_error"},
            )
            raise PDFDownloadError(f"Failed to compute file hash: {e}")

    def download_pdf(
        self,
        url: str,
        document_title: Optional[str] = None,
        base_url: str = "https://www.mas.gov.sg",
    ) -> tuple[Optional[str], Optional[str], Optional[datetime]]:
        """
        Download PDF with retry logic and validation.

        Args:
            url: PDF URL (can be relative or absolute)
            document_title: Optional document title for filename
            base_url: Base URL to resolve relative URLs

        Returns:
            Tuple of (file_path, file_hash, download_timestamp) or (None, None, None) if failed

        Retry Strategy:
            - 3 attempts with exponential backoff (1s, 2s, 4s)
            - Retries on HTTP errors, timeouts, validation failures
            - Logs each attempt for audit trail
        """
        # Resolve relative URLs
        if url.startswith("/"):
            full_url = f"{base_url}{url}"
        elif url.startswith("http"):
            full_url = url
        else:
            full_url = f"{base_url}/{url}"

        # Generate safe filename
        filename = self._generate_safe_filename(full_url, document_title)
        file_path = os.path.join(self.config.download_dir, filename)

        # Retry logic: 3 attempts with exponential backoff
        backoff_delays = [1, 2, 4]  # seconds
        max_attempts = self.config.retry_max_attempts

        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(
                    f"Downloading PDF (attempt {attempt}/{max_attempts}): {full_url}",
                    extra={
                        "status": "download_attempt",
                        "attempt": attempt,
                        "url": full_url,
                    },
                )

                # Download PDF
                response = self.session.get(
                    full_url,
                    timeout=self.config.pdf_timeout,
                    stream=True,  # Stream for large files
                )
                response.raise_for_status()

                # Write to file
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Validate PDF
                if not self._validate_pdf(file_path):
                    raise PDFDownloadError(f"Downloaded file failed validation: {file_path}")

                # Compute hash
                file_hash = self._compute_file_hash(file_path)
                download_timestamp = datetime.now(timezone.utc)

                # Success!
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                self.logger.info(
                    f"Successfully downloaded PDF: {filename} ({file_size_mb:.2f}MB)",
                    extra={
                        "status": "download_success",
                        "file_path": file_path,
                        "file_hash": file_hash,
                        "size_mb": file_size_mb,
                        "attempt": attempt,
                    },
                )

                return (file_path, file_hash, download_timestamp)

            except Exception as e:
                error_msg = f"Download attempt {attempt} failed: {e}"
                self.logger.warning(
                    error_msg,
                    extra={
                        "status": "download_failed",
                        "attempt": attempt,
                        "url": full_url,
                        "error": str(e),
                    },
                )

                # Clean up partial download
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to clean up partial download: {cleanup_error}")

                # Retry with backoff (unless last attempt)
                if attempt < max_attempts:
                    delay = backoff_delays[attempt - 1]
                    self.logger.info(
                        f"Retrying in {delay}s...",
                        extra={"status": "retry_backoff", "delay_seconds": delay},
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All {max_attempts} download attempts failed for: {full_url}",
                        extra={"status": "download_failed_all_attempts", "url": full_url},
                    )

        # All attempts failed
        return (None, None, None)
