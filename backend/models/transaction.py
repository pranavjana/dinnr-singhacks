"""
Transaction models for payment history data.

Contains all 47 fields from the CSV dataset.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class TransactionRecord(BaseModel):
    """
    Complete transaction record matching CSV schema.
    All 47 fields from transactions_mock_1000_for_participants.csv
    """

    # Identifiers
    transaction_id: str = Field(..., description="Unique transaction identifier")
    booking_datetime: datetime = Field(..., description="Transaction booking timestamp")
    value_date: str = Field(..., description="Value date (DD/MM/YYYY format)")

    # Regulatory context
    booking_jurisdiction: str = Field(..., description="Jurisdiction (HK, SG, CH)")
    regulator: str = Field(..., description="Regulatory body (HKMA/SFC, MAS, FINMA)")

    # Transaction details
    amount: Decimal = Field(..., description="Transaction amount", ge=0)
    currency: str = Field(..., description="Currency code (USD, GBP, CHF, etc.)")
    channel: str = Field(..., description="Channel (RTGS, SWIFT, Cash, etc.)")
    product_type: str = Field(..., description="Product (fx_conversion, wire_transfer, etc.)")

    # Originator (sender)
    originator_name: str = Field(..., description="Originator full name")
    originator_account: str = Field(..., description="Originator account number")
    originator_country: str = Field(..., description="Originator country code (2-letter)")

    # Beneficiary (recipient)
    beneficiary_name: str = Field(..., description="Beneficiary full name")
    beneficiary_account: str = Field(..., description="Beneficiary account number")
    beneficiary_country: str = Field(..., description="Beneficiary country code (2-letter)")

    # SWIFT fields
    swift_mt: str | None = Field(None, description="SWIFT message type (MT103, MT202COV, etc.)")
    ordering_institution_bic: str | None = Field(None, description="Ordering institution BIC")
    beneficiary_institution_bic: str | None = Field(None, description="Beneficiary institution BIC")
    swift_f50_present: bool = Field(..., description="Field 50 (Ordering Customer) present")
    swift_f59_present: bool = Field(..., description="Field 59 (Beneficiary) present")
    swift_f70_purpose: str | None = Field(None, description="Field 70 (Remittance Info)")
    swift_f71_charges: str | None = Field(None, description="Field 71 (Charges) - BEN/OUR/SHA")

    # Compliance flags
    travel_rule_complete: bool = Field(..., description="Travel Rule compliance completed")
    fx_indicator: bool = Field(..., description="Foreign exchange involved")
    fx_base_ccy: str | None = Field(None, description="FX base currency")
    fx_quote_ccy: str | None = Field(None, description="FX quote currency")
    fx_applied_rate: Decimal | None = Field(None, description="FX rate applied")
    fx_market_rate: Decimal | None = Field(None, description="Market FX rate at time")
    fx_spread_bps: int | None = Field(None, description="FX spread in basis points")
    fx_counterparty: str | None = Field(None, description="FX counterparty name")

    # Customer data
    customer_id: str = Field(..., description="Customer identifier (CUST-XXXXXX)")
    customer_type: str = Field(..., description="Type: individual/corporate/domiciliary_company")
    customer_risk_rating: str = Field(..., description="Risk rating: Low/Medium/High")
    customer_is_pep: bool = Field(..., description="Politically Exposed Person flag")

    # KYC/EDD
    kyc_last_completed: str = Field(..., description="Last KYC completion date (DD/M/YYYY)")
    kyc_due_date: str = Field(..., description="Next KYC due date (DD/M/YYYY)")
    edd_required: bool = Field(..., description="Enhanced Due Diligence required")
    edd_performed: bool = Field(..., description="EDD actually performed")
    sow_documented: bool = Field(..., description="Source of Wealth documented")

    # Transaction metadata
    purpose_code: str = Field(..., description="Purpose: SAL/INV/EDU/TAX/etc.")
    narrative: str = Field(..., description="Transaction narrative/description")
    is_advised: bool = Field(..., description="Transaction is advised")
    product_complex: bool = Field(..., description="Product is complex")
    client_risk_profile: str = Field(..., description="Risk profile: Low/Balanced/High")
    suitability_assessed: bool = Field(..., description="Suitability assessment performed")
    suitability_result: str | None = Field(None, description="Suitability result (match/mismatch)")
    product_has_va_exposure: bool = Field(..., description="Virtual asset exposure")
    va_disclosure_provided: bool = Field(..., description="VA disclosure provided")

    # Cash-specific
    cash_id_verified: bool = Field(..., description="Cash ID verification completed")
    daily_cash_total_customer: Decimal = Field(..., description="Daily cash total for customer", ge=0)
    daily_cash_txn_count: int = Field(..., description="Daily cash transaction count", ge=0)

    # AML screening
    sanctions_screening: str = Field(..., description="Screening result: none/potential/confirmed")
    suspicion_determined_datetime: datetime | None = Field(None, description="When suspicion flagged")
    str_filed_datetime: datetime | None = Field(None, description="Suspicious Transaction Report filed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
                    "booking_datetime": "2024-10-10T10:24:43",
                    "amount": 590012.92,
                    "currency": "HKD",
                    "originator_name": "Meredith Krueger",
                    "beneficiary_name": "Natalie Sandoval",
                    "sanctions_screening": "potential",
                }
            ]
        }
    }


class PaymentHistory(BaseModel):
    """
    Aggregated payment history for analysis.
    Collection of transactions matching query criteria.
    """

    transactions: list[TransactionRecord] = Field(..., description="Deduplicated transactions matching query (OR logic)")
    total_count: int = Field(..., description="Number of unique transactions", ge=0)
    date_range: tuple[datetime | None, datetime | None] = Field(
        ..., description="Earliest and latest transaction dates in results"
    )

    @property
    def is_empty(self) -> bool:
        """Check if payment history contains no transactions."""
        return self.total_count == 0

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transactions": [],
                    "total_count": 0,
                    "date_range": (None, None),
                }
            ]
        }
    }
