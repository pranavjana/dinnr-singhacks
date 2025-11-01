"""
Analysis result models for LLM-powered risk analysis.

Contains Pydantic models for structured LLM output per FR-014.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class FlaggedTransaction(BaseModel):
    """Individual transaction flagged during analysis."""

    transaction_id: str = Field(..., description="Transaction ID from CSV")
    reason: str = Field(..., description="Why this transaction was flagged")
    risk_level: str = Field(..., description="Low/Medium/High/Critical")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
                "reason": "Round-number amount to high-risk jurisdiction",
                "risk_level": "High",
            }
        }


class IdentifiedPattern(BaseModel):
    """Pattern detected across transactions."""

    pattern_type: str = Field(
        ...,
        description="Type: volume_spike/round_amounts/high_risk_jurisdiction/similar_names/etc.",
    )
    description: str = Field(..., description="Human-readable pattern description")
    affected_transactions: list[str] = Field(
        ..., description="Transaction IDs exhibiting this pattern"
    )
    severity: str = Field(..., description="Low/Medium/High")

    class Config:
        json_schema_extra = {
            "example": {
                "pattern_type": "round_amounts",
                "description": "Multiple transactions with round-number amounts (structuring indicator)",
                "affected_transactions": [
                    "ad66338d-b17f-47fc-a966-1b4395351b41",
                    "f72e3c4a-8b91-4d5f-9a2e-6c1b7d3e8f4a",
                ],
                "severity": "High",
            }
        }


class AnalysisResult(BaseModel):
    """
    Structured JSON output from LLM analysis (FR-014).
    Returned by /api/payment-history/analyze endpoint.
    """

    # Risk assessment
    overall_risk_score: float | None = Field(
        None,
        description="Numeric risk score (0-10 scale), null if analysis failed",
        ge=0,
        le=10,
    )
    risk_category: str | None = Field(
        None,
        description="Overall category: Low/Medium/High/Critical, null if analysis failed",
    )

    # Flagged items
    flagged_transactions: list[FlaggedTransaction] = Field(
        default_factory=list, description="Transactions flagged as suspicious"
    )

    # Patterns
    identified_patterns: list[IdentifiedPattern] = Field(
        default_factory=list, description="Patterns detected across payment history"
    )

    # Summary
    narrative_summary: str = Field(
        ..., description="Human-readable explanation of findings"
    )

    # Metadata
    analyzed_transaction_count: int = Field(
        ..., description="Number of transactions analyzed", ge=0
    )
    analysis_timestamp: datetime = Field(..., description="When analysis was performed")

    # Error handling (FR-018)
    error: str | None = Field(
        None,
        description="Error message if LLM unavailable (graceful degradation)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "overall_risk_score": 7.5,
                "risk_category": "High",
                "flagged_transactions": [
                    {
                        "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
                        "reason": "Round-number amount to high-risk jurisdiction",
                        "risk_level": "High",
                    }
                ],
                "identified_patterns": [
                    {
                        "pattern_type": "round_amounts",
                        "description": "Multiple transactions with round-number amounts (structuring indicator)",
                        "affected_transactions": [
                            "ad66338d-b17f-47fc-a966-1b4395351b41",
                            "f72e3c4a-8b91-4d5f-9a2e-6c1b7d3e8f4a",
                        ],
                        "severity": "High",
                    }
                ],
                "narrative_summary": "Analysis detected potential structuring behavior with multiple round-number transactions to high-risk jurisdictions.",
                "analyzed_transaction_count": 25,
                "analysis_timestamp": "2025-11-01T12:00:00Z",
                "error": None,
            }
        }
