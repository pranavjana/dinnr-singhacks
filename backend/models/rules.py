"""
Rules data models for regulatory compliance validation.

Placeholder structure for external team's rules data format.
Supports graceful degradation when rules unavailable (FR-012, FR-013).
"""

from decimal import Decimal
from pydantic import BaseModel, Field


class ThresholdRule(BaseModel):
    """Transaction threshold rule for compliance checks."""

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    threshold_amount: Decimal = Field(..., description="Threshold amount", ge=0)
    currency: str = Field(..., description="Currency code (USD, EUR, etc.)")
    time_period_days: int = Field(
        ..., description="Time period for aggregation (days)", ge=1
    )
    violation_severity: str = Field(..., description="Low/Medium/High/Critical")

    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "THR-001",
                "rule_name": "Daily cash transaction threshold",
                "threshold_amount": 10000.00,
                "currency": "USD",
                "time_period_days": 1,
                "violation_severity": "High",
            }
        }


class ProhibitedJurisdiction(BaseModel):
    """High-risk or prohibited jurisdiction for compliance checks."""

    country_code: str = Field(..., description="2-letter country code")
    country_name: str = Field(..., description="Full country name")
    risk_level: str = Field(..., description="Low/Medium/High/Critical")
    sanctions_list: str | None = Field(
        None, description="Sanctions list name (OFAC, UN, EU, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "country_code": "KP",
                "country_name": "North Korea",
                "risk_level": "Critical",
                "sanctions_list": "OFAC SDN",
            }
        }


class DocumentationRequirement(BaseModel):
    """Documentation requirements for specific transaction types."""

    requirement_id: str = Field(..., description="Unique requirement identifier")
    requirement_name: str = Field(..., description="Human-readable requirement name")
    applies_to_product_types: list[str] = Field(
        ..., description="Product types this applies to"
    )
    required_documents: list[str] = Field(
        ..., description="Required document types (e.g., KYC, EDD, SOW)"
    )
    violation_severity: str = Field(..., description="Low/Medium/High/Critical")

    class Config:
        json_schema_extra = {
            "example": {
                "requirement_id": "DOC-001",
                "requirement_name": "EDD required for high-risk customers",
                "applies_to_product_types": ["wire_transfer", "fx_conversion"],
                "required_documents": ["edd_report", "source_of_wealth"],
                "violation_severity": "High",
            }
        }


class RulesData(BaseModel):
    """
    Container for regulatory rules data (FR-012, FR-013).

    Placeholder structure for external team's data format.
    When rules_data is None or empty, validation is skipped (graceful degradation).
    """

    threshold_rules: list[ThresholdRule] = Field(
        default_factory=list,
        description="Transaction threshold rules for compliance checks",
    )
    prohibited_jurisdictions: list[ProhibitedJurisdiction] = Field(
        default_factory=list,
        description="High-risk or prohibited countries/jurisdictions",
    )
    documentation_requirements: list[DocumentationRequirement] = Field(
        default_factory=list,
        description="Documentation requirements for transaction types",
    )

    @property
    def is_empty(self) -> bool:
        """Check if rules data is empty (enables graceful degradation)."""
        return (
            len(self.threshold_rules) == 0
            and len(self.prohibited_jurisdictions) == 0
            and len(self.documentation_requirements) == 0
        )

    class Config:
        json_schema_extra = {
            "example": {
                "threshold_rules": [
                    {
                        "rule_id": "THR-001",
                        "rule_name": "Daily cash transaction threshold",
                        "threshold_amount": 10000.00,
                        "currency": "USD",
                        "time_period_days": 1,
                        "violation_severity": "High",
                    }
                ],
                "prohibited_jurisdictions": [
                    {
                        "country_code": "KP",
                        "country_name": "North Korea",
                        "risk_level": "Critical",
                        "sanctions_list": "OFAC SDN",
                    }
                ],
                "documentation_requirements": [
                    {
                        "requirement_id": "DOC-001",
                        "requirement_name": "EDD required for high-risk customers",
                        "applies_to_product_types": ["wire_transfer"],
                        "required_documents": ["edd_report", "source_of_wealth"],
                        "violation_severity": "High",
                    }
                ],
            }
        }
