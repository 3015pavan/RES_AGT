# Frontend (Next.js 14)

Production-grade frontend for the grounded AI backend.

## Stack

- Next.js 14 (App Router)
- React + TypeScript
- Tailwind CSS
- Axios

## Folder Structure

- app/
- app/page.tsx
- app/workbench/page.tsx
- app/students/page.tsx
- app/documents/page.tsx
- app/reports/page.tsx
- app/status/page.tsx
- app/api/chat/route.ts
- app/api/upload/route.ts
- app/api/email/poll/route.ts
- app/api/students/route.ts
- app/api/documents/route.ts
- app/api/report/route.ts
- app/api/status/route.ts
- components/chat-panel.tsx
- components/upload-panel.tsx
- components/email-panel.tsx
- components/status-panel.tsx
- components/students-table.tsx
- components/documents-table.tsx
- components/report-panel.tsx
- lib/api-client.ts
- lib/backend.ts
- lib/types.ts

## Environment

Create frontend/.env.local from frontend/.env.example and set:

- NEXT_PUBLIC_API_BASE_URL=<http://127.0.0.1:8000>
- BACKEND_API_BASE_URL=<http://127.0.0.1:8000>
- BACKEND_API_KEY=your-backend-api-key

## Run

1. cd frontend
2. npm install
3. npm run dev
4. Open <http://localhost:3000>

## Notes

- The browser never receives backend secret keys directly.
- Browser calls Next route handlers under app/api/*, and those handlers call FastAPI using server-side env vars.
- If backend returns NO DATA AVAILABLE, chat UI shows a clean fallback message.
