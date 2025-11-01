# Implementation Plan: Payment History Analysis Tool

**Branch**: `001-payment-history-analysis` | **Date**: 2025-11-01 | **Spec**: [spec.md](./spec.md)

## Summary

Build a Payment History Analysis Tool for AML compliance that retrieves transaction data based on customer identifiers (originator/beneficiary names and accounts), analyzes patterns using Grok Kimi 2 LLM via LangGraph agents, and integrates with regulatory rules when available. The system uses OR logic to retrieve all transactions matching any provided identifier, performs AI-powered risk analysis, and returns structured JSON results with graceful degradation when services are unavailable.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, LangGraph, Grok Kimi 2 LLM client, Pydantic, pandas (CSV processing)
**Storage**: CSV file (`transactions_mock_1000_for_participants.csv`) - read-only access
**Testing**: pytest, pytest-asyncio (for async FastAPI endpoints)
**Target Platform**: Linux/macOS server (development), containerized deployment (production)
**Project Type**: Web API (backend only, frontend already exists)
**Performance Goals**: <5 seconds query retrieval (10K transactions), <30 seconds LLM analysis (100 transactions)
**Constraints**: <200ms API response for health checks, graceful degradation for LLM failures, case-insensitive search
**Scale/Scope**: 1000 transactions (current CSV), 10 concurrent users, extensible to larger datasets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: No project-specific constitution found (template placeholder in `.specify/memory/constitution.md`). Applying standard best practices:

✅ **Simplicity**: Single backend service, minimal dependencies
✅ **Testability**: Pytest for unit/integration tests, contract testing for API endpoints
✅ **Observability**: Structured logging for audit trails (FR-017), error messages for failures
✅ **Maintainability**: Clear separation: routers (API) → agents (LangGraph) → services (business logic)
✅ **Security**: API key management via environment variables (placeholder for Grok API key)

**Potential Violations**: None identified

## Project Structure

### Documentation (this feature)

```text
specs/001-payment-history-analysis/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technology decisions)
├── data-model.md        # Phase 1 output (entities and schemas)
├── quickstart.md        # Phase 1 output (setup and usage)
├── contracts/           # Phase 1 output (OpenAPI schemas)
│   └── api-spec.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
backend/                             # FastAPI + LangGraph backend
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration (API keys, file paths)
├── routers/                         # FastAPI route handlers
│   ├── __init__.py
│   ├── payment_history.py           # Query and analysis endpoints
│   └── health.py                    # Health check endpoint
├── agents/                          # LangGraph agent definitions
│   ├── __init__.py
│   ├── aml_monitoring/              # P2: LLM analysis agents
│   │   ├── __init__.py
│   │   ├── risk_analyzer.py         # LangGraph StateGraph for risk analysis
│   │   └── states.py                # Agent state definitions (TypedDict/Pydantic)
│   └── document_corroboration/      # Future: P3 document analysis (placeholder)
│       └── __init__.py
├── services/                        # Business logic layer
│   ├── __init__.py
│   ├── transaction_service.py       # CSV query logic (OR filters, deduplication)
│   └── llm_client.py                # Grok Kimi 2 API wrapper
├── models/                          # Pydantic models and schemas
│   ├── __init__.py
│   ├── query_params.py              # Input: QueryParameters
│   ├── transaction.py               # Entity: TransactionRecord
│   └── analysis_result.py           # Output: AnalysisResult (JSON structure)
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures (mock CSV, mock LLM)
│   ├── unit/                        # Unit tests (services, models)
│   │   ├── test_transaction_service.py
│   │   └── test_llm_client.py
│   ├── integration/                 # Integration tests (agents, end-to-end)
│   │   ├── test_risk_analyzer_agent.py
│   │   └── test_payment_history_api.py
│   └── contract/                    # Contract tests (OpenAPI compliance)
│       └── test_api_contracts.py
├── requirements.txt                 # Python dependencies
└── .env.example                     # Example environment variables (GROK_API_KEY)

frontend/                            # Existing Next.js frontend (unchanged)
transactions_mock_1000_for_participants.csv  # Sample AML data
```

**Structure Decision**: Web application architecture (Option 2) with backend-only implementation. Frontend already exists at `frontend/`. Backend follows layered architecture: API layer (routers) → Agent layer (LangGraph workflows) → Service layer (business logic) → Data layer (CSV access).

## Complexity Tracking

No constitution violations identified. Design follows standard best practices for FastAPI + LangGraph applications.

---

## Phase Completion Summary

### ✅ Phase 0: Research (Complete)

**Output**: `research.md`

**Key Decisions**:
- LLM Integration: Grok Kimi 2 via HTTP API
- Agent Framework: LangGraph with StateGraph pattern
- CSV Query: pandas with OR filtering and deduplication
- API Design: FastAPI with async endpoints
- Testing: pytest with fixtures for mocking
- Configuration: Environment variables via `.env`

**All technical unknowns resolved. Ready for Phase 1.**

---

### ✅ Phase 1: Design & Contracts (Complete)

**Outputs**:
- `data-model.md`: 4 entities (QueryParameters, TransactionRecord, PaymentHistory, AnalysisResult)
- `contracts/api-spec.yaml`: OpenAPI 3.1 specification with 3 endpoints
- `quickstart.md`: Setup guide, API usage examples, troubleshooting
- `CLAUDE.md`: Updated with technology stack for future AI assistance

**Constitution Re-Check**: ✅ No new violations introduced

**Key Artifacts**:
1. **Data Model**: All 47 CSV fields mapped to TransactionRecord Pydantic model
2. **API Contract**: 3 endpoints defined - `/health`, `/api/payment-history/query`, `/api/payment-history/analyze`
3. **LangGraph State**: RiskAnalysisState with 5-node workflow (format → call_llm → parse → validate/error → end)
4. **Error Handling**: Graceful degradation pattern for LLM failures (FR-018)

---

## Next Steps

### Phase 2: Task Generation (Not Started)

Run `/speckit.tasks` to generate actionable task list from this plan.

Expected tasks:
1. **Backend setup** (5-6 tasks): Create directory structure, config.py, requirements.txt, .env.example
2. **Data models** (4 tasks): Implement Pydantic models for query_params, transaction, analysis_result, states
3. **Services** (2-3 tasks): transaction_service.py (CSV query), llm_client.py (Grok wrapper)
4. **LangGraph agent** (3-4 tasks): risk_analyzer.py (StateGraph), node functions, conditional routing
5. **API endpoints** (3 tasks): health.py, payment_history.py routers, main.py application
6. **Testing** (4-5 tasks): conftest.py fixtures, unit tests, integration tests, contract tests
7. **Documentation** (2 tasks): README.md, deployment guide

**Estimated Total**: 23-27 implementation tasks

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Grok API changes/unavailability | Medium | High | Graceful degradation (FR-018), comprehensive error handling |
| CSV performance at scale | Low | Medium | Profiling with 10K rows, migration path to PostgreSQL documented |
| LangGraph learning curve | Medium | Low | Well-documented StateGraph pattern in research.md, examples in quickstart.md |
| Missing rules data dependency | High | Low | P3 feature, system functional without it (FR-012) |
| Test coverage gaps | Medium | Medium | Comprehensive test plan with fixtures, >80% coverage target |

---

## Implementation Readiness

✅ **All planning phases complete**
✅ **Technology stack validated** (FastAPI + LangGraph + Grok Kimi 2)
✅ **API contracts defined** (OpenAPI 3.1 spec)
✅ **Data models documented** (47-field TransactionRecord + 3 other entities)
✅ **Error handling designed** (graceful degradation for LLM failures)
✅ **Testing strategy established** (unit/integration/contract tests with pytest)
✅ **Agent context updated** (CLAUDE.md has technology stack for AI assistance)

**Ready for `/speckit.tasks` command to generate implementation tasks.**
