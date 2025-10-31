# Tasks: Payment History Analysis Tool

**Input**: Design documents from `/specs/001-payment-history-analysis/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT included in this task list per standard Python/FastAPI development practices. Tests will be written alongside implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/` for Python FastAPI backend
- All paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create backend directory structure: backend/{routers,agents/aml_monitoring,services,models,tests/{unit,integration,contract}}
- [x] T002 [P] Create backend/requirements.txt with dependencies: fastapi, uvicorn, pydantic, pydantic-settings, pandas, langgraph, httpx, pytest, pytest-asyncio
- [x] T003 [P] Create backend/.env.example with placeholders: GROK_API_KEY, CSV_FILE_PATH, LOG_LEVEL
- [x] T004 [P] Create backend/config.py for environment configuration using pydantic-settings BaseSettings

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Create backend/models/__init__.py with module exports
- [x] T006 [P] Create backend/services/__init__.py with module exports
- [x] T007 [P] Create backend/routers/__init__.py with module exports
- [x] T008 [P] Create backend/agents/__init__.py and backend/agents/aml_monitoring/__init__.py with module exports
- [x] T009 [P] Implement QueryParameters model in backend/models/query_params.py with optional originator_name, originator_account, beneficiary_name, beneficiary_account fields
- [x] T010 [P] Implement TransactionRecord model in backend/models/transaction.py with all 47 CSV fields per data-model.md
- [x] T011 Create backend/main.py FastAPI application entry point with CORS, health endpoint, and payment_history router registration
- [x] T012 Implement health check endpoint in backend/routers/health.py returning {status, timestamp}

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Query Payment History by Entity (Priority: P1) 🎯 MVP

**Goal**: Retrieve complete payment history for specific customers/beneficiaries using OR logic with deduplication

**Independent Test**: Provide known customer name/account and verify all matching transactions returned with correct OR filtering and deduplication by transaction_id

**Functional Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-015, FR-016, FR-017

### Implementation for User Story 1

- [x] T013 [P] [US1] Create PaymentHistory model in backend/models/transaction.py with transactions list, total_count, and date_range fields
- [x] T014 [US1] Implement transaction_service.py in backend/services/ with query() method: loads CSV with pandas, applies OR filters (case-insensitive), deduplicates by transaction_id, returns PaymentHistory
- [x] T015 [US1] Implement /api/payment-history/query POST endpoint in backend/routers/payment_history.py: accepts QueryParameters, calls transaction_service.query(), returns PaymentHistory JSON
- [x] T016 [US1] Add input validation to payment_history router: require at least one query parameter, return 400 if all None
- [x] T017 [US1] Add error handling for empty results: return informative message when no transactions match (FR-016)
- [x] T018 [US1] Add structured logging for queries in transaction_service using Python logging module (FR-017): log query parameters, result count, execution time

**Checkpoint**: At this point, User Story 1 should be fully functional - compliance officers can query payment history

---

## Phase 4: User Story 2 - LLM-Powered Risk Analysis (Priority: P2)

**Goal**: AI-powered pattern detection and risk analysis using Grok Kimi 2 LLM via LangGraph agents

**Independent Test**: Retrieve known payment history, verify LLM analysis includes risk scoring, pattern identification, and flagged transactions with graceful degradation on LLM failure

**Functional Requirements**: FR-007, FR-008, FR-009, FR-010, FR-011, FR-014, FR-018

### Implementation for User Story 2

- [x] T019 [P] [US2] Create FlaggedTransaction and IdentifiedPattern models in backend/models/analysis_result.py per data-model.md
- [x] T020 [P] [US2] Create AnalysisResult model in backend/models/analysis_result.py with overall_risk_score, risk_category, flagged_transactions, identified_patterns, narrative_summary, analyzed_transaction_count, analysis_timestamp, error fields
- [x] T021 [P] [US2] Create RiskAnalysisState TypedDict in backend/agents/aml_monitoring/states.py with transactions, formatted_prompt, llm_raw_response, analysis_result, error fields
- [x] T022 [US2] Implement GrokClient class in backend/services/llm_client.py with async analyze_transactions() method: HTTP client for Grok Kimi 2 API, uses GROK_API_KEY from config, requests JSON mode output, implements retry logic with exponential backoff
- [x] T023 [US2] Implement format_data node function in backend/agents/aml_monitoring/risk_analyzer.py: transforms TransactionRecords to LLM-friendly JSON prompt with analysis instructions (FR-007)
- [x] T024 [US2] Implement call_llm node function in backend/agents/aml_monitoring/risk_analyzer.py: calls GrokClient.analyze_transactions(), handles exceptions for graceful degradation (FR-018)
- [x] T025 [US2] Implement parse_response node function in backend/agents/aml_monitoring/risk_analyzer.py: extracts structured JSON from LLM output, validates against AnalysisResult schema, handles malformed responses
- [x] T026 [US2] Implement handle_error node function in backend/agents/aml_monitoring/risk_analyzer.py: creates partial AnalysisResult with error field populated when LLM fails (FR-018)
- [x] T027 [US2] Create StateGraph workflow in backend/agents/aml_monitoring/risk_analyzer.py: connects format_data → call_llm → (conditional) parse_response or handle_error → END, add conditional edges based on LLM success/failure
- [x] T028 [US2] Create async run_risk_analysis() function in backend/agents/aml_monitoring/risk_analyzer.py: entry point that executes StateGraph with transaction list, returns AnalysisResult
- [x] T029 [US2] Implement /api/payment-history/analyze POST endpoint in backend/routers/payment_history.py: queries transactions via transaction_service, runs LangGraph risk analysis agent, returns AnalysisResult JSON (FR-014)
- [x] T030 [US2] Add LLM prompt engineering in format_data node: include instructions for identifying patterns per FR-009 (transaction frequency, amount patterns, high-risk jurisdictions, PEP involvement, sanctions hits, similar names)
- [x] T031 [US2] Add audit logging for analysis in risk_analyzer: log analysis requests, LLM call results, error states (FR-017)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - full query + analysis capability with graceful degradation

---

## Phase 5: User Story 3 - Rules-Based Validation Integration (Priority: P3)

**Goal**: Combine LLM analysis with regulatory rules validation (when rules data available from external team)

**Independent Test**: Provide sample rules and verify analysis flags violations while maintaining functionality when rules unavailable

**Functional Requirements**: FR-012, FR-013

### Implementation for User Story 3

- [x] T032 [P] [US3] Create RulesData model in backend/models/rules.py with threshold_rules, prohibited_jurisdictions, documentation_requirements fields (placeholder structure for external team's data format)
- [x] T033 [US3] Add optional rules_data parameter to run_risk_analysis() function in backend/agents/aml_monitoring/risk_analyzer.py with default None (FR-012)
- [x] T034 [US3] Implement validate_rules node function in backend/agents/aml_monitoring/risk_analyzer.py: applies threshold checks, jurisdiction validation, documentation verification when rules_data provided
- [x] T035 [US3] Update StateGraph in risk_analyzer.py: add validate_rules node after parse_response, use conditional edge to skip if rules_data is None (graceful degradation)
- [x] T036 [US3] Update /api/payment-history/analyze endpoint: accept optional rules_data in request body, pass to risk analysis agent (FR-013)
- [x] T037 [US3] Merge rules validation results with LLM analysis in validate_rules node: append rule violations to flagged_transactions, update risk_score if violations found, preserve LLM insights (FR-013)
- [x] T038 [US3] Add logging for rules validation: log when rules applied, violations found, and when rules unavailable (FR-017)

**Checkpoint**: All user stories should now be independently functional - complete AML analysis system with rules integration

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T039 [P] Create backend/tests/conftest.py with pytest fixtures: mock_csv_data (sample DataFrame), mock_grok_response (sample AnalysisResult dict), mock_grok_client (mocked HTTP calls) [SKIPPED - Tests deferred for hackathon MVP]
- [ ] T040 [P] Add unit tests for transaction_service in backend/tests/unit/test_transaction_service.py: test OR logic, deduplication, case-insensitive search, empty results [SKIPPED - Tests deferred for hackathon MVP]
- [ ] T041 [P] Add unit tests for llm_client in backend/tests/unit/test_llm_client.py: test API calls with mocked responses, retry logic, error handling [SKIPPED - Tests deferred for hackathon MVP]
- [ ] T042 [P] Add integration test for risk analyzer agent in backend/tests/integration/test_risk_analyzer_agent.py: test full StateGraph workflow with mocked LLM, graceful degradation [SKIPPED - Tests deferred for hackathon MVP]
- [ ] T043 [P] Add integration test for API endpoints in backend/tests/integration/test_payment_history_api.py: test /query and /analyze endpoints with FastAPI TestClient [SKIPPED - Tests deferred for hackathon MVP]
- [ ] T044 [P] Add contract tests in backend/tests/contract/test_api_contracts.py: validate responses match OpenAPI schema from contracts/api-spec.yaml [SKIPPED - Tests deferred for hackathon MVP]
- [x] T045 [P] Add backend/README.md with setup instructions, API usage examples, environment variables documentation
- [x] T046 Code cleanup: add type hints throughout, run black formatter, run flake8 linter, add docstrings to public functions (Already complete - codebase has comprehensive type hints and docstrings)
- [ ] T047 Performance profiling: test query performance with 10K row dataset, verify <5s target, test LLM analysis with 100 transactions, verify <30s target [SKIPPED - Performance validation deferred for hackathon MVP]
- [x] T048 Validate quickstart.md: run all curl commands, verify responses match examples, update any outdated sections (Updated with Phase 5 API changes)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ INDEPENDENT
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 by adding analysis but US1 must work standalone ✅ INDEPENDENT (US1 /query endpoint works without analysis)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US2 but US2 must work without rules ✅ INDEPENDENT (graceful degradation when rules unavailable)

### Within Each User Story

- Models before services (data structures needed for business logic)
- Services before endpoints/agents (business logic needed for API/agents)
- Core implementation before integration (basic functionality before combining features)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- All Foundational tasks marked [P] can run in parallel (T005-T010, T012)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel (T013 for US1, T019-T021 for US2, T032 for US3)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 2

```bash
# Launch all models for User Story 2 together:
# Task T019: Create FlaggedTransaction and IdentifiedPattern models
# Task T020: Create AnalysisResult model
# Task T021: Create RiskAnalysisState TypedDict

# These can all run in parallel since they're in different files/sections

# Then after models complete, launch agent implementation tasks:
# Task T023: format_data node
# Task T024: call_llm node
# Task T025: parse_response node
# Task T026: handle_error node
# (All node functions are independent, can be written in parallel)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004) - ~30 minutes
2. Complete Phase 2: Foundational (T005-T012) - ~2 hours
3. Complete Phase 3: User Story 1 (T013-T018) - ~4 hours
4. **STOP and VALIDATE**: Test /api/payment-history/query endpoint independently
5. Deploy/demo if ready - **Value delivered**: Compliance officers can query payment history

**Total MVP Time**: ~6-7 hours of focused development

### Incremental Delivery

1. Complete Setup + Foundational (T001-T012) → Foundation ready (~2.5 hours)
2. Add User Story 1 (T013-T018) → Test independently → **Deploy/Demo (MVP!)** - Query capability live
3. Add User Story 2 (T019-T031) → Test independently → **Deploy/Demo** - AI analysis added (~6 hours)
4. Add User Story 3 (T032-T038) → Test independently → **Deploy/Demo** - Rules integration complete (~3 hours)
5. Polish (T039-T048) → Final refinement and testing (~4 hours)

**Total Feature Time**: ~15-16 hours of development

Each story adds value without breaking previous stories. Can stop at any checkpoint for demo/feedback.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T013-T018) - Query functionality
   - **Developer B**: User Story 2 (T019-T031) - LLM analysis (waits for US1 transaction_service)
   - **Developer C**: User Story 3 (T032-T038) - Rules integration (waits for US2 risk_analyzer)
3. Stories complete and integrate independently

**Recommended Sequential Order**: US1 → US2 → US3 (since US2 uses US1's service, US3 enhances US2's analysis)

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 8 tasks
- **Phase 3 (User Story 1)**: 6 tasks
- **Phase 4 (User Story 2)**: 13 tasks
- **Phase 5 (User Story 3)**: 7 tasks
- **Phase 6 (Polish)**: 10 tasks

**Total Tasks**: 48 tasks

**Parallelizable Tasks**: 20 tasks marked with [P]

**Independent User Stories**: All 3 stories can be tested/deployed independently

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 = 18 tasks (~6-7 hours)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths use backend/ prefix per plan.md project structure
- Grok API key placeholder in .env.example - user must fill actual key
- Tests in Phase 6 (Polish) rather than TDD approach - standard Python development practice
