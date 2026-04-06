# RES_AGT - Unified Agentic AI Academic Backend

A production-oriented full-stack project for academic result ingestion, grounded chat, and report generation.

## Overview

This repository contains:

- A FastAPI backend for:
  - file ingestion (CSV, XLSX, PDF)
  - optional email polling ingestion
  - grounded chat and report generation
  - Supabase SQL + pgvector retrieval
- A Next.js 14 frontend for:
  - upload, chat, student/document browsing, reports, and status views

Core retrieval contract:

- Responses are grounded in persisted data only.
- If no data is found, the response is exactly: NO DATA AVAILABLE.

## Tech Stack

Backend:

- FastAPI
- Supabase (PostgreSQL + pgvector)
- LangGraph
- sentence-transformers
- LlamaParse (for document parsing when configured)

Frontend:

- Next.js 14 (App Router)
- React + TypeScript
- Tailwind CSS

## Repository Structure

- app/ : backend application code
- app/db/sql/schema.sql : database schema and RPC functions
- frontend/ : Next.js UI
- tests/integration/ : integration tests
- Dockerfile : backend container image
- docker-compose.yml : API + worker services

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- Supabase project with schema applied

## Environment Setup

1. Copy .env.example to .env
2. Fill required values:

Required:

- SUPABASE_URL
- SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY)
- LLM_API_KEY
- HF_API_KEY (or EMBEDDING_API_KEY)
- API_KEY (or scoped API_KEYS)

Optional:

- LLAMA_CLOUD_API_KEY
- LLAMA_PARSE_RESULT_TYPE (markdown or text)
- EMAIL_AUTOMATION_ENABLED and IMAP/SMTP variables for email flows

## Backend Setup (Local)

1. Create and activate a virtual environment
2. Install dependencies:

   pip install -r requirements.txt

3. Run backend:

   python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

4. API docs:

- http://127.0.0.1:8010/docs

## Frontend Setup (Local)

1. Go to frontend:

   cd frontend

2. Install dependencies:

   npm install

3. Configure frontend env:

- Create frontend/.env.local
- Set:
  - NEXT_PUBLIC_API_BASE_URL
  - BACKEND_API_BASE_URL
  - BACKEND_API_KEY

4. Run:

   npm run dev

5. Open:

- http://localhost:3000

## API Endpoints

Ingestion:

- POST /upload
- POST /email/poll

Query:

- POST /chat
- POST /report

Catalog:

- GET /students
- GET /documents

Ops:

- GET /health
- GET /ready
- GET /metrics

Authentication:

- Provide x-api-key request header.
- Scoped authorization is supported via API_KEYS.

## Database

Apply the SQL file before using chat and reports:

- app/db/sql/schema.sql

The schema includes:

- students, subjects, results
- documents, vector_chunks
- query_logs, email_logs, email_dead_letters
- RPC functions for student lookup, ranking, aggregation, analysis, and reports

## LlamaParse Integration

When LLAMA_CLOUD_API_KEY is configured:

- Ingestion attempts official LlamaParse document extraction
- Parsed content is normalized and upserted into students/subjects/results
- Existing deterministic and LLM-assisted fallback paths remain available

## Testing

Integration tests:

- tests/integration/test_real_data_flow.py

Run:

- pytest tests/integration/test_real_data_flow.py

Notes:

- Tests are real-service integration style (no mock business data).
- Configure INTEGRATION_API_BASE_URL and optional integration env values.

## Docker

Start services:

- docker compose up --build

Services:

- api: FastAPI app
- worker: email polling worker

## Production Notes

- Do not commit real secrets in .env files.
- Keep node_modules and build caches out of Git.
- Use scoped API keys for least privilege.
- Validate readiness at /ready after deployment.

## License

No license file is currently included. Add one if this project is to be distributed publicly.
