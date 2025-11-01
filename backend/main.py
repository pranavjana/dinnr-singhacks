"""
FastAPI application entry point for Payment History Analysis Tool.

This module initializes the FastAPI app with:
- CORS configuration
- Health check endpoint
- Payment history router
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health, payment_history

# Initialize FastAPI app
app = FastAPI(
    title="Payment History Analysis API",
    description="AML compliance tool for querying payment history and performing LLM-powered risk analysis",
    version="1.0.0",
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["System"])
app.include_router(payment_history.router, prefix="/api", tags=["Payment History"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Payment History Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
