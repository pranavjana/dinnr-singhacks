# Research: Payment History Analysis Tool

**Feature**: 001-payment-history-analysis
**Date**: 2025-11-01
**Purpose**: Resolve technology choices and implementation patterns

## Technology Decisions

### 1. LLM Integration: Grok Kimi 2

**Decision**: Use Grok Kimi 2 (xAI's LLM) via API for transaction analysis

**Rationale**:
- User requirement specifies Grok Kimi 2
- Grok excels at structured data analysis and pattern recognition tasks
- Supports large context windows suitable for analyzing multiple transactions simultaneously
- JSON output mode aligns with FR-014 requirement for structured results

**Implementation Approach**:
- HTTP client wrapper in `services/llm_client.py`
- API key via environment variable: `GROK_API_KEY` (placeholder for user to fill)
- Retry logic with exponential backoff for transient failures
- Graceful degradation: catch exceptions and return data without analysis (FR-018)

**API Example**:
```python
import httpx

class GrokClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"  # Grok API endpoint

    async def analyze_transactions(self, transactions: list[dict]) -> dict:
        # POST to /chat/completions with structured prompt
        # Request JSON mode output for AnalysisResult schema
```

**Alternatives Considered**:
- OpenAI GPT-4: Not selected (user specified Grok)
- Anthropic Claude: Not selected (user specified Grok)
- Open-source LLMs (Llama, Mistral): Require self-hosting, added complexity

---

### 2. Agent Framework: LangGraph

**Decision**: Use LangGraph for orchestrating multi-step analysis workflows

**Rationale**:
- User requirement specifies LangGraph
- Stateful graph-based execution ideal for multi-step AML analysis (retrieve → format → analyze → validate)
- Built-in support for conditional routing (e.g., skip rules validation if unavailable)
- Integrates seamlessly with LLM calls and supports human-in-the-loop patterns

**Implementation Approach**:
- Define `RiskAnalysisState` (TypedDict) with fields: `transactions`, `formatted_data`, `llm_response`, `analysis_result`, `error`
- Create `StateGraph` with nodes:
  1. `format_data`: Transform TransactionRecords to LLM-friendly format
  2. `call_llm`: Send to Grok Kimi 2 with analysis prompt
  3. `parse_response`: Extract structured JSON from LLM output
  4. `validate_rules`: (Optional) Apply rules if available
  5. `handle_error`: Graceful degradation path
- Use conditional edges to route based on LLM availability and rules presence

**Pattern Example**:
```python
from langgraph.graph import StateGraph
from typing import TypedDict

class RiskAnalysisState(TypedDict):
    transactions: list[dict]
    formatted_data: str
    llm_response: dict | None
    analysis_result: dict | None
    error: str | None

workflow = StateGraph(RiskAnalysisState)
workflow.add_node("format_data", format_transactions_node)
workflow.add_node("call_llm", call_grok_node)
workflow.add_node("parse_response", parse_llm_output_node)
workflow.add_conditional_edges("call_llm", route_based_on_success)
```

**Alternatives Considered**:
- LangChain: More complex, LangGraph is simpler for stateful workflows
- Custom orchestration: Reinventing the wheel, LangGraph provides battle-tested patterns

---

### 3. CSV Query Strategy: Pandas with OR Filtering

**Decision**: Use pandas for in-memory CSV querying with OR logic and deduplication

**Rationale**:
- Existing data source is CSV (`transactions_mock_1000_for_participants.csv`)
- pandas provides efficient filtering, case-insensitive search, and deduplication
- 1000 rows fit comfortably in memory (scales to 100K+ rows without issues)
- Meets performance requirement: <5 seconds for 10K transactions

**Implementation Approach**:
```python
import pandas as pd

def query_transactions(
    originator_name: str | None = None,
    originator_account: str | None = None,
    beneficiary_name: str | None = None,
    beneficiary_account: str | None = None
) -> pd.DataFrame:
    df = pd.read_csv("transactions_mock_1000_for_participants.csv")

    # Build OR filters (case-insensitive)
    filters = []
    if originator_name:
        filters.append(df['originator_name'].str.lower() == originator_name.lower())
    if originator_account:
        filters.append(df['originator_account'].str.lower() == originator_account.lower())
    if beneficiary_name:
        filters.append(df['beneficiary_name'].str.lower() == beneficiary_name.lower())
    if beneficiary_account:
        filters.append(df['beneficiary_account'].str.lower() == beneficiary_account.lower())

    # Combine with OR, deduplicate by transaction_id
    if filters:
        mask = filters[0]
        for f in filters[1:]:
            mask = mask | f
        result = df[mask].drop_duplicates(subset=['transaction_id'])
        return result
    return pd.DataFrame()  # No filters = empty result
```

**Deduplication**: `drop_duplicates(subset=['transaction_id'])` handles FR-005 requirement

**Alternatives Considered**:
- SQLite in-memory: Overkill for read-only CSV, adds complexity
- Direct file parsing: Less efficient than pandas for filtering/searching
- Database migration: Future optimization, not needed for 1000-row dataset

---

### 4. API Design: FastAPI with Async Endpoints

**Decision**: FastAPI with async/await for I/O-bound operations (LLM calls)

**Rationale**:
- User requirement specifies FastAPI
- Async support crucial for LLM API calls (30-second analysis times)
- Automatic OpenAPI schema generation (contract testing)
- Pydantic integration for request/response validation
- Meets performance constraint: <200ms for health checks

**Endpoint Design**:
```python
@router.post("/api/payment-history/analyze", response_model=AnalysisResult)
async def analyze_payment_history(query: QueryParameters) -> AnalysisResult:
    # 1. Query transactions (sync, fast)
    transactions = transaction_service.query(query)

    # 2. Run LangGraph agent (async, calls Grok)
    analysis = await risk_analyzer_agent.run(transactions)

    # 3. Return structured result
    return analysis
```

**Error Handling**:
- LLM unavailable: Return `AnalysisResult` with `error` field populated, `risk_scores=None`
- No transactions found: Return empty result with informative message (FR-016)
- Invalid query params: Pydantic validation raises 422 Unprocessable Entity

**Alternatives Considered**:
- Flask: Lacks native async support, FastAPI is superior for I/O-bound workloads
- Django: Too heavy for simple API, overkill for this use case

---

### 5. Testing Strategy

**Decision**: Pytest with fixtures for mocking CSV data and LLM responses

**Approach**:
1. **Unit Tests**: Test individual components in isolation
   - `test_transaction_service.py`: Test OR logic, deduplication, case-insensitivity
   - `test_llm_client.py`: Test API wrapper with mocked HTTP responses

2. **Integration Tests**: Test end-to-end flows
   - `test_risk_analyzer_agent.py`: Test LangGraph workflow with mocked LLM
   - `test_payment_history_api.py`: Test FastAPI endpoints with TestClient

3. **Contract Tests**: Validate OpenAPI schema compliance
   - `test_api_contracts.py`: Ensure responses match defined schemas

**Fixtures** (`conftest.py`):
```python
@pytest.fixture
def mock_csv_data():
    return pd.DataFrame({
        'transaction_id': ['tx1', 'tx2'],
        'originator_name': ['John Smith', 'Jane Doe'],
        'amount': [1000, 2000],
        # ... all 47 CSV fields
    })

@pytest.fixture
def mock_grok_response():
    return {
        "risk_score": 7.5,
        "flagged_transactions": ["tx1"],
        "patterns": ["High-value round amounts"],
        "summary": "Potential structuring detected"
    }
```

**Coverage Goals**: >80% code coverage, 100% coverage for critical paths (query logic, LLM error handling)

---

### 6. Configuration Management

**Decision**: Environment variables via `.env` file (development) and system env (production)

**Required Variables**:
- `GROK_API_KEY`: Grok Kimi 2 API authentication (PLACEHOLDER - user fills)
- `CSV_FILE_PATH`: Path to transaction CSV (default: `./transactions_mock_1000_for_participants.csv`)
- `LOG_LEVEL`: Logging verbosity (default: `INFO`)

**Implementation**:
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    grok_api_key: str = "YOUR_GROK_API_KEY_HERE"  # Placeholder
    csv_file_path: str = "./transactions_mock_1000_for_participants.csv"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

**`.env.example`**:
```
GROK_API_KEY=YOUR_GROK_API_KEY_HERE
CSV_FILE_PATH=./transactions_mock_1000_for_participants.csv
LOG_LEVEL=INFO
```

---

## Best Practices Applied

### FastAPI
- Async endpoints for I/O-bound operations
- Dependency injection for services (transaction_service, llm_client)
- Automatic request validation via Pydantic
- Structured error responses (HTTPException with detail)

### LangGraph
- Clear state definitions with TypedDict/Pydantic
- Idempotent nodes (no side effects)
- Conditional routing for error paths
- State persistence for debugging (optional checkpoints)

### Python Code Quality
- Type hints throughout (mypy compatibility)
- Black formatting
- Flake8 linting
- Docstrings for public functions

### Security
- API keys in environment variables (never hardcoded)
- Input validation via Pydantic
- CORS configuration for frontend integration
- Rate limiting (future enhancement)

---

## Unresolved Items

None. All technical decisions resolved based on user requirements and spec clarifications.
