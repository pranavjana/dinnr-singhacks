# DINNR AML Platform — Project Constitution

<!-- Sync Impact Report (v1.0.0 → v1.1.0): Added Next.js best practices, LangGraph patterns, and shadcn/ui specification -->

## Core Principles

### I. Agentic AI-First Architecture
Every core workflow (regulatory ingestion, transaction monitoring, document analysis) must be implemented as a stateful, multi-turn agentic system using LangGraph. Agents must maintain memory of prior decisions, justify recommendations through chain-of-thought reasoning, and expose audit trails for compliance defensibility. Hard requirement: No monolithic scripts; reasoning must be transparent and reproducible.

**LangGraph Best Practices**:
- Each agent workflow MUST be modeled as a directed graph with explicit state transitions; no implicit branching.
- Agent state schema MUST be Pydantic-based with strict type validation; all decision points must be typed.
- Agent memory MUST persist intermediate reasoning steps, tool calls, and LLM reasoning chains for auditability.
- Tool definitions MUST include schemas, descriptions, and error handling; no black-box tool calls.
- Conditional edges (router nodes) MUST be deterministic; decisions must be logged and reproducible.
- Max loop iterations MUST be configurable per workflow to prevent infinite loops; default is 10 iterations with escape hatch.
- Agent response validation MUST verify output schema before returning; invalid responses logged with full context for debugging.

### II. Real-Time Monitoring & Alerting
AML risk detection must operate in real-time or near-real-time with sub-second latency for alert generation. All alerts must be role-specific (Front/Compliance/Legal teams), prioritized by risk level, and include actionable remediation suggestions with regulatory context. Alerts without clear evidence or remediation path are rejected before surfacing to users.

### III. Audit Trail & Compliance First
Every decision—transaction analysis, document risk assessment, alert override, remediation action—must be logged with timestamp, user identity, decision rationale, and regulatory reference. Audit logs are immutable and queryable. No decision can be forgotten or overwritten. Compliance defensibility is non-negotiable.

### IV. Multi-Format Document Handling
Document processing must support PDFs, images, and text files. Format validation, OCR, image authenticity verification (reverse search, AI-detection, tampering analysis), and risk scoring must be integrated into a single pipeline. Formatting errors, missing sections, and structural anomalies must be flagged with evidence citations for compliance officers.

### V. Security & Data Minimization
All sensitive transaction data, client documents, and regulatory intelligence must be encrypted at rest (Supabase AES-256) and in transit (TLS 1.3+). Access control must enforce role-based permissions (Front, Compliance, Legal, Admin). PII logging is forbidden. Data retention policies must be explicit and configurable per jurisdiction (GDPR, AML regulations, etc.).

### VI. Scalable, Observable Backend
FastAPI backend must expose structured metrics (Prometheus-compatible) and structured logs (JSON format) for every transaction analyzed, document processed, and alert generated. Request tracing must be end-to-end. Performance SLAs: transaction analysis <500ms, document processing <5s per file. Health checks and circuit breakers required for all external API calls (Groq, regulatory data sources).

### VII. Frontend UX for Compliance Officers
Next.js frontend must provide intuitive, role-specific dashboards with real-time alert displays, drill-down document inspection, audit trail browsing, and one-click remediation actions. No dark patterns. Color-coding for risk levels must follow industry standards (red=high, yellow=medium, green=low). All workflows must be completable in ≤3 clicks from login.

**Next.js Best Practices**:
- All data fetching MUST use Server Components by default; Client Components only for interactivity (forms, state, event listeners).
- API routes MUST follow RESTful conventions with explicit HTTP methods (GET, POST, PUT, DELETE); no mixed-method routes.
- Middleware MUST handle authentication and authorization checks; no auth logic in route handlers.
- Dynamic routes MUST use proper path validation; prevent arbitrary path traversal via segment matchers.
- Image optimization MUST use Next.js `Image` component (never `<img>`); lazy load non-critical images.
- Environment variables MUST be prefixed (`NEXT_PUBLIC_` for client-side only); secrets never exposed to frontend.
- CSS MUST use TailwindCSS with shadcn/ui components; no custom CSS except for domain-specific styling via Tailwind utilities.
- Type safety MANDATORY: All API responses typed with TypeScript interfaces; no untyped `any`.

**shadcn/ui Integration Standards**:
- Use shadcn/ui base components as foundation for all UI elements (Button, Card, Table, Dialog, Input, etc.).
- Customize shadcn/ui components via Tailwind utility classes in component props (e.g., `className`); never override base component styles.
- Create custom domain components that wrap shadcn/ui for AML-specific workflows (e.g., `<AlertCard>`, `<RiskBadge>`, `<DocumentViewer>`).
- Color scheme MUST match risk-level standards: shadcn/ui destructive (red) for high-risk, warning (yellow) for medium, success (green) for low-risk.
- Accessibility MANDATORY: All shadcn/ui components automatically include ARIA attributes; preserve them; test keyboard navigation.
- Dark mode support REQUIRED: shadcn/ui provides dark class utilities; test all components in both light and dark themes.

## Technology Stack & Non-Negotiable Dependencies

**Frontend**: Next.js 14+, React 18+, TypeScript, TailwindCSS for styling, shadcn/ui for component library, Axios/SWR for API client, React Hook Form for form validation.
**Backend**: FastAPI 0.100+, Python 3.11+, LangGraph 0.1+, Pydantic for schema validation, Langsmith for agent observability.
**LLM Provider**: Groq (inference only; no fine-tuning or training).
**Database & Storage**: Supabase (PostgreSQL + S3-compatible storage for documents), with PostgREST for API layer.
**Authentication**: Supabase Auth (OAuth2/JWT) with role-based access control; enforce scopes for frontend/backend separation.
**Testing**: Pytest (backend), Vitest/Jest (frontend), Playwright/Cypress (e2e), integration tests for all critical workflows.
**Deployment**: Docker containerization, environment-based config (dev/staging/prod).
**Monitoring**: Structured logging (JSON), Prometheus metrics, Langsmith for agent tracing, optional APM (e.g., Datadog, NewRelic if budget available).

**Prohibited Technologies**: Unencrypted storage, plaintext credentials in code, closed-source compliance logic, vendor lock-in beyond Groq, custom component libraries (use shadcn/ui), untyped code (TypeScript strict mode MANDATORY).

## Development Workflow & Testing Discipline

### Code Review & Approval
All code changes (frontend, backend, agent logic) require:
1. Peer code review (minimum 1 approval) before merge.
2. All tests passing (backend: ≥80% coverage, frontend: ≥60% coverage, integration tests for alert/workflow paths).
3. Compliance checklist signed off by the team member most familiar with AML regulations.
4. Architecture review for changes affecting agent design or data flow.
5. **Frontend-specific checks**: TypeScript strict mode passes, shadcn/ui components used, Tailwind utilities only, Server Components by default.
6. **Backend/Agent-specific checks**: LangGraph graph structure valid, agent state schema typed, all tools have error handling, max iterations configured.

### Testing Gates (Non-Negotiable)
- **Unit tests**: Every agent decision logic function must have test coverage; all shadcn/ui custom domain components tested in isolation.
- **Integration tests**: Multi-turn agent workflows, database queries, Groq API calls, LangGraph state transitions must be tested end-to-end.
- **Compliance tests**: Alert generation accuracy, audit trail completeness, role-based access control, LangGraph reasoning chains logged correctly.
- **Load tests**: Backend must handle 100 concurrent requests for transaction analysis without degrading below SLA; Frontend must handle rapid alert streams without UI lag.
- **E2E tests**: Critical user journeys (login → view alerts → drill into document → trigger remediation) tested via Playwright/Cypress; run on every release candidate.

### CI/CD Pipeline
- **Linting**: Ruff for Python (include F, E, W, C codes), ESLint + Prettier for TypeScript/React, isort for imports.
- **Type Checking**: TypeScript strict mode (`tsconfig.json` with `strict: true`), mypy for Python backend.
- **Test execution**: Every PR must pass all tests; frontend e2e tests on release candidates only (time-box to 10min).
- **Security scanning**: Trivy for container images, OWASP dependency-check for vulnerabilities, Bandit for Python secrets.
- **Component checks**: Lighthouse audit for frontend (target: >90 Accessibility, >85 Performance); shadcn/ui version compatibility checked.
- **Manual security review**: Required for changes touching authentication, encryption, audit logic, or agent decision boundaries.
- **Staging deployment**: Automated after main branch tests pass; includes smoke tests for API health and agent workflows.
- **Production deployment**: Requires explicit approval + manual sign-off from backend and frontend owners; includes canary deployment (10% traffic first).

## Security & Observability Standards

### Information Security
- All environment variables (API keys, database credentials) stored in secure vaults (Supabase Secrets, GitHub Actions Secrets), never in version control.
- Encrypted PII at rest; no logging of raw transaction amounts, client names, or account numbers in plain text.
- TLS 1.3+ enforced for all external API calls (Groq, regulatory data sources).
- Rate limiting on API endpoints to prevent abuse (10 requests/second per user by default).
- Input validation on all user-provided data (SQL injection, XSS, command injection prevention).

### Observability & Monitoring
- All agent decisions logged as JSON with `timestamp`, `agent_id`, `decision_type`, `risk_score`, `user_id`, `rationale`.
- Prometheus metrics exposed at `/metrics` endpoint: `aml_transactions_analyzed_total`, `aml_alerts_generated_total`, `aml_document_risk_scores`, `groq_api_latency_ms`.
- Distributed tracing: Every request tagged with a unique `trace_id` propagated across services.
- Alert latency SLO: 95th percentile transaction analysis <500ms, 95th percentile alert generation <1000ms.
- Dashboard for on-call team to monitor system health, error rates, and SLA compliance (real-time during hackathon).

## Collaboration Expectations & Governance

### Team Communication
- Async-first: Document decisions in RFC format (request for comment) in GitHub Issues before implementation.
- Synchronous standups: 5-minute daily standup (async update in Slack if timezone prevents live sync).
- Code comments: Explain *why* not *what*; especially required for regulatory rule logic and agent decision trees.
- Architectural decision records (ADRs): Any major design change must be recorded in `.specify/adr/` directory.

### Responsibility Assignment
- **AML Regulatory Logic**: One designated team member acts as compliance subject matter expert; all compliance-critical PRs reviewed by this person.
- **Agent Design & LangGraph**: Another team member owns LangGraph architecture; all agent workflow changes, state schemas, tool definitions, and graph structure reviewed by this person; responsible for agent observability setup (Langsmith).
- **Frontend UX & shadcn/ui**: One team member owns Next.js dashboard and shadcn/ui component consistency; ensures Server Components used correctly, Tailwind utilities followed, dark mode support, accessibility standards enforced.
- **Backend Infrastructure**: One team member owns FastAPI setup, Supabase integration, monitoring; SLA and performance owned by this role; responsible for API contract stability.
- **Integration & Testing**: One team member owns test strategy, integration tests, and CI/CD; test coverage standards and e2e test suite ownership by this role; responsible for test infrastructure and CI/CD reliability.

### Conflict Resolution
- Technical disagreements resolved via RFC + architectural review; decision made within 24 hours.
- If consensus cannot be reached, escalate to the hackathon mentor for guidance.
- No code merged without resolution of blocking comments.

## Governance & Amendment Procedure

### Constitution Authority
This constitution supersedes all prior practices and guidelines. All technical decisions, code reviews, and deployment approvals must align with these principles. Violations are tracked and addressed in retros.

### Amendment Process
1. **Proposal**: Submit a GitHub Issue with title `[CONSTITUTION] <Change Description>` detailing the motivation and proposed change.
2. **Discussion**: Team discusses for max 24 hours asynchronously; decision made by consensus or mentor guidance.
3. **Documentation**: Approved amendments are integrated into this document with version bump and change log.
4. **Communication**: All team members notified of amendment; changes to dependent artifacts (spec.md, tasks.md, workflow files) are prioritized immediately.

### Version Policy
- **MAJOR** (e.g., 2.0.0): Removal or radical redefinition of a core principle.
- **MINOR** (e.g., 1.1.0): Addition of a new principle or materially expanded guidance.
- **PATCH** (e.g., 1.0.1): Clarifications, wording refinements, non-semantic corrections.

### Compliance Review
All PRs must include a checklist item: `- [ ] Verified compliance with Constitution (Core Principles I–VII)`. Code cannot be merged without this check signed off.

**Domain-Specific Checklists by Area**:
- **Frontend PRs**: `- [ ] TypeScript strict mode passes` | `- [ ] shadcn/ui components used (no custom CSS)` | `- [ ] Server Components by default` | `- [ ] Accessibility (WCAG 2.1 AA minimum)`
- **Backend/Agent PRs**: `- [ ] LangGraph graph structure valid and logged` | `- [ ] Agent state schema typed (Pydantic)` | `- [ ] All tools have error handling` | `- [ ] Max iterations set with escape hatch` | `- [ ] Reasoning chain preserved for audit trail`
- **Integration PRs**: `- [ ] E2E test coverage for user journey` | `- [ ] API contract stability verified` | `- [ ] No cross-layer responsibility violations`

---

**Version**: 1.1.0 | **Ratified**: 2025-11-01 | **Last Amended**: 2025-11-01
