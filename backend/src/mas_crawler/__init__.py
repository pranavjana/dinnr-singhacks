"""
MAS AML/CFT Document Crawler

A Python library for discovering, downloading, and processing regulatory guidance documents
from the Monetary Authority of Singapore (MAS) website.
"""

__version__ = "0.1.0"
__author__ = "DINNR Team"

from .models import Category, Document, CrawlSession, CrawlResult
from .config import Config
from .logger import setup_logging

__all__ = [
    "Category",
    "Document",
    "CrawlSession",
    "CrawlResult",
    "Config",
    "setup_logging",
]
