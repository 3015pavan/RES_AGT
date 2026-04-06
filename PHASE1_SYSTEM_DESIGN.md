# Phase 1 - System Design (Unified Agentic AI, Real Data Only)

## 1) Scope and Non-Negotiable Rules

This system is a production-grade, data-grounded AI backend that behaves like ChatGPT but answers only from real stored data.

Hard rules:
- No mock, seed, or hardcoded business data.
- Answer source of truth is only:
  - Supabase PostgreSQL tables (structured data)
  - Supabase pgvector index (unstructured data)
- If query execution returns no rows/chunks, return exactly:
  - NO DATA AVAILABLE
- LLM is never allowed to invent facts.
- LLM use is restricted to:
  - query normalization
  - intent/entity extraction
  - response formatting from retrieved results only

## 2) Unified End-to-End Architecture

Input channels:
- Upload API (CSV, XLSX, PDF)
- Email ingestion (IMAP polling of unread emails)
- Chat API

Unified processing:
1. Parse and normalize incoming artifacts (upload and email attachment paths share same parser pipeline).
2. Persist structured entities into shared relational tables.
3. Persist textual artifacts into shared vector store.
4. Route user/email queries through a LangGraph execution graph.
5. Execute SQL, vector, or hybrid retrieval.
6. Validate non-empty, source-grounded outputs.
7. Return chat response or send SMTP email response.

Single dataset rule:
- Upload and email data are stored in the same schema and are queried together.
- No separate duplicate data paths.

## 3) Logical Components

Core services:
- API Gateway (FastAPI)
- Upload Ingestion Service
- Email Poller Service (IMAP)
- Document Parsing Service (CSV/XLSX/PDF)
- Normalization and Validation Service
- Embedding Service (Hugging Face embeddings)
- Unified Repository Layer (Supabase Postgres + pgvector)
- LangGraph Orchestrator
- Query Tooling Layer (SQL tool, Vector tool, Hybrid merge tool)
- Report Generation Service
- Email Reply Service (SMTP)
- Audit and Observability Layer

External dependencies:
- Supabase Postgres + pgvector
- Grok LLM endpoint
- Hugging Face embedding model/API
- IMAP server
- SMTP server

## 4) Unified Data Model

### 4.1 Structured Tables

1. students
- id (uuid, pk)
- usn (text, unique, indexed)
- student_name (text, nullable)
- semester (int, nullable)
- section (text, nullable)
- created_at (timestamptz)
- updated_at (timestamptz)

2. subjects
- id (uuid, pk)
- subject_code (text, unique, indexed)
- subject_name (text, indexed)
- semester (int, nullable)
- credits (numeric, nullable)
- created_at (timestamptz)
- updated_at (timestamptz)

3. results
- id (uuid, pk)
- student_id (uuid, fk students.id, indexed)
- subject_id (uuid, fk subjects.id, indexed)
- exam_type (text, nullable)
- marks (numeric, nullable)
- max_marks (numeric, nullable)
- grade (text, nullable)
- pass_fail (text, nullable)
- source_type (text, check upload|email)
- source_ref (uuid, nullable)
- created_at (timestamptz)
- updated_at (timestamptz)
- unique constraint on (student_id, subject_id, exam_type, source_ref)

4. documents
- id (uuid, pk)
- source_type (text, check upload|email)
- source_ref (uuid, nullable)
- file_name (text)
- mime_type (text)
- content_text (text, nullable)
- metadata (jsonb)
- created_at (timestamptz)

5. email_logs
- id (uuid, pk)
- message_id (text, unique, indexed)
- sender_email (text, indexed)
- subject (text)
- body_text (text, nullable)
- received_at (timestamptz)
- processed_at (timestamptz, nullable)
- has_attachments (boolean)
- query_detected (boolean)
- query_text (text, nullable)
- response_status (text, nullable)
- response_error (text, nullable)
- created_at (timestamptz)

### 4.2 Vector Table

6. vector_chunks (pgvector)
- id (uuid, pk)
- document_id (uuid, fk documents.id, indexed)
- chunk_index (int)
- chunk_text (text)
- embedding (vector(N))
- source_type (text, check upload|email)
- source_ref (uuid, nullable)
- metadata (jsonb)
- created_at (timestamptz)

Indexing:
- ivfflat or hnsw index on embedding for ANN similarity search.
- btree indexes on usn, subject_code, subject_name, sender_email, message_id, created_at.

## 5) Unified Ingestion Pipelines

### 5.1 Upload Agent Flow

Input: CSV/XLSX/PDF via POST /upload.

Steps:
1. Validate file type and size.
2. Parse file:
   - CSV/XLSX: tabular extraction
   - PDF: OCR/text extraction if needed
3. Normalize to canonical schema:
   - USN, subject, marks, grades, semester
4. Validate required fields and data types.
5. Upsert students/subjects.
6. Insert results rows.
7. Store original/extracted text into documents.
8. Chunk text, embed via HF, insert vector_chunks.
9. Emit audit log and return ingestion summary.

### 5.2 Email Agent Flow

Trigger: POST /email/poll or scheduled worker.

Steps:
1. Connect IMAP and poll unread emails.
2. For each email:
   - Extract sender, subject, body, message-id, attachments
3. Insert email_logs row first (idempotent by message_id).
4. Store email body in documents and vector_chunks.
5. If attachment exists, route attachment bytes into same parser used by upload agent.
6. Persist parsed structured data into same students/subjects/results tables.
7. Detect if email body contains a data query.
8. If query exists, invoke LangGraph QA flow.
9. Send SMTP reply and update email_logs response_status.

Idempotency:
- message_id unique key prevents duplicate ingestion.
- attachment hash can prevent repeated attachment re-processing.

## 6) LangGraph Agent Design (Strict Graph)

Graph nodes:
1. normalize_query
2. extract_intent_entities
3. plan_query
4. decide_tool
5. execute_sql (conditional)
6. execute_vector (conditional)
7. merge_validate
8. format_response

State object (typed):
- raw_query
- normalized_query
- intent
- entities {usn, subject, semester, filters}
- missing_fields
- tool_plan
- sql_result_rows
- vector_result_chunks
- merged_result
- validation_status
- final_response

Node policies:
- normalize_query: LLM rewrite to canonical form only, no facts.
- extract_intent_entities: classify intent + extract entities; if required entity missing, return clarification prompt.
- plan_query: deterministic plan template from intent + entities.
- decide_tool:
  - SQL for structured metrics
  - Vector for semantic docs/email body
  - Hybrid for mixed asks
- execute_sql: parameterized SQL only.
- execute_vector: embedding similarity search with optional metadata filters.
- merge_validate: enforce source grounding and non-empty checks.
- format_response: LLM formats only using merged_result payload.

Critical enforcement:
- If merged_result is empty -> final_response must be exactly NO DATA AVAILABLE.
- Formatting node receives only retrieved payload; no autonomous generation allowed.

## 7) Intent Taxonomy and Query Handling

Supported intents:
- student_lookup
- subject_analysis
- ranking
- comparison
- aggregation
- report_generation

Messy query normalization examples:
- marks phy of 1ms21cs002 -> intent student_lookup, entities usn=1MS21CS002, subject=Physics
- who top?? -> intent ranking, entities missing scope -> ask clarification (class/subject/semester)
- lowest sub which -> intent subject_analysis with missing context -> ask clarification
- sgpa cs001 -> intent aggregation/student_lookup with usn parse

Clarification rule:
- If required scope/entity is missing, ask targeted clarification; do not guess.

## 8) Report Generator Design

Report types:
1. Student Report
- per-subject marks
- grades
- SGPA computation

2. Class Report
- top students
- class average
- failure counts

3. Subject Report
- highest
- lowest
- average

Computation policy:
- All computations happen from SQL query results only.
- No LLM arithmetic.

## 9) FastAPI Surface

Required endpoints:
- POST /upload
  - multipart file upload
  - returns ingestion counts and document IDs

- POST /email/poll
  - triggers IMAP poll cycle
  - returns processed email count + errors

- POST /chat
  - accepts query text + optional context
  - invokes LangGraph flow
  - returns grounded answer or NO DATA AVAILABLE

- GET /students
  - paginated students listing from table

- GET /documents
  - paginated documents listing

- POST /report
  - report_type + filters
  - returns computed report object

Recommended additional endpoints for production:
- GET /health
- GET /metrics

## 10) Security and Hardening

Input and API:
- Pydantic strict schemas for all request payloads.
- File upload type, size, and content scanning checks.
- Request rate limiting.
- AuthN/AuthZ layer (JWT/API key).

Database:
- Parameterized SQL only, never string interpolation.
- Least-privilege DB role for app.
- Row-level security as needed in Supabase.

Email:
- Validate sender and sanitize email body.
- Attachment filename/path sanitization.
- IMAP/SMTP TLS required.

Runtime reliability:
- Timeouts and retries with capped exponential backoff.
- Circuit-breaker around external LLM/embedding APIs.
- Dead-letter handling for failed email items.

Auditability:
- Request IDs and trace IDs.
- Persist execution metadata for query path and tool decisions.

## 11) Testing Strategy (Design-Level)

Test suites:
- Unit tests:
  - parsers, normalizers, validators, SGPA calculator
- Integration tests:
  - upload -> DB/vector writes
  - email poll -> attachment ingest -> DB/vector writes
  - chat -> SQL/vector/hybrid -> response
- Security tests:
  - SQL injection payloads
  - malformed file uploads
- Reliability tests:
  - IMAP timeout, SMTP failure, LLM timeout
- Contract tests:
  - endpoint schemas and status behavior

Critical assertion in all query tests:
- empty retrieval returns exact string NO DATA AVAILABLE

## 12) Deployment Topology

Services:
- fastapi-app (API + LangGraph orchestrator)
- email-worker (scheduler + IMAP poll + SMTP reply)
- shared Supabase backend (Postgres + pgvector)

Execution model:
- API and worker share same repository layer and schemas.
- Worker can be cron-triggered or queue-triggered.

Observability:
- Structured logs (JSON)
- Metrics (latency, error rate, ingestion counts)
- Trace spans per graph node

## 13) Environment Variables

Required:
- SUPABASE_URL
- SUPABASE_KEY
- HF_API_KEY
- GROK_API_KEY
- IMAP_HOST
- IMAP_PORT
- IMAP_USER
- IMAP_PASSWORD
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD
- SMTP_FROM

Recommended:
- APP_ENV
- LOG_LEVEL
- API_TIMEOUT_SECONDS
- EMBEDDING_MODEL_NAME
- GROK_MODEL_NAME
- MAX_UPLOAD_MB
- EMAIL_POLL_BATCH_SIZE

## 14) Explicit Gaps To Resolve Before Build (Phase 2)

Open decisions required for implementation:
1. Exact SGPA formula and grade-point mapping policy.
2. Canonical subject dictionary (aliases, e.g., phy -> Physics).
3. PDF extraction approach (native text first, OCR fallback policy).
4. Poll cadence and deployment style for email worker.
5. Authentication model for FastAPI endpoints.

These are design blockers for deterministic behavior, not architectural blockers.

## 15) Phase 1 Acceptance Checklist

- Unified schema for upload and email defined.
- Single vector strategy defined for both sources.
- Strict LangGraph node flow defined.
- Non-hallucination constraints encoded in node policies.
- Required API surface and report requirements mapped.
- Security, reliability, and testing strategy documented.
