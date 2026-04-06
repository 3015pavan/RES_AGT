# Unified Agentic AI Backend (Phase 2 Foundation)

This repository provides the production-oriented backend foundation for a real-data-only agentic AI system.

## Rules Enforced
- No mock or seeded business data.
- Responses are generated only from Supabase PostgreSQL and pgvector retrievals.
- If no retrieval data exists, response is exactly: NO DATA AVAILABLE.
- LLM is restricted to normalization, intent extraction, and formatting.

## Run
1. Create and activate virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill all required values.
4. Run API:
   - `uvicorn app.main:app --reload`
5. Include API key in requests:
   - `x-api-key: <API_KEY>`
   - or use scoped key from `API_KEYS`.

## Endpoints
- POST /upload
- POST /email/poll
- POST /chat
- GET /students
- GET /documents
- POST /report
- GET /health
- GET /ready
- GET /metrics

Upload response includes:
- rows_ingested
- documents_created
- document_ids

## Scoped Authorization
- Legacy full-access key:
   - `API_KEY=<value>` grants all scopes.
- Scoped keys:
   - `API_KEYS=<key1>:ingest:upload|query:chat,<key2>:read:students|read:documents`
- Route scope map:
   - `/upload` -> `ingest:upload`
   - `/email/poll` -> `ingest:email`
   - `/chat` -> `query:chat`
   - `/report` -> `report:generate`
   - `/students` -> `read:students`
   - `/documents` -> `read:documents`

## Notes
- SQL schema is in `app/db/sql/schema.sql`.
- LangGraph flow is in `app/agents/graph.py`.
- Email polling and attachment ingestion use the same normalization path as upload ingestion.

## Phase 3 Additions
- Deterministic tabular normalization maps CSV/XLSX columns to canonical fields before DB upsert.
- Structured rows are upserted into unified `students`, `subjects`, and `results` tables.
- SQL RPC function package is included for all intents and reports.
- `student_report` computes SGPA from credits and grade scale (customizable via request payload).

## Phase 4 Hardening
- Request tracing middleware attaches and returns `x-request-id`.
- In-memory rate limiting is enabled with `RATE_LIMIT_PER_MINUTE`.
- API key authentication is required for data endpoints.
- Standardized JSON error envelope is returned for handled and unhandled errors.
- Startup readiness checks validate env and Supabase connectivity.
- Grok, IMAP, and SMTP calls are guarded with retries and timeouts.
- Email attachment idempotency is enforced via SHA-256 hash tracking.

## Phase 5 Hardening And Deployment
- CORS and trusted-host policies are configurable via environment variables.
- Request-size middleware enforces global body size limits.
- Structured JSON logs include correlated request_id for traceability.
- Request audit logs capture method, path, status, latency, and client host.
- Lightweight metrics endpoint exposes request totals, error totals, and average latency.
- Worker loop supports graceful shutdown on process signals.
- Dockerfile and docker-compose provide supervised API and worker services.

## Phase 6 Additions
- Migration package markers are stored in `app/db/migrations`.
- Startup readiness now enforces migration guard by validating `schema_migrations` versions.
- OpenAPI metadata now includes grouped tags, endpoint summaries, and request examples.
- Endpoint authorization is scope-aware with explicit per-route requirements.
- CI workflow added for lint, compile, integration command, and container build verification.

## Additional Reliability And Audit Features
- `query_logs` stores query path metadata (intent, tool choice, result counts, status).
- `email_dead_letters` stores failed email processing records for replay/investigation.
- Circuit breaker guards added for Grok and embedding calls.
- Upload content scanner blocks known dangerous signatures before processing.

## Migration Guard Flow
1. Apply schema SQL from `app/db/sql/schema.sql`.
2. Ensure row exists in `schema_migrations` for required package versions.
3. Check `/ready`; it will report pending migration versions if any are missing.

## Container Run
1. Copy environment file:
   - cp .env.example .env
2. Fill all environment variables in .env.
3. Build and start services:
   - docker compose up --build
4. Stop services:
   - docker compose down

## Worker Mode
Run continuous email automation worker:
- `python -m app.worker.email_worker`

The worker performs:
- Poll unread emails
- Ingest body and attachments into unified data system
- Detect query emails and send SMTP replies
- Repeat on configured interval (`EMAIL_POLL_INTERVAL_SECONDS`)

## Apply Database Schema
Run `app/db/sql/schema.sql` in Supabase SQL editor before using chat/report flows.

## Integration Tests (Real Services Only)
The integration suite does not use mock data. It runs against a deployed API and real configured backends.

Required env:
- `INTEGRATION_API_BASE_URL`

Optional env:
- `INTEGRATION_UPLOAD_FILE` for upload ingestion test
- `INTEGRATION_CHAT_QUERY` for chat test override
- `INTEGRATION_REPORT_USN` for scoped student report
- `INTEGRATION_ENABLE_EMAIL_TEST=1` to run `/email/poll` test

Run:
- `pytest tests/integration/test_real_data_flow.py`
