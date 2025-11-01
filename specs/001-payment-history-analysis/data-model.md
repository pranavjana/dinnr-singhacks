# Data Model: Payment History Analysis Tool

**Feature**: 001-payment-history-analysis
**Date**: 2025-11-01
**Purpose**: Define entities, schemas, and relationships

## Overview

The system operates on four primary entities:
1. **QueryParameters**: Input for transaction searches
2. **TransactionRecord**: Individual payment transaction from CSV
3. **PaymentHistory**: Collection of matching transactions
4. **AnalysisResult**: Structured output from LLM analysis

All models use Pydantic for validation and serialization.

---

## Entity Definitions

### 1. QueryParameters (Input)

**Purpose**: Encapsulates user search criteria for retrieving transactions

**File**: `backend/models/query_params.py`

**Schema**:
```python
from pydantic import BaseModel, Field

class QueryParameters(BaseModel):
    """
    Search criteria for querying payment history.
    Supports OR logic: returns transactions matching ANY provided field.
    """
    originator_name: str | None = Field(
        None,
        description="Originator name (case-insensitive exact match)",
        example="Jennifer Parker"
    )
    originator_account: str | None = Field(
        None,
        description="Originator account number (case-insensitive exact match)",
        example="GB39OOLA52427580832378"
    )
    beneficiary_name: str | None = Field(
        None,
        description="Beneficiary name (case-insensitive exact match)",
        example="George Brown"
    )
    beneficiary_account: str | None = Field(
        None,
        description="Beneficiary account number (case-insensitive exact match)",
        example="GB88KUDJ48147748190437"
    )

    @property
    def has_filters(self) -> bool:
        """Check if at least one filter is provided"""
        return any([
            self.originator_name,
            self.originator_account,
            self.beneficiary_name,
            self.beneficiary_account
        ])
```

**Validation Rules**:
- At least one field must be non-null (enforced in API endpoint)
- Strings are trimmed and converted to lowercase during query
- Empty strings treated as None

**Relationships**:
- Input to `transaction_service.query()` method
- Passed to API endpoint `/api/payment-history/analyze`

---

### 2. TransactionRecord (Entity)

**Purpose**: Represents a single payment transaction from the CSV dataset

**File**: `backend/models/transaction.py`

**Schema** (47 fields from CSV):
```python
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

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

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
                "booking_datetime": "2024-10-10T10:24:43",
                "amount": 590012.92,
                "currency": "HKD",
                "originator_name": "Meredith Krueger",
                "beneficiary_name": "Natalie Sandoval",
                "sanctions_screening": "potential"
            }
        }
```

**Validation Rules**:
- `amount` must be non-negative
- `currency` should be valid ISO 4217 code (not enforced, CSV data trusted)
- `customer_risk_rating` must be one of: Low, Medium, High
- `sanctions_screening` must be one of: none, potential, confirmed
- Date fields use flexible parsing (CSV has mixed formats)

**Relationships**:
- Returned by `transaction_service.query()` as list
- Input to LangGraph risk analysis agent
- Serialized to JSON for LLM prompt

---

### 3. PaymentHistory (Aggregate)

**Purpose**: Collection of transactions matching query criteria

**File**: `backend/models/transaction.py`

**Schema**:
```python
class PaymentHistory(BaseModel):
    """
    Aggregated payment history for analysis.
    """
    transactions: list[TransactionRecord] = Field(
        ...,
        description="Deduplicated transactions matching query (OR logic)"
    )
    total_count: int = Field(..., description="Number of unique transactions", ge=0)
    date_range: tuple[datetime | None, datetime | None] = Field(
        ...,
        description="Earliest and latest transaction dates in results"
    )

    @property
    def is_empty(self) -> bool:
        return self.total_count == 0
```

**Computed Fields**:
- `total_count`: Length of transactions list
- `date_range`: Min/max of `booking_datetime` across transactions

**Relationships**:
- Created by `transaction_service.query()` from filtered DataFrame
- Passed to LangGraph agent for analysis

---

### 4. AnalysisResult (Output)

**Purpose**: Structured output from LLM analysis (FR-014 requirement)

**File**: `backend/models/analysis_result.py`

**Schema**:
```python
from pydantic import BaseModel, Field

class FlaggedTransaction(BaseModel):
    """Individual transaction flagged during analysis"""
    transaction_id: str = Field(..., description="Transaction ID from CSV")
    reason: str = Field(..., description="Why this transaction was flagged")
    risk_level: str = Field(..., description="Low/Medium/High/Critical")

class IdentifiedPattern(BaseModel):
    """Pattern detected across transactions"""
    pattern_type: str = Field(..., description="Type: volume_spike/round_amounts/high_risk_jurisdiction/similar_names/etc.")
    description: str = Field(..., description="Human-readable pattern description")
    affected_transactions: list[str] = Field(..., description="Transaction IDs exhibiting this pattern")
    severity: str = Field(..., description="Low/Medium/High")

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
        le=10
    )
    risk_category: str | None = Field(
        None,
        description="Overall category: Low/Medium/High/Critical, null if analysis failed"
    )

    # Flagged items
    flagged_transactions: list[FlaggedTransaction] = Field(
        default_factory=list,
        description="Transactions flagged as suspicious"
    )

    # Patterns
    identified_patterns: list[IdentifiedPattern] = Field(
        default_factory=list,
        description="Patterns detected across payment history"
    )

    # Summary
    narrative_summary: str = Field(
        ...,
        description="Human-readable explanation of findings"
    )

    # Metadata
    analyzed_transaction_count: int = Field(..., description="Number of transactions analyzed", ge=0)
    analysis_timestamp: datetime = Field(..., description="When analysis was performed")

    # Error handling (FR-018)
    error: str | None = Field(
        None,
        description="Error message if LLM unavailable (graceful degradation)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "overall_risk_score": 7.5,
                "risk_category": "High",
                "flagged_transactions": [
                    {
                        "transaction_id": "tx-123",
                        "reason": "Round-number amount to high-risk jurisdiction",
                        "risk_level": "High"
                    }
                ],
                "identified_patterns": [
                    {
                        "pattern_type": "round_amounts",
                        "description": "Multiple transactions with round-number amounts (structuring indicator)",
                        "affected_transactions": ["tx-123", "tx-456"],
                        "severity": "High"
                    }
                ],
                "narrative_summary": "Analysis detected potential structuring behavior with multiple round-number transactions to high-risk jurisdictions.",
                "analyzed_transaction_count": 25,
                "analysis_timestamp": "2025-11-01T12:00:00Z",
                "error": None
            }
        }
```

**Validation Rules**:
- `overall_risk_score` range: 0-10 (null allowed for errors)
- `risk_category` must be one of: Low, Medium, High, Critical (null allowed)
- `flagged_transactions` and `identified_patterns` can be empty lists
- `error` field populated when LLM fails (FR-018), other fields may be null/empty

**Relationships**:
- Returned by LangGraph risk analyzer agent
- Serialized to JSON by FastAPI endpoint
- Consumed by frontend for display

---

## State Definitions (LangGraph)

### RiskAnalysisState

**Purpose**: State object passed between LangGraph nodes during analysis

**File**: `backend/agents/aml_monitoring/states.py`

**Schema**:
```python
from typing import TypedDict

class RiskAnalysisState(TypedDict):
    """
    State for risk analysis LangGraph workflow.
    """
    # Input
    transactions: list[dict]  # TransactionRecords as dicts

    # Intermediate
    formatted_prompt: str | None
    llm_raw_response: str | None

    # Output
    analysis_result: dict | None  # AnalysisResult as dict
    error: str | None
```

**Node Transitions**:
1. **START** → `format_data` (receives `transactions`)
2. `format_data` → `call_llm` (sets `formatted_prompt`)
3. `call_llm` → `parse_response` (sets `llm_raw_response`) OR `handle_error` (sets `error`)
4. `parse_response` → **END** (sets `analysis_result`)
5. `handle_error` → **END** (returns partial result with `error` field)

---

## Relationships Diagram

```
┌─────────────────┐
│ QueryParameters │ (Input)
└────────┬────────┘
         │
         │ (filter)
         ▼
┌─────────────────────┐
│ TransactionRecord   │ (CSV rows)
│   (47 fields)       │
└────────┬────────────┘
         │
         │ (aggregate)
         ▼
┌─────────────────┐
│ PaymentHistory  │
└────────┬────────┘
         │
         │ (LangGraph agent)
         ▼
┌─────────────────┐
│ AnalysisResult  │ (Output)
│   - risk_scores │
│   - flagged_txs │
│   - patterns    │
│   - summary     │
└─────────────────┘
```

---

## Database Schema

**Note**: No database required. CSV file is read-only data source. Future enhancement could migrate to PostgreSQL for larger datasets.

**CSV Schema** (`transactions_mock_1000_for_participants.csv`):
- 1000 rows (sample data)
- 47 columns (mapped 1:1 to TransactionRecord fields)
- Primary key: `transaction_id` (UUID format)
- No foreign keys (flat structure)

---

## Validation Strategy

1. **Input Validation**: Pydantic validates QueryParameters at API boundary
2. **Entity Validation**: TransactionRecord validates CSV data on load (optional: skip malformed rows)
3. **Output Validation**: AnalysisResult ensures LLM output conforms to schema
4. **State Validation**: LangGraph state transitions checked at runtime

**Error Handling**:
- Invalid CSV data: Log warning, skip row, continue processing
- LLM returns malformed JSON: Attempt repair with regex, fallback to error state
- No transactions match query: Return empty AnalysisResult with informative message (FR-016)
