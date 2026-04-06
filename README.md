# RES_AGT - Agentic AI Academic Data System

RES_AGT is an AI agent project for academic data ingestion, retrieval, and reasoning.

Primary focus:

- agentic query handling over real stored data
- grounded answers from SQL and vector retrieval
- no hallucinated records

## Agent Capabilities

- Ingest structured and unstructured academic documents (CSV, XLSX, PDF)
- Normalize data into students, subjects, and results
- Parse complex documents with LlamaParse
- Answer chat queries using LangGraph-based agent flow
- Generate SQL-grounded reports
- Ingest and process email data through worker flow
- Return exact fallback message when data is missing: NO DATA AVAILABLE

## Architecture

Core runtime:

- FastAPI API layer
- LangGraph agent orchestration
- Supabase PostgreSQL + pgvector
- sentence-transformers embeddings
- LlamaParse integration for document extraction
- Email worker for IMAP polling and SMTP response flow

Application UI:

- Next.js 14 frontend in frontend/

## Project Structure

- app/ : agent backend and services
- app/agents/ : query planning, intent extraction, response formatting
- app/services/ : ingestion, parsing, embeddings, reports
- app/db/sql/schema.sql : schema + RPC functions
- tests/integration/ : integration tests
- frontend/ : application web client
- docker-compose.yml : API + worker orchestration
- Dockerfile : backend runtime image

## Quick Start

1. Copy .env.example to .env
2. Fill required variables
3. Install backend dependencies
4. Start backend API
5. Install frontend dependencies
6. Start frontend UI

Backend commands:

1. pip install -r requirements.txt
2. python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

Backend OpenAPI:

- http://127.0.0.1:8010/docs

Frontend commands:

1. cd frontend
2. npm install
3. npm run dev

Frontend URL:

- http://localhost:3000

## Required Environment

Core backend variables:

- SUPABASE_URL
- SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY
- LLM_API_KEY
- HF_API_KEY or EMBEDDING_API_KEY
- API_KEY (or scoped API_KEYS)
- LLAMA_CLOUD_API_KEY
- LLAMA_PARSE_RESULT_TYPE=markdown
- LLM_PARSER_ENABLED=true

Email ingestion variables:

- EMAIL_AUTOMATION_ENABLED=true
- IMAP_HOST, IMAP_PORT, IMAP_USER/IMAP_USERNAME, IMAP_PASSWORD
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

Frontend variables (frontend/.env.local):

- NEXT_PUBLIC_API_BASE_URL
- BACKEND_API_BASE_URL
- BACKEND_API_KEY

## API Surface

Ingestion:

- POST /upload
- POST /email/poll

Agent Query:

- POST /chat
- POST /report

Data Catalog:

- GET /students
- GET /documents

Ops:

- GET /health
- GET /ready
- GET /metrics

Auth:

- x-api-key header is required on protected endpoints

## Data And Retrieval Contract

- Agent answers must come from persisted database/vector retrieval
- If retrieval is empty, response must be exactly NO DATA AVAILABLE
- SQL and vector retrieval are grounded by stored data only

## Database Setup

Apply schema before using query/report flows:

- app/db/sql/schema.sql

Includes:

- students, subjects, results
- documents, vector_chunks
- query_logs, email_logs, email_dead_letters
- RPCs for lookup, ranking, aggregation, comparison, and reports

## LlamaParse Wiring

- LlamaParse extraction is integrated into ingestion flow
- Parsed output is normalized and stored in unified tables
- Deterministic and LLM fallback parsers remain in pipeline for robustness

## Email Worker

Start worker loop:

- python -m app.worker.email_worker

Worker responsibilities:

- Poll unread emails from IMAP
- Ingest body and attachments into the same data model
- Trigger grounded responses for query emails
- Send replies using SMTP

## Integration Testing

Test file:

- tests/integration/test_real_data_flow.py

Run:

- pytest tests/integration/test_real_data_flow.py

Environment for tests:

- INTEGRATION_API_BASE_URL

## Docker

Run application services:

- docker compose up --build

Services:

- api
- worker

## Operational Notes

- Never commit real secrets
- Keep generated artifacts out of Git
- Use scoped API keys for least privilege
- Check /ready after deploy
- Apply schema migrations before production startup

## License

No license file is currently included.
