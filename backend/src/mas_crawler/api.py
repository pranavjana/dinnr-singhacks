"""FastAPI endpoint wrapper for MAS crawler.

Provides HTTP REST API for triggering crawls and retrieving results.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .config import Config
from .logger import setup_logging
from .models import CrawlResult, CrawlSession, Document
from .scraper import MASCrawler


# ==================== Request/Response Models ====================


class CrawlRequest(BaseModel):
    """Request parameters for the crawl endpoint."""

    days_back: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Number of days to look back for recent documents (1-365)",
    )
    include_pdfs: bool = Field(
        default=True,
        description="Whether to download PDFs for discovered documents",
    )
    download_dir: Optional[str] = Field(
        default=None,
        description="Custom directory to download PDFs (default: from config)",
    )
    max_pdf_size_mb: Optional[int] = Field(
        default=None,
        ge=1,
        le=500,
        description="Maximum PDF file size in MB (1-500)",
    )
    max_pdfs: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of PDFs to download",
    )

    class Config:
        """Pydantic config for request model."""

        json_schema_extra = {
            "example": {
                "days_back": 90,
                "include_pdfs": True,
                "download_dir": None,
                "max_pdf_size_mb": None,
                "max_pdfs": None,
            }
        }


class CrawlStatusResponse(BaseModel):
    """Response for status endpoint."""

    session_id: str = Field(..., description="Unique crawl session ID")
    status: str = Field(..., description="Status: pending, in_progress, completed, failed")
    message: Optional[str] = Field(None, description="Status message")
    result: Optional[CrawlResult] = Field(None, description="Crawl result if completed")


# ==================== FastAPI App Setup ====================


def create_app(config: Optional[Config] = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        config: Optional Config object (if None, loads from environment)

    Returns:
        FastAPI application instance
    """
    # Load config from environment if not provided
    if config is None:
        config = Config.from_env()

    # Setup logging
    logger = setup_logging(log_level=config.log_level)
    logger.info("Initializing FastAPI application")

    # Create FastAPI app
    app = FastAPI(
        title="MAS AML/CFT Document Crawler API",
        description="REST API for discovering and downloading MAS AML/CFT documents",
        version="1.0.0",
    )

    # Store config and logger in app state for dependency injection
    app.state.config = config
    app.state.logger = logger
    app.state.crawler = MASCrawler(config)
    app.state.crawl_sessions: dict = {}  # In-memory session storage

    # ==================== API Endpoints ====================

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/api/v1/crawl")
    async def start_crawl(request: CrawlRequest = None):
        """
        Trigger a crawl of MAS website and optionally download PDFs.

        Args:
            request: CrawlRequest with optional parameters

        Returns:
            CrawlResult with discovered documents and metadata

        Raises:
            HTTPException: 400 for invalid parameters, 500 for crawl errors
        """
        if request is None:
            request = CrawlRequest()

        try:
            logger = app.state.logger
            config = app.state.config
            crawler = app.state.crawler

            # Override config if parameters provided
            if request.download_dir:
                config.download_dir = request.download_dir
            if request.max_pdf_size_mb:
                config.max_pdf_size_mb = request.max_pdf_size_mb

            logger.info(
                f"Starting crawl with parameters: days_back={request.days_back}, "
                f"include_pdfs={request.include_pdfs}",
                extra={
                    "status": "crawl_requested",
                    "details": {
                        "days_back": request.days_back,
                        "include_pdfs": request.include_pdfs,
                    },
                },
            )

            # Execute crawl
            crawl_result = crawler.crawl(
                days_back=request.days_back,
                max_pdfs=request.max_pdfs if request.include_pdfs else 0,
            )

            # Store session for status checking
            app.state.crawl_sessions[crawl_result.session.session_id] = crawl_result

            logger.info(
                f"Crawl completed: {crawl_result.session.session_id}",
                extra={
                    "status": "crawl_completed",
                    "details": {
                        "session_id": crawl_result.session.session_id,
                        "documents_found": crawl_result.session.documents_found,
                        "documents_downloaded": crawl_result.session.documents_downloaded,
                    },
                },
            )

            return crawl_result

        except ValueError as e:
            logger = app.state.logger
            error_msg = f"Invalid request parameters: {str(e)}"
            logger.error(error_msg, extra={"status": "validation_error"})
            raise HTTPException(status_code=400, detail=error_msg)

        except Exception as e:
            logger = app.state.logger
            error_msg = f"Crawl failed: {str(e)}"
            logger.error(
                error_msg,
                extra={"status": "crawl_error", "details": {"error": str(e)}},
            )
            raise HTTPException(status_code=500, detail=error_msg)

    @app.get("/api/v1/crawl/status/{session_id}")
    async def get_crawl_status(session_id: str):
        """
        Retrieve status and result of a crawl session.

        Args:
            session_id: Unique session ID from crawl response

        Returns:
            CrawlStatusResponse with status and result (if completed)

        Raises:
            HTTPException: 404 if session not found
        """
        try:
            if session_id not in app.state.crawl_sessions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found",
                )

            result = app.state.crawl_sessions[session_id]

            return CrawlStatusResponse(
                session_id=session_id,
                status="completed",
                message="Crawl completed successfully",
                result=result,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger = app.state.logger
            error_msg = f"Failed to retrieve status: {str(e)}"
            logger.error(
                error_msg,
                extra={"status": "status_error", "details": {"error": str(e)}},
            )
            raise HTTPException(status_code=500, detail=error_msg)

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = Config.from_env()
    app = create_app(config)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower(),
    )
