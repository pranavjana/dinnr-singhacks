"""
Data models for MAS crawler using Pydantic v2.

Defines entities for documents, crawl sessions, and results with validation rules.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator, model_validator


class Category(str, Enum):
    """Document source category from MAS website."""

    NEWS = "News"
    CIRCULAR = "Circular"
    REGULATION = "Regulation"


class Document(BaseModel):
    """Single MAS AML/CFT document metadata."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        use_enum_values=True,
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title as displayed on MAS website",
    )

    publication_date: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 publication date (UTC). None if not found on page.",
    )

    category: Category = Field(
        ...,
        description="Source section: News, Circular, or Regulation",
    )

    source_url: HttpUrl = Field(
        ...,
        description="Direct link to document on MAS website",
    )

    normalized_url: str = Field(
        ...,
        description="Normalized source_url (query params/fragments removed) for deduplication",
    )

    downloaded_pdf_path: Optional[str] = Field(
        default=None,
        description="Local filesystem path to downloaded PDF. None if download failed or unavailable.",
    )

    file_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of downloaded PDF (lowercase hex string). None if PDF not downloaded.",
    )

    download_timestamp: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 timestamp when PDF was successfully downloaded (UTC). None if not downloaded.",
    )

    data_quality_notes: Optional[str] = Field(
        default=None,
        description="Optional: Free-text notes on data completeness",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Validate title is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("normalized_url")
    @classmethod
    def normalized_url_lowercase(cls, v: str) -> str:
        """Normalize URL to lowercase for consistency."""
        return v.lower()

    @field_validator("file_hash")
    @classmethod
    def hash_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA-256 hash format if provided."""
        if v is not None:
            if not (len(v) == 64 and all(c in "0123456789abcdef" for c in v)):
                raise ValueError(
                    "file_hash must be 64-character lowercase hex string (SHA-256)"
                )
        return v

    @model_validator(mode="after")
    def downloaded_path_requires_hash(self) -> "Document":
        """If PDF was downloaded, hash must be present."""
        if self.downloaded_pdf_path is not None and self.file_hash is None:
            raise ValueError("file_hash must be set if downloaded_pdf_path is not null")
        return self


class CrawlSession(BaseModel):
    """Metadata and summary of a single crawl execution."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    session_id: str = Field(
        ...,
        description="Unique identifier (UUID or timestamp-based) for this crawl session",
    )

    start_time: datetime = Field(
        ...,
        description="ISO-8601 timestamp when crawl started (UTC)",
    )

    end_time: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 timestamp when crawl completed (UTC). None if in progress.",
    )

    duration_seconds: Optional[float] = Field(
        default=None,
        description="Total execution time in seconds. Calculated as end_time - start_time.",
    )

    documents_found: int = Field(
        default=0,
        ge=0,
        description="Total unique documents discovered on MAS website (before dedup)",
    )

    documents_downloaded: int = Field(
        default=0,
        ge=0,
        description="Number of PDFs successfully downloaded",
    )

    documents_skipped: int = Field(
        default=0,
        ge=0,
        description="Documents skipped (duplicates, robots.txt, missing fields, etc.)",
    )

    errors_encountered: int = Field(
        default=0,
        ge=0,
        description="Count of non-fatal errors (retries, missing fields, broken links)",
    )

    errors_details: List[str] = Field(
        default_factory=list,
        description="Log entries for errors (up to 100 most recent; summary of issues)",
    )

    success: bool = Field(
        default=False,
        description="True if crawl completed without fatal errors; False if halted early",
    )

    crawl_config: dict = Field(
        default_factory=dict,
        description="Configuration used for crawl (days_back, download_dir, retry_policy, etc.)",
    )


class CrawlResult(BaseModel):
    """Complete output of a crawl session: metadata + documents."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    session: CrawlSession = Field(
        ...,
        description="Crawl execution metadata and summary statistics",
    )

    documents: List[Document] = Field(
        default_factory=list,
        description="Array of documents discovered and processed in this crawl",
    )

    @classmethod
    def get_json_schema(cls) -> dict:
        """
        Generate JSON schema for CrawlResult model.

        Returns:
            dict: JSON schema compatible with OpenAPI/JSON Schema specifications
        """
        return cls.model_json_schema()

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize CrawlResult to JSON string with proper formatting.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)

        Returns:
            str: JSON-formatted string representation
        """
        return self.model_dump_json(indent=indent)

    def validate_schema(self) -> bool:
        """
        Validate that the current instance conforms to the JSON schema.

        Returns:
            bool: True if valid (raises ValidationError if not)
        """
        # Pydantic validates automatically on construction, but we can
        # re-validate by round-tripping through JSON
        json_str = self.model_dump_json()
        CrawlResult.model_validate_json(json_str)
        return True
