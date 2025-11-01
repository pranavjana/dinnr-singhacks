"""
Health check endpoint for system monitoring.

Provides basic health status and timestamp.
"""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Verifies API is running and responsive (<200ms target).

    Returns:
        dict: Health status and current timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
