# Payment History Analysis Tool - Backend

FastAPI backend for AML compliance tool with LLM-powered risk analysis.

## Features

- **Query Payment History**: Retrieve transactions by originator/beneficiary identifiers (OR logic, case-insensitive)
- **LLM Risk Analysis**: AI-powered pattern detection using Grok Kimi 2
- **Rules Validation**: Optional regulatory compliance checks (thresholds, jurisdictions, documentation)
- **Graceful Degradation**: Returns data even when LLM unavailable

## Tech Stack

- **Python 3.11+**
- **FastAPI**: Async web framework
- **LangGraph**: Agent orchestration for multi-step workflows
- **Pandas**: CSV data processing
- **Pydantic**: Data validation
- **Grok Kimi 2**: xAI's LLM for transaction analysis

## Project Structure

```
backend/
├── agents/
│   └── aml_monitoring/
│       ├── risk_analyzer.py    # LangGraph workflow
│       └── states.py           # State definitions
├── models/
│   ├── analysis_result.py      # LLM output models
│   ├── query_params.py         # Query input model
│   ├── rules.py                # Rules validation models
│   └── transaction.py          # Transaction entities
├── routers/
│   ├── health.py               # Health check endpoint
│   └── payment_history.py      # Query & analysis endpoints
├── services/
│   ├── llm_client.py           # Grok API client
│   └── transaction_service.py  # CSV query service
├── config.py                   # Environment configuration
├── main.py                     # FastAPI app entry point
└── requirements.txt            # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
GROK_API_KEY=your_actual_grok_api_key_here
CSV_FILE_PATH=../transactions_mock_1000_for_participants.csv
LOG_LEVEL=INFO
```

**Important**: Replace `your_actual_grok_api_key_here` with your Grok Kimi 2 API key from https://x.ai

### 3. Run Server

```bash
uvicorn main:app --reload --port 8000
```

Server will start at: http://localhost:8000

## API Documentation

Once the server is running, visit:

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

## API Endpoints

### Health Check

```bash
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T12:00:00Z"
}
```

### Query Payment History

```bash
POST /api/payment-history/query
Content-Type: application/json

{
  "originator_name": "Jennifer Parker"
}
```

**Parameters** (at least one required):
- `originator_name`: Originator name (case-insensitive)
- `originator_account`: Originator account number
- `beneficiary_name`: Beneficiary name
- `beneficiary_account`: Beneficiary account number

**Response**:
```json
{
  "transactions": [
    {
      "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
      "booking_datetime": "2024-10-10T10:24:43",
      "amount": 590012.92,
      "currency": "HKD",
      "originator_name": "Jennifer Parker",
      "beneficiary_name": "Natalie Sandoval",
      ...
    }
  ],
  "total_count": 25,
  "date_range": ["2024-01-15T08:30:00", "2024-10-10T10:24:43"]
}
```

### Analyze Payment History

```bash
POST /api/payment-history/analyze
Content-Type: application/json

{
  "query": {
    "originator_name": "Jennifer Parker"
  },
  "rules_data": null
}
```

**With Rules Validation** (optional):
```json
{
  "query": {
    "originator_name": "Jennifer Parker"
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
    "documentation_requirements": []
  }
}
```

**Response**:
```json
{
  "overall_risk_score": 7.5,
  "risk_category": "High",
  "flagged_transactions": [
    {
      "transaction_id": "ad66338d-b17f-47fc-a966-1b4395351b41",
      "reason": "Round-number amount to high-risk jurisdiction",
      "risk_level": "High"
    }
  ],
  "identified_patterns": [
    {
      "pattern_type": "round_amounts",
      "description": "Multiple transactions with round-number amounts (structuring indicator)",
      "affected_transactions": ["ad66338d-...", "f72e3c4a-..."],
      "severity": "High"
    }
  ],
  "narrative_summary": "Analysis detected potential structuring behavior...",
  "analyzed_transaction_count": 25,
  "analysis_timestamp": "2025-11-01T12:00:00Z",
  "error": null
}
```

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROK_API_KEY` | `your_grok_api_key_here` | Grok Kimi 2 API key (REQUIRED) |
| `CSV_FILE_PATH` | `../transactions_mock_1000_for_participants.csv` | Path to transaction CSV |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |

## Development

### Code Quality

The codebase follows Python best practices:
- Type hints throughout
- Pydantic models for validation
- Comprehensive docstrings
- Structured logging

### Adding New Features

1. **Models**: Add to `models/` directory
2. **Services**: Business logic in `services/`
3. **Agents**: LangGraph workflows in `agents/aml_monitoring/`
4. **Endpoints**: API routes in `routers/`
5. **Register**: Update `main.py` to include new routers

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure:
1. Virtual environment is activated
2. Dependencies installed: `pip install -r requirements.txt`
3. Running from `backend/` directory

### LLM Unavailable

If Grok API fails:
- Check `GROK_API_KEY` is valid
- Verify internet connectivity
- System returns partial results with `error` field populated (graceful degradation)

### Empty Query Results

Returns empty `transactions` list with `total_count: 0`. This is not an error - means no matches found.

### CORS Issues

Frontend must run on `http://localhost:3000`. To change, update `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://your-frontend-url:port"],
    ...
)
```

## Architecture

### Query Flow (User Story 1)

```
Client → POST /api/payment-history/query
       → QueryParameters validation
       → transaction_service.query()
       → Pandas DataFrame filtering (OR logic, case-insensitive)
       → Deduplication by transaction_id
       → PaymentHistory response
```

### Analysis Flow (User Story 2 & 3)

```
Client → POST /api/payment-history/analyze
       → Query transactions (User Story 1)
       → LangGraph Agent:
          ├─ format_data: Build LLM prompt
          ├─ call_llm: Grok Kimi 2 API (with retry)
          ├─ parse_response: Validate JSON output
          └─ validate_rules: Apply regulatory rules (optional)
       → AnalysisResult response
```

### LangGraph Workflow

```
START → format_data → call_llm → [conditional]
                                  ├─ parse_response → [conditional]
                                  │                   ├─ validate_rules → END (if rules)
                                  │                   └─ END (no rules)
                                  └─ handle_error → END (LLM failed)
```

## Performance

- Query: <5 seconds for 10K transactions
- Analysis: <30 seconds for 100 transactions
- Health check: <200ms

## License

MIT License - Hackathon Project for Julius Baer Challenge

## Support

For issues or questions, see main repository README or create an issue on GitHub.
