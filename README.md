# RES_AGT - Agentic AI Academic Data System

RES_AGT is an AI agent project for academic data ingestion, retrieval, and reasoning.

Primary focus:

- agentic query handling over real stored data
- grounded answers from SQL and vector retrieval
- no hallucinated records

Frontend exists as an optional client UI. The core of the project is the agent backend.

## Agent Capabilities

- Ingest structured and unstructured academic documents (CSV, XLSX, PDF)
- Normalize data into students, subjects, and results
- Parse complex documents with LlamaParse when configured
- Answer chat queries using LangGraph-based agent flow
- Generate SQL-grounded reports
- Return exact fallback message when data is missing: NO DATA AVAILABLE

## Architecture

Core runtime:

- FastAPI API layer
- LangGraph agent orchestration
- Supabase PostgreSQL + pgvector
- sentence-transformers embeddings
- LlamaParse integration for document extraction

Optional UI:

- Next.js 14 frontend in frontend/

## Project Structure

- app/ : agent backend and services
- app/agents/ : query planning, intent extraction, response formatting
- app/services/ : ingestion, parsing, embeddings, reports
- app/db/sql/schema.sql : schema + RPC functions
- tests/integration/ : integration tests
- frontend/ : optional UI client

## Quick Start (Agent Backend)

1. Copy .env.example to .env
2. Fill required variables
3. Install dependencies
4. Run API server

Commands:

1. pip install -r requirements.txt
2. python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

OpenAPI:

- http://127.0.0.1:8010/docs

## Required Environment

Minimum required for backend agent:

- SUPABASE_URL
- SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY
- LLM_API_KEY
- HF_API_KEY or EMBEDDING_API_KEY
- API_KEY (or scoped API_KEYS)

Optional but recommended:

- LLAMA_CLOUD_API_KEY
- LLAMA_PARSE_RESULT_TYPE=markdown
- LLM_PARSER_ENABLED=true

Email automation (optional):

- EMAIL_AUTOMATION_ENABLED=true plus IMAP/SMTP values

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

## Database Setup

Apply schema before using query/report flows:

- app/db/sql/schema.sql

Includes:

- students, subjects, results
- documents, vector_chunks
- query_logs, email_logs, email_dead_letters
- RPCs for lookup, ranking, aggregation, comparison, and reports

## LlamaParse Wiring

When LLAMA_CLOUD_API_KEY is set:

- ingestion tries official LlamaParse extraction first
- parsed output is normalized and stored
- deterministic and LLM fallback parsers are still available

## Integration Testing

Test file:

- tests/integration/test_real_data_flow.py

Run:

- pytest tests/integration/test_real_data_flow.py

Environment for tests:

- INTEGRATION_API_BASE_URL

## Optional Frontend

If you want UI usage:

1. cd frontend
2. npm install
3. configure frontend/.env.local
4. npm run dev

## Docker

Run backend services:

- docker compose up --build

Services:

- api
- worker

## Operational Notes

- Never commit real secrets
- Keep generated artifacts out of Git
- Use scoped API keys for least privilege
- Check /ready after deploy

## License

No license file is currently included.
