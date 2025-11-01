# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **hackathon project** building an **Agentic AI solution for Anti-Money Laundering (AML)** for Julius Baer. The project consists of two integrated components:

1. **Part 1: Real-Time AML Monitoring & Alerts** - Ingests regulatory circulars, analyzes transactions, and generates role-based alerts
2. **Part 2: Document & Image Corroboration** - Validates compliance documents, detects formatting errors, and performs image integrity analysis

The solution combines a **Next.js frontend** with backend AI agents for regulatory monitoring and document processing.

## Repository Structure

```
dinnr-singhacks/
├── frontend/                           # Next.js 16 application
│   ├── app/                            # App Router pages
│   │   ├── dashboard/                  # Dashboard with sidebar layout
│   │   ├── layout.tsx                  # Root layout
│   │   └── page.tsx                    # Home page
│   ├── components/                     # React components
│   │   ├── ui/                         # shadcn/ui components (Avatar, Sidebar, etc.)
│   │   ├── app-sidebar.tsx             # Main navigation sidebar
│   │   └── nav-*.tsx                   # Navigation components
│   └── package.json                    # Frontend dependencies
├── backend/                            # FastAPI + LangGraph backend (to be created)
│   ├── main.py                         # FastAPI application entry point
│   ├── agents/                         # LangGraph agent definitions
│   │   ├── aml_monitoring/             # Part 1: AML monitoring agents
│   │   └── document_corroboration/     # Part 2: Document analysis agents
│   ├── routers/                        # FastAPI route handlers
│   ├── services/                       # Business logic and integrations
│   ├── models/                         # Pydantic models and schemas
│   └── requirements.txt                # Python dependencies
├── transactions_mock_1000_for_participants.csv  # Sample AML transaction data
├── Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf  # Sample compliance document
└── README.md                           # Full hackathon requirements
```

## Technology Stack

### Frontend
- **Framework**: Next.js 16.0.1 with App Router
- **React**: 19.2.0
- **TypeScript**: 5
- **Styling**: Tailwind CSS 4
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Icons**: lucide-react

### Backend
- **Framework**: FastAPI
- **AI Orchestration**: LangGraph for building agentic workflows
- **Capabilities**:
  - Regulatory parsing and document analysis
  - Transaction monitoring engine
  - Image verification (reverse search, AI-generated detection, tampering)

## Common Commands

### Frontend Development
```bash
cd frontend
npm run dev      # Start dev server (http://localhost:3000)
npm run build    # Production build
npm run start    # Start production server
npm run lint     # Run ESLint
```

### Backend Development
```bash
cd backend
uvicorn main:app --reload           # Start FastAPI dev server (http://localhost:8000)
uvicorn main:app --reload --port 8001  # Start on custom port
python -m pytest                    # Run tests
python -m pytest tests/ -v          # Run tests with verbose output
```

## Key Architecture Patterns

### Backend Structure (FastAPI + LangGraph)
- **FastAPI Routers**: Organize endpoints by feature domain (e.g., `/api/aml`, `/api/documents`)
- **LangGraph Agents**: Each major workflow (regulatory ingestion, transaction analysis, document validation) is implemented as a stateful graph
- **Agent Architecture**:
  - **State**: Defined using TypedDict or Pydantic models
  - **Nodes**: Individual processing steps (e.g., parse regulation, score transaction, extract document fields)
  - **Edges**: Control flow between nodes (conditional routing based on results)
  - **Graphs**: Compose nodes into complete workflows using StateGraph
- **Service Layer**: Business logic separate from API routes for testability
- **Integration Pattern**: Frontend calls FastAPI endpoints → FastAPI invokes LangGraph agents → Agents return structured results

### Frontend Structure
- **Path Alias**: `@/*` maps to the frontend root directory (e.g., `@/components/ui/button`)
- **Client Components**: Components using hooks/state are marked with `"use client"` directive
- **Sidebar Pattern**: The dashboard uses a collapsible sidebar layout with `SidebarProvider` wrapping content
- **Component Structure**:
  - UI primitives in `components/ui/`
  - Feature components at `components/` root
  - Page components in `app/`

### Data Files
- **transactions_mock_1000_for_participants.csv**: Contains synthetic AML transaction data with jurisdiction, regulator, amounts, screening flags, and SWIFT fields for building the monitoring engine
- **Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf**: Scanned compliance document for OCR, format validation, and document corroboration testing

## Hackathon Requirements

### Part 1: Real-Time AML Monitoring
- Regulatory ingestion from FINMA, HKMA, MAS
- Transaction analysis against current rules
- Role-based alerts (Front/Compliance/Legal teams)
- Remediation workflows with audit trails

### Part 2: Document & Image Corroboration
- Multi-format processing (PDF, text, images)
- Format validation (spacing, fonts, spelling, headers)
- Image authenticity checks (reverse search, AI-detection, tampering)
- Risk scoring and real-time feedback

### Integration Requirements
- Unified dashboard showing both transaction alerts and document risks
- Cross-reference capabilities between transaction and document analysis
- PDF report generation highlighting red flags
- Comprehensive audit trails

## Important Notes

- **Hackathon Context**: This is a time-sensitive competition project. Focus on demonstrable functionality over perfect architecture.
- **Judging Criteria**: Objective achievement (20%), Creativity (20%), Visual design (20%), Presentation (20%), Technical depth (20%)
- **Sample Data**: Use the provided CSV and PDF files for prototyping and demonstration
- **Backend Stack**: FastAPI for REST APIs + LangGraph for orchestrating multi-agent AI workflows.
- **Frontend Already Has CLAUDE.md**: The frontend subdirectory has its own CLAUDE.md with Next.js-specific guidance. Refer to `frontend/CLAUDE.md` for frontend-only work.

## Development Workflow

When implementing features:
1. Understand which part (AML Monitoring vs Document Corroboration) you're building
2. Use the provided sample data files for testing
3. Frontend changes go in `frontend/` directory
4. Backend changes go in `backend/` directory
   - API endpoints in `routers/`
   - LangGraph agent workflows in `agents/`
   - Business logic in `services/`
5. Keep the hackathon timeline in mind - prioritize working demos over perfect code

### LangGraph Agent Development
- Each agent workflow should be a separate StateGraph in `backend/agents/`
- Define clear state schemas using TypedDict or Pydantic
- Break complex workflows into discrete nodes (each node = one focused task)
- Use conditional edges for decision points (e.g., risk threshold routing)
- Agents should be composable - larger workflows can invoke smaller sub-agents
- Test agents independently before integrating with FastAPI endpoints

## Reference Documentation

- Full requirements and features checklist: `README.md`
- Frontend-specific guidance: `frontend/CLAUDE.md`
- Mentor: Wee Kiat (Open Innovation Lead, AI, Data & Innovation)

## Active Technologies
- Python 3.11+ + FastAPI, LangGraph, Grok Kimi 2 LLM client, Pydantic, pandas (CSV processing) (001-payment-history-analysis)
- CSV file (`transactions_mock_1000_for_participants.csv`) - read-only access (001-payment-history-analysis)

## Recent Changes
- 001-payment-history-analysis: Added Python 3.11+ + FastAPI, LangGraph, Grok Kimi 2 LLM client, Pydantic, pandas (CSV processing)
