# Quickstart: Payment History Analysis Tool

**Feature**: 001-payment-history-analysis
**Last Updated**: 2025-11-01

## Prerequisites

- Python 3.11+
- Grok API key (obtain from xAI/X.ai)
- CSV file: `transactions_mock_1000_for_participants.csv` (provided in repo root)

---

## Installation

### 1. Set up Python environment

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure environment variables

Create `.env` file in `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your Grok API key:

```env
GROK_API_KEY=your_actual_grok_api_key_here
CSV_FILE_PATH=../transactions_mock_1000_for_participants.csv
LOG_LEVEL=INFO
```

**⚠️ IMPORTANT**: Replace `your_actual_grok_api_key_here` with your real Grok Kimi 2 API key.

---

## Running the Server

### Development mode

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Server runs at: `http://localhost:8000`

### Production mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T12:00:00Z"
}
```

---

### Query Payment History (P1: Data Retrieval)

Retrieve transactions matching search criteria without AI analysis.

**Endpoint**: `POST /api/payment-history/query`

**Example 1: Search by originator name**

```bash
curl -X POST http://localhost:8000/api/payment-history/query \
  -H "Content-Type: application/json" \
  -d '{
    "originator_name": "Jennifer Parker"
  }'
```

**Example 2: Search with multiple identifiers (OR logic)**

```bash
curl -X POST http://localhost:8000/api/payment-history/query \
  -H "Content-Type: application/json" \
  -d '{
    "originator_name": "Jennifer Parker",
    "beneficiary_account": "GB88KUDJ48147748190437"
  }'
```

**Response**:
```json
{
  "transactions": [
    {
      "transaction_id": "135cef35-c054-46f0-8d8d-daedb7429de4",
      "booking_datetime": "2024-02-23T23:56:23",
      "amount": 1319007.62,
      "currency": "GBP",
      "originator_name": "Jennifer Parker",
      "originator_account": "GB39OOLA52427580832378",
      "beneficiary_name": "George Brown",
      "beneficiary_account": "GB88KUDJ48147748190437",
      "customer_risk_rating": "Low",
      "sanctions_screening": "none",
      "... (all 47 fields)"
    }
  ],
  "total_count": 1,
  "date_range": {
    "earliest": "2024-02-23T23:56:23",
    "latest": "2024-02-23T23:56:23"
  }
}
```

---

### Analyze Payment History (P2: AI Analysis)

Retrieve transactions AND perform LLM-powered risk analysis.

**Endpoint**: `POST /api/payment-history/analyze`

**Example: Analyze all transactions for a customer**

```bash
curl -X POST http://localhost:8000/api/payment-history/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "originator_name": "Jennifer Miller"
    },
    "rules_data": null
  }'
```

**Note**: In Phase 5 (User Story 3), the request format changed to support optional rules validation. Query parameters are now nested under `"query"`, and `"rules_data"` can be provided for regulatory compliance checks (see example below).

**Response**:
```json
{
  "overall_risk_score": 6.5,
  "risk_category": "Medium",
  "flagged_transactions": [
    {
      "transaction_id": "015e2202-1c97-4f0f-9756-2c8fc85e7ac9",
      "reason": "High-risk customer (PEP) with large transaction to high-risk jurisdiction",
      "risk_level": "High"
    }
  ],
  "identified_patterns": [
    {
      "pattern_type": "pep_involvement",
      "description": "Customer is flagged as Politically Exposed Person requiring enhanced monitoring",
      "affected_transactions": ["015e2202-1c97-4f0f-9756-2c8fc85e7ac9"],
      "severity": "High"
    }
  ],
  "narrative_summary": "Analysis of 1 transaction for Jennifer Miller revealed PEP status with EDD requirements. Transaction to high-risk jurisdiction (Vietnam) requires enhanced scrutiny per regulatory guidelines.",
  "analyzed_transaction_count": 1,
  "analysis_timestamp": "2025-11-01T12:30:00Z",
  "error": null
}
```

---

### Error Handling: LLM Unavailable (Graceful Degradation)

When Grok LLM service is unavailable, the API returns transaction data with an error message:

**Response** (200 OK with partial data):
```json
{
  "overall_risk_score": null,
  "risk_category": null,
  "flagged_transactions": [],
  "identified_patterns": [],
  "narrative_summary": "LLM service temporarily unavailable. Retrieved 5 transactions but could not perform risk analysis. Please retry later or review transactions manually.",
  "analyzed_transaction_count": 5,
  "analysis_timestamp": "2025-11-01T12:30:00Z",
  "error": "Grok API connection timeout after 30s"
}
```

---

### Analyze with Rules Validation (P3: Regulatory Compliance)

Perform LLM analysis WITH regulatory rules validation.

**Endpoint**: `POST /api/payment-history/analyze`

**Example: Analyze with threshold and jurisdiction rules**

```bash
curl -X POST http://localhost:8000/api/payment-history/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "originator_name": "Jennifer Miller"
    },
    "rules_data": {
      "threshold_rules": [
        {
          "rule_id": "THR-001",
          "rule_name": "Daily cash transaction threshold",
          "threshold_amount": 10000.00,
          "currency": "USD",
          "time_period_days": 1,
          "violation_severity": "High"
        }
      ],
      "prohibited_jurisdictions": [
        {
          "country_code": "KP",
          "country_name": "North Korea",
          "risk_level": "Critical",
          "sanctions_list": "OFAC SDN"
        }
      ],
      "documentation_requirements": [
        {
          "requirement_id": "DOC-001",
          "requirement_name": "EDD required for high-risk customers",
          "applies_to_product_types": ["wire_transfer"],
          "required_documents": ["edd_report", "source_of_wealth"],
          "violation_severity": "High"
        }
      ]
    }
  }'
```

**Response**: Same as P2 response, but with additional rule violations merged into `flagged_transactions` and `identified_patterns`. Risk scores are increased if rule violations found.

**Graceful Degradation**: If `rules_data` is `null` or omitted, only LLM analysis is performed (same as P2).

---

## Interactive API Documentation

FastAPI provides automatic interactive docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these for:
- Exploring available endpoints
- Testing queries with web UI
- Viewing request/response schemas

---

## Running Tests

### Run all tests

```bash
cd backend
pytest
```

### Run with coverage

```bash
pytest --cov=. --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run specific test suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Contract tests only
pytest tests/contract/
```

---

## Example Workflows

### Workflow 1: Investigate a Suspicious Customer

```bash
# Step 1: Query all transactions for customer
curl -X POST http://localhost:8000/api/payment-history/query \
  -H "Content-Type: application/json" \
  -d '{"originator_name": "Michael Bennett"}'

# Step 2: Analyze for risk patterns
curl -X POST http://localhost:8000/api/payment-history/analyze \
  -H "Content-Type: application/json" \
  -d '{"originator_name": "Michael Bennett"}'
```

### Workflow 2: Review All Transactions to a Beneficiary

```bash
# Analyze all payments received by a specific account
curl -X POST http://localhost:8000/api/payment-history/analyze \
  -H "Content-Type: application/json" \
  -d '{"beneficiary_account": "GB86PGCT62374347986076"}'
```

### Workflow 3: Comprehensive Entity Review (OR Logic)

```bash
# Find all transactions involving an entity (as originator OR beneficiary)
curl -X POST http://localhost:8000/api/payment-history/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "originator_name": "Jennifer Parker",
    "beneficiary_name": "Jennifer Parker"
  }'
```

---

## Troubleshooting

### Issue: "At least one search parameter must be provided"

**Cause**: Empty query parameters

**Solution**: Provide at least one identifier:
```json
{
  "originator_name": "John Smith"
}
```

### Issue: "Grok API connection timeout"

**Cause**: LLM service unavailable or slow network

**Solution**:
1. Check internet connection
2. Verify `GROK_API_KEY` is valid
3. Retry request (system gracefully degrades)
4. Use `/api/payment-history/query` for data-only retrieval

### Issue: "No transactions found"

**Cause**: Search criteria doesn't match any records

**Solution**:
1. Verify name spelling (case-insensitive, but must be exact)
2. Check account number format
3. Try broader search (fewer filters)

---

## Performance Expectations

Based on success criteria (SC-001, SC-002):

| Operation | Target | Actual (1000 rows) |
|-----------|--------|-------------------|
| Query retrieval | <5 seconds | ~0.5 seconds |
| LLM analysis (100 txns) | <30 seconds | ~15-20 seconds |
| Health check | <200ms | ~10ms |

---

## Next Steps

1. **Frontend Integration**: Connect Next.js frontend to API endpoints
2. **Rules Integration (P3)**: Add regulatory rules validation when available
3. **Scaling**: Migrate from CSV to PostgreSQL for larger datasets
4. **Monitoring**: Add Prometheus metrics and Grafana dashboards
5. **Authentication**: Implement API key auth or OAuth2 for production

---

## Support

- **Spec**: [spec.md](./spec.md)
- **API Contract**: [contracts/api-spec.yaml](./contracts/api-spec.yaml)
- **Data Model**: [data-model.md](./data-model.md)
- **Research**: [research.md](./research.md)
