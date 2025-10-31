"""Main scraper logic for MAS website."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .config import Config
from .errors import HTTPError, ParseError, RobotsViolation
from .logger import setup_logging
from .models import Category, CrawlResult, CrawlSession, Document
from .pdf_downloader import PDFDownloader


class MASCrawler:
    """Main crawler for MAS AML/CFT documents."""

    # MAS website URLs
    BASE_URL = "https://www.mas.gov.sg"
    NEWS_URL = f"{BASE_URL}/news/media-releases"
    CIRCULARS_URL = f"{BASE_URL}/regulation/circulars"
    NOTICES_URL = f"{BASE_URL}/regulation/notices"
    # Regulations and Guidance page filtered for AML/CFT + Banking
    REGULATIONS_GUIDANCE_URL = f"{BASE_URL}/regulation/regulations-and-guidance?topics=Anti-Money%20Laundering&sectors=Banking"
    REGULATION_URL = f"{BASE_URL}/regulation/regulations"
    ROBOTS_URL = f"{BASE_URL}/robots.txt"

    # Search API endpoint (v1)
    SEARCH_API = "https://www.mas.gov.sg/api/v1/search"

    def __init__(self, config: Config):
        """
        Initialize MAS crawler.

        Args:
            config: Configuration object with crawler settings
        """
        self.config = config
        self.logger = setup_logging(log_level=config.log_level)
        self.session = requests.Session()

        # Set headers for API and HTTP requests
        # Note: API requires a Chrome/browser User-Agent, not a bot UA
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.mas.gov.sg/regulation/regulations-and-guidance",
        })

        self.robots_parser: Optional[RobotFileParser] = None
        self._init_robots_parser()

    def _init_robots_parser(self) -> None:
        """Initialize robots.txt parser."""
        try:
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(self.ROBOTS_URL)
            self.robots_parser.read()
            self.logger.info("Successfully loaded robots.txt rules")
        except Exception as e:
            self.logger.warning(
                f"Failed to load robots.txt: {e}. Will proceed without robot restrictions."
            )
            self.robots_parser = None

    def _check_robots_allowed(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed or no robots.txt loaded, False otherwise
        """
        if self.robots_parser is None:
            return True

        allowed = self.robots_parser.can_fetch(self.config.user_agent, url)
        if not allowed:
            self.logger.warning(
                f"URL blocked by robots.txt: {url}",
                extra={"document_url": url, "status": "robots_blocked"},
            )
        return allowed

    def fetch_page(self, url: str, timeout: Optional[int] = None) -> str:
        """
        Fetch HTML page with retry logic.

        Args:
            url: URL to fetch
            timeout: Optional timeout override (uses config default if not provided)

        Returns:
            HTML content as string

        Raises:
            HTTPError: If all retry attempts fail
            RobotsViolation: If URL is blocked by robots.txt
        """
        if not self._check_robots_allowed(url):
            raise RobotsViolation(f"URL blocked by robots.txt: {url}")

        timeout = timeout or self.config.request_timeout
        last_error = None

        for attempt in range(1, self.config.retry_max_attempts + 1):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()

                self.logger.info(
                    f"Successfully fetched page: {url}",
                    extra={"document_url": url, "status": "fetch_success"},
                )
                return response.text

            except requests.exceptions.RequestException as e:
                last_error = e
                self.logger.warning(
                    f"Fetch attempt {attempt}/{self.config.retry_max_attempts} failed for {url}: {e}",
                    extra={
                        "document_url": url,
                        "status": "fetch_retry",
                        "details": {
                            "attempt": attempt,
                            "max_attempts": self.config.retry_max_attempts,
                            "error": str(e),
                        },
                    },
                )

                if attempt < self.config.retry_max_attempts:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff_time = 2 ** (attempt - 1)
                    time.sleep(backoff_time)

        # All retries failed
        error_msg = f"Failed to fetch {url} after {self.config.retry_max_attempts} attempts: {last_error}"
        self.logger.error(
            error_msg,
            extra={"document_url": url, "status": "fetch_failed"},
        )
        raise HTTPError(error_msg)

    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse date string to datetime object.

        Args:
            date_string: Date string in various formats

        Returns:
            Datetime object in UTC, or None if parsing fails
        """
        if not date_string or not date_string.strip():
            return None

        try:
            # Use dateutil parser for flexible date parsing
            dt = date_parser.parse(date_string)

            # Convert to UTC if naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            return dt
        except Exception as e:
            self.logger.warning(
                f"Failed to parse date: '{date_string}': {e}",
                extra={"status": "date_parse_error", "details": {"date_string": date_string}},
            )
            return None

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL (lowercase, no query params/fragments)
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

    def _is_recent(self, publication_date: Optional[datetime], days_back: int = 90) -> bool:
        """
        Check if document is within recency window.

        Args:
            publication_date: Document publication date
            days_back: Number of days to look back (default: 90)

        Returns:
            True if document is recent, False otherwise
        """
        if publication_date is None:
            # If no date, include it (pragmatic approach)
            return True

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        return publication_date >= cutoff_date

    def parse_news_page(self, html: str) -> List[Document]:
        """
        Parse News section page to extract documents.

        Args:
            html: HTML content of news page

        Returns:
            List of Document objects

        Note:
            This is a simplified parser. In production, CSS selectors would be
            determined by inspecting the actual MAS website structure.
        """
        soup = BeautifulSoup(html, "html.parser")
        documents = []

        try:
            # PLACEHOLDER: Adjust selectors based on actual MAS website structure
            # This is a generic pattern that would need to be customized
            articles = soup.find_all("article") or soup.find_all("div", class_="news-item")

            for article in articles:
                try:
                    # Extract title
                    title_elem = article.find(["h2", "h3", "a"])
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    link_elem = article.find("a", href=True)
                    if not link_elem:
                        continue
                    source_url = urljoin(self.NEWS_URL, link_elem["href"])

                    # Extract date (if available)
                    date_elem = article.find(["time", "span"], class_=["date", "published"])
                    publication_date = None
                    if date_elem:
                        date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                        publication_date = self._parse_date(date_text)

                    # Create document
                    doc = Document(
                        title=title,
                        publication_date=publication_date,
                        category=Category.NEWS,
                        source_url=source_url,
                        normalized_url=self._normalize_url(source_url),
                        data_quality_notes="publication_date not found" if publication_date is None else None,
                    )
                    documents.append(doc)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse news article: {e}",
                        extra={"status": "parse_warning"},
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"Failed to parse news page: {e}",
                extra={"status": "parse_error"},
            )
            raise ParseError(f"Failed to parse news page: {e}")

        self.logger.info(
            f"Parsed {len(documents)} documents from News section",
            extra={"status": "parse_success", "details": {"count": len(documents)}},
        )
        return documents

    def parse_circulars_page(self, html: str) -> List[Document]:
        """
        Parse Circulars section page to extract documents.

        Args:
            html: HTML content of circulars page

        Returns:
            List of Document objects
        """
        soup = BeautifulSoup(html, "html.parser")
        documents = []

        try:
            # PLACEHOLDER: Adjust selectors based on actual MAS website structure
            # Looking for table rows or list items that contain circular information
            items = soup.find_all("tr") or soup.find_all("li", class_="circular-item")

            for item in items:
                try:
                    # Extract title
                    title_elem = item.find(["a", "td", "span"])
                    if not title_elem or not title_elem.get_text(strip=True):
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    link_elem = item.find("a", href=True)
                    if not link_elem:
                        continue
                    source_url = urljoin(self.CIRCULARS_URL, link_elem["href"])

                    # Extract date
                    date_elem = item.find(["time", "td", "span"], class_=["date", "published"])
                    publication_date = None
                    if date_elem:
                        date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                        publication_date = self._parse_date(date_text)

                    # Create document
                    doc = Document(
                        title=title,
                        publication_date=publication_date,
                        category=Category.CIRCULAR,
                        source_url=source_url,
                        normalized_url=self._normalize_url(source_url),
                        data_quality_notes="publication_date not found" if publication_date is None else None,
                    )
                    documents.append(doc)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse circular item: {e}",
                        extra={"status": "parse_warning"},
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"Failed to parse circulars page: {e}",
                extra={"status": "parse_error"},
            )
            raise ParseError(f"Failed to parse circulars page: {e}")

        self.logger.info(
            f"Parsed {len(documents)} documents from Circulars section",
            extra={"status": "parse_success", "details": {"count": len(documents)}},
        )
        return documents

    def fetch_aml_documents_from_api(self) -> List[dict]:
        """
        Fetch AML/CFT documents from MAS search API (v1).

        Filters for:
        - Topic: Anti-Money Laundering
        - Sector: Banking
        - Type: Regulatory Instrument

        Returns:
            List of document objects from API response
        """
        try:
            # Build parameters with AML filter
            # Using list of tuples to allow multiple 'fq' parameters
            params = [
                ("json.nl", "map"),
                ("q", "*:*"),
                ("fq", "{!tag=topic_path}topic_path:\"Anti-Money Laundering\""),
                ("fq", "{!tag=mas_sector_sm}mas_sector_sm:(\"Banking\")"),
                ("sort", "mas_date_tdt desc"),
                ("rows", "100"),
            ]

            response = self.session.get(self.SEARCH_API, params=params, timeout=self.config.request_timeout)
            response.raise_for_status()

            # Check if response is valid JSON
            if not response.text or response.text.startswith("<!"):
                self.logger.error(
                    f"API returned non-JSON response ({len(response.text)} bytes)",
                    extra={"status": "api_error"},
                )
                return []

            data = response.json()

            # The API response has a 'response' key containing 'docs'
            response_data = data.get("response", {})
            docs = response_data.get("docs", [])

            num_found = response_data.get("numFound", 0)

            self.logger.info(
                f"Fetched {len(docs)} documents from API",
                extra={
                    "status": "api_success",
                    "details": {
                        "count": len(docs),
                        "num_found": num_found,
                        "filters": "AML + Banking + Regulatory Instruments",
                    },
                },
            )

            return docs

        except Exception as e:
            self.logger.error(
                f"Failed to fetch documents from API: {e}",
                extra={"status": "api_error", "details": {"error": str(e)}},
            )
            return []

    def extract_notice_documents(self, api_docs: List[dict]) -> List[Document]:
        """
        Extract Document objects from MAS search API response.

        Args:
            api_docs: List of documents from API response

        Returns:
            List of Document objects
        """
        documents = []

        for doc in api_docs:
            try:
                # Extract fields from API response (Solr format)
                title = doc.get("document_title_string_s") or doc.get("navigation_title_string_s", "")
                page_url = doc.get("page_url_s", "")

                if not title or not page_url:
                    continue

                # Construct full URL
                full_url = urljoin(self.BASE_URL, page_url)

                # Extract date from mas_date_tdt (ISO-8601 format)
                publication_date = None
                if "mas_date_tdt" in doc:
                    publication_date = self._parse_date(doc["mas_date_tdt"])

                # Determine category based on content type
                content_type = doc.get("mas_contenttype_s", "")
                if "Notice" in content_type:
                    category = Category.CIRCULAR  # Notices are regulatory circulars
                elif "Circular" in content_type:
                    category = Category.CIRCULAR
                elif "Regulation" in content_type or "Guidance" in content_type or "Guideline" in content_type:
                    category = Category.REGULATION
                else:
                    category = Category.CIRCULAR  # Default

                # Create document
                document = Document(
                    title=title,
                    publication_date=publication_date,
                    category=category,
                    source_url=full_url,
                    normalized_url=self._normalize_url(full_url),
                    data_quality_notes="publication_date not found" if publication_date is None else None,
                )

                documents.append(document)

            except Exception as e:
                self.logger.warning(
                    f"Failed to extract document from API response: {e}",
                    extra={"status": "extraction_error", "details": {"error": str(e)}},
                )
                continue

        self.logger.info(
            f"Extracted {len(documents)} valid documents from API",
            extra={"status": "extraction_success", "details": {"count": len(documents)}},
        )

        return documents

    def parse_regulation_page(self, html: str) -> List[Document]:
        """
        Parse Regulation section page to extract documents.

        Args:
            html: HTML content of regulation page

        Returns:
            List of Document objects
        """
        soup = BeautifulSoup(html, "html.parser")
        documents = []

        try:
            # PLACEHOLDER: Adjust selectors based on actual MAS website structure
            items = soup.find_all("div", class_="regulation-item") or soup.find_all("article")

            for item in items:
                try:
                    # Extract title
                    title_elem = item.find(["h2", "h3", "a", "strong"])
                    if not title_elem or not title_elem.get_text(strip=True):
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    link_elem = item.find("a", href=True)
                    if not link_elem:
                        continue
                    source_url = urljoin(self.REGULATION_URL, link_elem["href"])

                    # Extract date
                    date_elem = item.find(["time", "span"], class_=["date", "published", "updated"])
                    publication_date = None
                    if date_elem:
                        date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                        publication_date = self._parse_date(date_text)

                    # Create document
                    doc = Document(
                        title=title,
                        publication_date=publication_date,
                        category=Category.REGULATION,
                        source_url=source_url,
                        normalized_url=self._normalize_url(source_url),
                        data_quality_notes="publication_date not found" if publication_date is None else None,
                    )
                    documents.append(doc)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse regulation item: {e}",
                        extra={"status": "parse_warning"},
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"Failed to parse regulation page: {e}",
                extra={"status": "parse_error"},
            )
            raise ParseError(f"Failed to parse regulation page: {e}")

        self.logger.info(
            f"Parsed {len(documents)} documents from Regulation section",
            extra={"status": "parse_success", "details": {"count": len(documents)}},
        )
        return documents

    def extract_pdf_links_from_page(self, page_url: str) -> List[str]:
        """
        Extract PDF links from a notice/document page.

        Args:
            page_url: URL of the document page to scrape

        Returns:
            List of PDF URLs found on the page (can be empty if none found)

        Note:
            Based on debug analysis, MAS notice pages contain <a> tags
            with href ending in .pdf for PDF downloads.
        """
        try:
            # Fetch the page
            html = self.fetch_page(page_url)
            soup = BeautifulSoup(html, "html.parser")

            # Strategy: Find all <a> tags with href ending in .pdf
            pdf_links = soup.find_all("a", href=lambda x: x and x.lower().endswith(".pdf"))

            pdf_urls = []
            for link in pdf_links:
                href = link.get("href")
                if href:
                    # Convert relative URLs to absolute
                    full_url = urljoin(page_url, href)
                    pdf_urls.append(full_url)

            self.logger.info(
                f"Found {len(pdf_urls)} PDF link(s) on page: {page_url}",
                extra={
                    "status": "pdf_extraction_success",
                    "page_url": page_url,
                    "pdf_count": len(pdf_urls),
                },
            )

            return pdf_urls

        except Exception as e:
            self.logger.warning(
                f"Failed to extract PDF links from {page_url}: {e}",
                extra={"status": "pdf_extraction_failed", "page_url": page_url},
            )
            return []

    def crawl(self, days_back: int = 90, max_pdfs: Optional[int] = None) -> CrawlResult:
        """
        Execute full crawl of MAS website.

        Args:
            days_back: Number of days to look back for recent documents (default: 90)
            max_pdfs: Maximum number of PDFs to download (default: None = unlimited)

        Returns:
            CrawlResult with session metadata and discovered documents
        """
        # Initialize session
        session_id = f"crawl_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now(timezone.utc)

        session = CrawlSession(
            session_id=session_id,
            start_time=start_time,
            crawl_config={
                "days_back": days_back,
                "user_agent": self.config.user_agent,
                "request_timeout": self.config.request_timeout,
            },
        )

        self.logger.info(
            f"Starting crawl session: {session_id}",
            extra={
                "status": "session_started",
                "details": {"session_id": session_id, "config": session.crawl_config},
            },
        )

        all_documents: List[Document] = []
        errors: List[str] = []

        # Fetch AML/CFT documents from API (primary method - filtered for Banking sector)
        try:
            api_docs = self.fetch_aml_documents_from_api()
            aml_docs = self.extract_notice_documents(api_docs)
            all_documents.extend(aml_docs)
        except Exception as e:
            error_msg = f"Failed to fetch AML documents from API: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg, extra={"status": "section_failed"})

        # Fallback: Crawl News section (if API doesn't work)
        try:
            html = self.fetch_page(self.NEWS_URL)
            news_docs = self.parse_news_page(html)
            all_documents.extend(news_docs)
        except Exception as e:
            error_msg = f"Failed to crawl News section: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg, extra={"status": "section_failed"})

        # Fallback: Crawl Circulars section
        try:
            html = self.fetch_page(self.CIRCULARS_URL)
            circulars_docs = self.parse_circulars_page(html)
            all_documents.extend(circulars_docs)
        except Exception as e:
            error_msg = f"Failed to crawl Circulars section: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg, extra={"status": "section_failed"})

        # Fallback: Crawl Regulation section
        try:
            html = self.fetch_page(self.REGULATION_URL)
            regulation_docs = self.parse_regulation_page(html)
            all_documents.extend(regulation_docs)
        except Exception as e:
            error_msg = f"Failed to crawl Regulation section: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg, extra={"status": "section_failed"})

        # Filter by recency (90-day window)
        recent_documents = [
            doc for doc in all_documents if self._is_recent(doc.publication_date, days_back)
        ]

        skipped_count = len(all_documents) - len(recent_documents)
        if skipped_count > 0:
            self.logger.info(
                f"Filtered out {skipped_count} documents outside {days_back}-day window",
                extra={"status": "filtered", "details": {"skipped_count": skipped_count}},
            )

        # Download PDFs for recent documents
        pdf_downloader = PDFDownloader(self.config)
        documents_downloaded = 0

        for doc in recent_documents:
            # Check if we've reached the PDF download limit
            if max_pdfs is not None and documents_downloaded >= max_pdfs:
                self.logger.info(
                    f"Reached max PDF download limit ({max_pdfs}), stopping downloads",
                    extra={"status": "max_pdfs_reached", "max_pdfs": max_pdfs},
                )
                break

            try:
                # Extract PDF links from the document page
                # Convert HttpUrl to string for processing
                pdf_urls = self.extract_pdf_links_from_page(str(doc.source_url))

                if not pdf_urls:
                    self.logger.info(
                        f"No PDF links found for document: {doc.title}",
                        extra={"status": "no_pdfs", "document_url": doc.source_url},
                    )
                    continue

                # Download the first PDF found (typically the main document)
                # Future enhancement: Could download all PDFs if needed
                pdf_url = pdf_urls[0]
                file_path, file_hash, download_timestamp = pdf_downloader.download_pdf(
                    pdf_url,
                    document_title=doc.title,
                )

                # Update document with download info if successful
                if file_path:
                    doc.downloaded_pdf_path = file_path
                    doc.file_hash = file_hash
                    doc.download_timestamp = download_timestamp
                    documents_downloaded += 1
                else:
                    self.logger.warning(
                        f"Failed to download PDF for: {doc.title}",
                        extra={"status": "pdf_download_failed", "pdf_url": pdf_url},
                    )

            except Exception as e:
                self.logger.error(
                    f"Error processing PDFs for {doc.title}: {e}",
                    extra={"status": "pdf_processing_error", "document_url": doc.source_url},
                )
                # Continue with other documents (graceful degradation)
                continue

        self.logger.info(
            f"Downloaded {documents_downloaded} PDFs out of {len(recent_documents)} documents",
            extra={
                "status": "pdf_download_complete",
                "details": {
                    "total_documents": len(recent_documents),
                    "pdfs_downloaded": documents_downloaded,
                },
            },
        )

        # Finalize session
        end_time = datetime.now(timezone.utc)
        session.end_time = end_time
        session.duration_seconds = (end_time - start_time).total_seconds()
        session.documents_found = len(all_documents)
        session.documents_downloaded = documents_downloaded
        session.documents_skipped = skipped_count
        session.errors_encountered = len(errors)
        session.errors_details = errors
        session.success = len(errors) < len([self.NEWS_URL, self.CIRCULARS_URL, self.REGULATION_URL])

        self.logger.info(
            f"Crawl session completed: {session_id}",
            extra={
                "status": "session_completed",
                "details": {
                    "session_id": session_id,
                    "documents_found": session.documents_found,
                    "documents_downloaded": session.documents_downloaded,
                    "documents_skipped": session.documents_skipped,
                    "errors_encountered": session.errors_encountered,
                    "success": session.success,
                },
            },
        )

        return CrawlResult(session=session, documents=recent_documents)
