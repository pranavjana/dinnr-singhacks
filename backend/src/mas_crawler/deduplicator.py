"""Duplicate detection using normalized URLs and file hashes."""

from typing import Set, Tuple
from urllib.parse import urlparse, urlunparse


class Deduplicator:
    """
    Handles duplicate detection for documents.

    Uses a hybrid approach:
    1. Normalized URLs for initial detection
    2. File hashes for content-based deduplication
    """

    def __init__(self):
        """Initialize deduplicator with empty tracking sets."""
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication.

        Removes query parameters, fragments, and converts to lowercase.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            "",  # Remove params
            "",  # Remove query
            "",  # Remove fragment
        ))
        return normalized

    def is_duplicate_url(self, url: str) -> bool:
        """
        Check if URL has been seen before.

        Args:
            url: URL to check

        Returns:
            True if URL is a duplicate, False otherwise
        """
        normalized = self.normalize_url(url)
        return normalized in self.seen_urls

    def is_duplicate_hash(self, file_hash: str) -> bool:
        """
        Check if file hash has been seen before.

        Args:
            file_hash: SHA-256 hash to check

        Returns:
            True if hash is a duplicate, False otherwise
        """
        return file_hash in self.seen_hashes

    def add_document(self, normalized_url: str, file_hash: str = None) -> None:
        """
        Register a document as seen.

        Args:
            normalized_url: Normalized URL of document
            file_hash: Optional SHA-256 hash of document content
        """
        self.seen_urls.add(normalized_url)
        if file_hash:
            self.seen_hashes.add(file_hash)

    def check_and_add(self, url: str, file_hash: str = None) -> Tuple[bool, str]:
        """
        Check if document is duplicate and add if not.

        Args:
            url: Document URL
            file_hash: Optional file hash

        Returns:
            Tuple of (is_duplicate: bool, reason: str)
        """
        normalized_url = self.normalize_url(url)

        # Check URL
        if normalized_url in self.seen_urls:
            return True, "duplicate_url"

        # Check hash (if provided)
        if file_hash and file_hash in self.seen_hashes:
            return True, "duplicate_hash"

        # Not a duplicate - add to tracking
        self.add_document(normalized_url, file_hash)
        return False, "unique"

    def get_stats(self) -> dict:
        """
        Get deduplication statistics.

        Returns:
            Dictionary with counts of seen URLs and hashes
        """
        return {
            "seen_urls": len(self.seen_urls),
            "seen_hashes": len(self.seen_hashes),
        }

    def clear(self) -> None:
        """Clear all tracking data."""
        self.seen_urls.clear()
        self.seen_hashes.clear()
